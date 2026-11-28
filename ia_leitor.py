import base64
import hashlib
import html
import ipaddress
import json
import re
import urllib.parse

import streamlit as st

from config import (
    ICONES_CATEGORIA,
    LISTA_CATEGORIAS,
    REGRAS_CATEGORIA,
    formatar_reais,
    ler_segredo,
    normalizar_texto,
    obter_gemini_client,
    obter_http_session,
    preparar_imagem_base,
)


# --- Categorização Automática ---
def identificar_categoria_local(produto):
    p_norm = normalizar_texto(produto)
    return next((cat for padrao, cat, _ in REGRAS_CATEGORIA if padrao.search(p_norm)), "Outros")


@st.cache_data(ttl=86400, show_spinner=False)
def classificar_com_ia(prod_norm, api_key):
    from google.genai import types
    resp = obter_gemini_client(api_key).models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"Produto: {prod_norm}",
        config=types.GenerateContentConfig(
            system_instruction=f"Classificador de produtos de mercado no Brasil. Responda APENAS com UMA categoria exata: {', '.join(LISTA_CATEGORIAS)}."
        ),
    )
    limpa = normalizar_texto(resp.text)
    return next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in limpa), "Outros")


@st.cache_data(ttl=86400, show_spinner=False)
def classificar_lote_com_ia(prods_norm, api_key):
    from google.genai import types
    resp = obter_gemini_client(api_key).models.generate_content(
        model="gemini-3.5-flash-lite",
        contents="Produtos:\n" + "\n".join(f"{i + 1}. {p}" for i, p in enumerate(prods_norm)),
        config=types.GenerateContentConfig(
            system_instruction=f"Classificador de produtos no Brasil. Retorne 'categorias' na mesma ordem usando APENAS: {', '.join(LISTA_CATEGORIAS)}.",
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {"categorias": {"type": "ARRAY", "items": {"type": "STRING"}}},
                "required": ["categorias"],
            },
        ),
    )
    cats = json.loads(resp.text).get("categorias", [])
    return [
        next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in (normalizar_texto(cats[i]) if i < len(cats) else "")), "Outros")
        for i in range(len(prods_norm))
    ]


def identificar_categoria(produto, api_key):
    if (cat_local := identificar_categoria_local(produto)) != "Outros" or not api_key:
        return cat_local
    try:
        return classificar_com_ia(normalizar_texto(produto), api_key)
    except Exception:
        return "Outros"


def identificar_categorias_em_lote(produtos, api_key):
    res = [identificar_categoria_local(p) for p in produtos]
    if not api_key or not (desc := [(i, normalizar_texto(produtos[i])) for i, c in enumerate(res) if c == "Outros"]):
        return res
    try:
        for (idx, _), cat_ia in zip(desc, classificar_lote_com_ia(tuple(p for _, p in desc), api_key)):
            res[idx] = cat_ia
    except Exception:
        pass
    return res


# --- Reconhecimento por Voz ---
def reconhecer_produto_por_voz(audio_bytes, api_key, mime_type="audio/wav"):
    from google.genai import types
    schema = {
        "type": "OBJECT",
        "properties": {
            k: {"type": t}
            for k, t in [
                ("transcricao", "STRING"),
                ("produto", "STRING"),
                ("categoria", "STRING"),
                ("quantidade", "INTEGER"),
                ("preco_unitario", "NUMBER"),
                ("supermercado", "STRING"),
            ]
        },
        "required": ["transcricao", "produto", "categoria", "quantidade", "preco_unitario", "supermercado"],
    }
    prompt = (
        f"Extraia do áudio de compra no Brasil: transcricao, produto, "
        f"categoria (uma de: {', '.join(LISTA_CATEGORIAS)}), quantidade (1 padrão), "
        f"preco_unitario (0 padrão) e supermercado ('' padrão)."
    )
    resp = obter_gemini_client(api_key).models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema),
    )
    d = json.loads(resp.text)
    cat_n, prod_ok = normalizar_texto(d.get("categoria", "")), str(d.get("produto", "")).strip()
    cat_ok = next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in cat_n), None) or identificar_categoria_local(prod_ok)
    return {
        "transcricao": str(d.get("transcricao", "")).strip(),
        "produto": prod_ok,
        "categoria": cat_ok,
        "quantidade": max(1, int(d.get("quantidade") or 1)),
        "preco_unitario": max(0.0, float(d.get("preco_unitario") or 0.0)),
        "supermercado": str(d.get("supermercado", "")).strip(),
    }


# --- Leitor Inteligente Estilo Pix (Código de Barras, Câmera, Galeria, QR Code e NFC-e) ---
_SCHEMA_COMPRA = {
    "type": "OBJECT",
    "properties": {
        "supermercado": {"type": "STRING"},
        "codigo_barras": {"type": "STRING"},
        "produto_embalagem": {"type": "STRING"},
        "itens": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "produto": {"type": "STRING"},
                    "categoria": {"type": "STRING"},
                    "quantidade": {"type": "INTEGER"},
                    "preco_unitario": {"type": "NUMBER"},
                },
                "required": ["produto", "categoria", "quantidade", "preco_unitario"],
            },
        },
    },
    "required": ["supermercado", "codigo_barras", "produto_embalagem", "itens"],
}


def _normalizar_itens_ia(dados):
    itens_ok = []
    for it in dados.get("itens", []):
        prod_ok = str(it.get("produto", "")).strip()
        preco_ok = float(it.get("preco_unitario") or 0.0)
        if not prod_ok or preco_ok <= 0:
            continue
        cat_n = normalizar_texto(it.get("categoria", ""))
        cat_ok = next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in cat_n), None) or identificar_categoria_local(prod_ok)
        itens_ok.append({
            "produto": prod_ok,
            "categoria": cat_ok,
            "quantidade": max(1, int(it.get("quantidade") or 1)),
            "preco_unitario": round(preco_ok, 2),
        })
    cod_limpo = re.sub(r"\D", "", str(dados.get("codigo_barras") or ""))
    if len(cod_limpo) not in (8, 12, 13, 14):
        cod_limpo = ""
    return {
        "supermercado": str(dados.get("supermercado", "")).strip(),
        "codigo_barras": cod_limpo,
        "produto_embalagem": str(dados.get("produto_embalagem", "")).strip(),
        "itens": itens_ok,
    }


def tentar_ler_codigos_imagem(img_bytes):
    """Tenta ler QR Code ou Código de Barras localmente se pyzbar ou OpenCV estiver instalado."""
    qr_url, barcode = "", ""
    try:
        from PIL import Image
        import io
        from pyzbar.pyzbar import decode as zbar_decode
        with Image.open(io.BytesIO(img_bytes)) as im:
            for obj in zbar_decode(im):
                txt = obj.data.decode("utf-8", errors="ignore").strip()
                if obj.type == "QRCODE" and txt.lower().startswith(("http://", "https://")):
                    qr_url = txt
                elif txt.isdigit() and len(txt) in (8, 12, 13, 14):
                    barcode = txt
    except Exception:
        pass

    if not qr_url or not barcode:
        try:
            import cv2
            import numpy as np
            arr = np.frombuffer(img_bytes, np.uint8)
            mat = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if mat is not None:
                if not qr_url:
                    q_txt, _, _ = cv2.QRCodeDetector().detectAndDecode(mat)
                    if q_txt and q_txt.strip().lower().startswith(("http://", "https://")):
                        qr_url = q_txt.strip()
                if not barcode and hasattr(cv2, "barcode"):
                    ok_b, infos, _, _ = cv2.barcode.BarcodeDetector().detectAndDecodeWithType(mat)
                    if ok_b:
                        for b in infos:
                            dig = re.sub(r"\D", "", str(b or ""))
                            if len(dig) in (8, 12, 13, 14):
                                barcode = dig
                                break
        except Exception:
            pass
    return qr_url, barcode


def _montar_nome_produto_ean(nome, marca="", qtd=""):
    partes = [str(nome or "").strip()]
    nome_n = normalizar_texto(partes[0])
    if marca and normalizar_texto(marca) not in nome_n:
        partes.append(marca.strip())
    if qtd and normalizar_texto(qtd) not in nome_n:
        partes.append(qtd.strip())
    return " ".join(p for p in partes if p).strip()


@st.cache_data(ttl=86400, show_spinner=False)
def consultar_produto_por_codigo_barras(codigo, api_key="", nome_embalagem=""):
    cod = re.sub(r"\D", "", str(codigo or ""))
    if len(cod) not in (8, 12, 13, 14):
        return None
    http = obter_http_session()

    # 1) Cosmos Bluesoft (opcional via Secret COSMOS_TOKEN — base brasileira de supermercados)
    if cosmos_token := ler_segredo("COSMOS_TOKEN"):
        try:
            r_cos = http.get(
                f"https://api.cosmos.bluesoft.com.br/gtins/{cod}.json",
                headers={"X-Cosmos-Token": cosmos_token, "User-Agent": "ListaiApp/1.0"},
                timeout=5,
            )
            if r_cos.status_code == 200:
                dc = r_cos.json()
                desc = str(dc.get("description") or "").strip()
                marca = str((dc.get("brand") or {}).get("name") or "").strip()
                if desc:
                    nome_ok = _montar_nome_produto_ean(desc, marca)
                    return {"codigo": cod, "produto": nome_ok, "categoria": identificar_categoria(nome_ok, api_key), "fonte": "Cosmos"}
        except Exception:
            pass

    # 2) Open Food Facts e bases irmãs (100% gratuito, sem chave)
    dominios = (
        "https://world.openfoodfacts.org",
        "https://world.openproductsfacts.org",
        "https://world.openbeautyfacts.org",
        "https://world.openpetfoodfacts.org",
    )
    for dom in dominios:
        try:
            resp = http.get(
                f"{dom}/api/v2/product/{cod}.json",
                params={"fields": "product_name,product_name_pt,brands,quantity"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1 and isinstance(data.get("product"), dict):
                    p = data["product"]
                    nome = str(p.get("product_name_pt") or p.get("product_name") or "").strip()
                    marca = str(p.get("brands") or "").split(",")[0].strip()
                    qtd = str(p.get("quantity") or "").strip()
                    if nome:
                        nome_ok = _montar_nome_produto_ean(nome, marca, qtd)
                        return {"codigo": cod, "produto": nome_ok, "categoria": identificar_categoria(nome_ok, api_key), "fonte": "OpenFoodFacts"}
        except Exception:
            continue

    # 3) Fallback com texto da embalagem lido na foto ou IA
    if nome_embalagem and len(nome_embalagem.strip()) >= 3:
        nome_ok = nome_embalagem.strip()
        return {"codigo": cod, "produto": nome_ok, "categoria": identificar_categoria(nome_ok, api_key), "fonte": "Embalagem"}

    return {"codigo": cod, "produto": "", "categoria": "Outros", "fonte": ""}


def _eh_url_publica_segura(url):
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        host = parsed.hostname.lower()
        if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local"):
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


def _extrair_texto_html(raw_html):
    limpo = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html)
    limpo = re.sub(r"(?is)<[^>]+>", " ", limpo)
    limpo = html.unescape(limpo)
    return re.sub(r"\s+", " ", limpo).strip()


def reconhecer_compra_por_foto(img_bytes, api_key, mime_type="image/jpeg"):
    from google.genai import types
    prompt = (
        f"Analise a imagem (pode ser código de barras EAN, embalagem de produto, etiqueta de preço ou cupom fiscal no Brasil). "
        f"1) Se houver preço visível (etiqueta ou nota fiscal), preencha 'itens' com produto, categoria (UMA de: {', '.join(LISTA_CATEGORIAS)}), quantidade (>=1) e preco_unitario (>0), além de 'supermercado' se visível. "
        f"2) Se houver um código de barras visível, extraia TODOS os dígitos dele em 'codigo_barras' (apenas números). "
        f"3) Se for foto de produto/embalagem sem preço, escreva o nome e peso do produto em 'produto_embalagem'."
    )
    resp = obter_gemini_client(api_key).models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=[types.Part.from_bytes(data=img_bytes, mime_type=mime_type), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=_SCHEMA_COMPRA),
    )
    return _normalizar_itens_ia(json.loads(resp.text))


def reconhecer_compra_por_texto_ou_link(entrada, api_key):
    from google.genai import types
    txt = str(entrada or "").strip()
    if txt.lower().startswith(("http://", "https://")):
        if not _eh_url_publica_segura(txt):
            raise ValueError("Link inválido ou não permitido.")
        resp_http = obter_http_session().get(
            txt,
            timeout=9,
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36"},
        )
        if not resp_http.ok:
            raise RuntimeError(f"Portal da nota retornou HTTP {resp_http.status_code}.")
        conteudo_nota = _extrair_texto_html(resp_http.text)[:24000]
    else:
        conteudo_nota = txt[:24000]

    if len(conteudo_nota) < 12:
        return {"supermercado": "", "codigo_barras": "", "produto_embalagem": "", "itens": []}

    prompt = (
        f"Extraia desta Nota Fiscal / Cupom do Brasil o supermercado (ou '') e os itens comprados com: "
        f"produto (nome claro), categoria (UMA de: {', '.join(LISTA_CATEGORIAS)}), quantidade (inteiro >= 1) "
        f"e preco_unitario (preço unitário em reais). Deixe codigo_barras='' e produto_embalagem=''. Conteúdo:\n\n{conteudo_nota}"
    )
    resp = obter_gemini_client(api_key).models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=_SCHEMA_COMPRA),
    )
    return _normalizar_itens_ia(json.loads(resp.text))


def _aplicar_produto_barcode_no_form(info_bc, versao):
    if info_bc and info_bc.get("produto"):
        cat_ok = info_bc["categoria"] if info_bc.get("categoria") in LISTA_CATEGORIAS else "✨ Automática"
        st.session_state.update({
            "valor_produto": info_bc["produto"],
            "valor_quantidade": 1,
            "valor_categoria": cat_ok,
            "aviso_barcode": info_bc,
            "form_versao": versao + 1,
        })
        st.session_state.pop("aviso_voz", None)
        st.rerun()


def _processar_imagem_pix(raw_bytes, api_key, versao):
    hc = hashlib.sha256(raw_bytes).hexdigest()
    if hc == st.session_state.get("ultimo_cupom_hash"):
        return

    with st.spinner("🔍 Lendo código de barras, etiqueta ou cupom..."):
        try:
            img_ocr = preparar_imagem_base(raw_bytes, max_lado=1600, quality=90, melhorar_contraste=True) or raw_bytes
            qr_url, cod_local = tentar_ler_codigos_imagem(img_ocr)

            # 1) Se leu código de barras localmente, já consulta o produto direto (mesmo sem IA!)
            if cod_local:
                info_bc = consultar_produto_por_codigo_barras(cod_local, api_key or "")
                if info_bc and info_bc.get("produto"):
                    st.session_state["ultimo_cupom_hash"] = hc
                    _aplicar_produto_barcode_no_form(info_bc, versao)
                    return

            if not api_key:
                st.warning("Configure a Chave Gemini em **👤 Perfil → Inteligência Artificial** (ou use a aba **🔢 Código**).")
                return

            # 2) Se leu QR Code de NFC-e localmente, tenta buscar os itens
            res_ocr = None
            if qr_url:
                try:
                    res_qr = reconhecer_compra_por_texto_ou_link(qr_url, api_key)
                    if res_qr.get("itens"):
                        res_ocr = res_qr
                except Exception:
                    pass

            # 3) Leitura visual por IA (cupom, etiqueta ou código de barras)
            if res_ocr is None:
                res_ocr = reconhecer_compra_por_foto(img_ocr, api_key, mime_type="image/jpeg")

            # Se encontrou itens com preço (cupom ou etiqueta), abre revisão
            if res_ocr.get("itens"):
                st.session_state["ultimo_cupom_hash"] = hc
                st.session_state["itens_foto_lidos"] = res_ocr
                st.rerun()
                return

            # Se encontrou código de barras (ou produto na embalagem) sem preço
            cod_ia = res_ocr.get("codigo_barras") or cod_local
            prod_emb = res_ocr.get("produto_embalagem", "")
            if cod_ia:
                info_bc = consultar_produto_por_codigo_barras(cod_ia, api_key, nome_embalagem=prod_emb)
                if info_bc and info_bc.get("produto"):
                    st.session_state["ultimo_cupom_hash"] = hc
                    _aplicar_produto_barcode_no_form(info_bc, versao)
                    return
                st.warning(f"Código **{cod_ia}** lido, mas esse produto ainda não está na base gratuita. Digite o nome dele acima!")
                return

            if prod_emb:
                st.session_state["ultimo_cupom_hash"] = hc
                _aplicar_produto_barcode_no_form({"codigo": "Embalagem", "produto": prod_emb, "categoria": identificar_categoria(prod_emb, api_key), "fonte": "Foto"}, versao)
                return

            st.warning("Não consegui identificar código de barras nem preço na foto. Aproxime mais e garanta boa iluminação.")
        except Exception as err_ocr:
            st.warning(f"⚠️ Não foi possível ler a imagem: {err_ocr}")


_SCANNER_HTML = """
<div class="pix-cam-box">
  <div class="pix-cam-view" id="pix-view">
    <video id="pix-video" autoplay playsinline muted></video>
    <div class="pix-cam-overlay">
      <div class="pix-cam-frame" id="pix-frame">
        <div class="pix-cam-laser"></div>
      </div>
    </div>
    <div id="pix-status" class="pix-status">📡 Iniciando câmera traseira...</div>
    <button id="pix-start-btn" class="pix-overlay-btn" style="display:none;" type="button">📷 Ativar Câmera Traseira</button>
  </div>
  <div class="pix-cam-actions">
    <button id="pix-snap" class="pix-btn-primary" type="button">📸 Ler Cupom / Etiqueta</button>
    <button id="pix-flip" class="pix-btn-sec" type="button" title="Trocar câmera">🔄 Câmera</button>
    <button id="pix-torch" class="pix-btn-sec" type="button" style="display:none;" title="Lanterna">🔦</button>
  </div>
</div>
"""

_SCANNER_CSS = """
.pix-cam-box {
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    width: 100%;
}
.pix-cam-view {
    position: relative;
    width: 100%;
    height: 270px;
    background: #0F172A;
    border-radius: 16px;
    overflow: hidden;
    border: 2px solid rgba(11, 78, 162, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
}
.pix-cam-view video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}
.pix-cam-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
}
.pix-cam-frame {
    position: relative;
    width: 78%;
    max-width: 290px;
    height: 132px;
    border-radius: 14px;
    border: 2px solid rgba(255, 255, 255, 0.78);
    box-shadow: 0 0 0 9999px rgba(15, 23, 42, 0.32);
    overflow: hidden;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.pix-cam-frame.pix-ok {
    border-color: #22C55E;
    box-shadow: 0 0 0 9999px rgba(21, 128, 61, 0.28);
}
.pix-cam-laser {
    position: absolute;
    left: 6%;
    right: 6%;
    height: 2.5px;
    border-radius: 999px;
    background: linear-gradient(90deg, transparent, #D91E2A, #3B82F6, transparent);
    animation: pixScan 2s ease-in-out infinite;
}
@keyframes pixScan {
    0%, 100% { top: 14%; }
    50% { top: 84%; }
}
.pix-status {
    position: absolute;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(15, 23, 42, 0.76);
    backdrop-filter: blur(6px);
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
    padding: 5px 12px;
    border-radius: 999px;
    white-space: nowrap;
    max-width: 92%;
    overflow: hidden;
    text-overflow: ellipsis;
}
.pix-overlay-btn {
    position: absolute;
    bottom: 14px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(125deg, #D91E2A, #0B4EA2);
    color: #FFFFFF;
    border: none;
    border-radius: 999px;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
}
.pix-cam-actions {
    display: flex;
    gap: 8px;
    margin-top: 9px;
}
.pix-btn-primary {
    flex: 1;
    background: linear-gradient(125deg, #D91E2A 0%, #5E2B7A 52%, #0B4EA2 100%);
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 800;
    cursor: pointer;
}
.pix-btn-sec {
    background: #FFFFFF;
    color: #0F172A;
    border: 1.5px solid #CBD5E1;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
}
"""

_SCANNER_JS = """
export default function (component) {
  const { parentElement, setTriggerValue } = component;
  const video = parentElement.querySelector("#pix-video");
  const statusEl = parentElement.querySelector("#pix-status");
  const frameEl = parentElement.querySelector("#pix-frame");
  const startBtn = parentElement.querySelector("#pix-start-btn");
  const snapBtn = parentElement.querySelector("#pix-snap");
  const flipBtn = parentElement.querySelector("#pix-flip");
  const torchBtn = parentElement.querySelector("#pix-torch");

  const hostEl = parentElement instanceof ShadowRoot ? parentElement.host : parentElement;
  const detailsEl = hostEl && hostEl.closest ? hostEl.closest("details") : null;

  let stream = null;
  let timerId = null;
  let facingMode = "environment";
  let torchOn = false;
  let detector = null;
  let isNative = false;
  let done = false;
  let destroyed = false;
  let scanCanvas = null;

  function setStatus(txt) {
    if (statusEl) statusEl.textContent = txt;
  }

  function stopCamera() {
    if (timerId) {
      clearTimeout(timerId);
      timerId = null;
    }
    if (stream) {
      stream.getTracks().forEach((t) => {
        try { t.stop(); } catch (_) {}
      });
      stream = null;
    }
    if (video) video.srcObject = null;
    torchOn = false;
    if (torchBtn) torchBtn.style.display = "none";
  }

  async function ensureDetector() {
    if (detector) return detector;
    const fmts = ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "qr_code"];
    if ("BarcodeDetector" in window) {
      try {
        detector = new window.BarcodeDetector({ formats: fmts });
      } catch (_) {
        detector = new window.BarcodeDetector();
      }
      isNative = true;
      return detector;
    }
    try {
      if (!window.__listaiBarcodePolyfill) {
        window.__listaiBarcodePolyfill = import("https://cdn.jsdelivr.net/npm/barcode-detector@3/ponyfill/+esm");
      }
      const mod = await window.__listaiBarcodePolyfill;
      detector = new mod.BarcodeDetector({ formats: fmts });
      isNative = false;
      return detector;
    } catch (_) {
      return null;
    }
  }

  function isValidAutoCode(raw) {
    const val = (raw || "").trim();
    if (!val) return false;
    if (/^https?:\\/\\//i.test(val)) return true;
    const digits = val.replace(/\\D/g, "");
    return val === digits && [8, 12, 13, 14].includes(digits.length);
  }

  async function scanLoop() {
    if (destroyed || done || !stream) return;
    try {
      if (video && video.readyState >= 2 && video.videoWidth > 0) {
        const det = await ensureDetector();
        if (det) {
          let source = video;
          if (!isNative) {
            if (!scanCanvas) scanCanvas = document.createElement("canvas");
            const scale = Math.min(1, 960 / video.videoWidth);
            scanCanvas.width = Math.round(video.videoWidth * scale);
            scanCanvas.height = Math.round(video.videoHeight * scale);
            const ctx = scanCanvas.getContext("2d");
            ctx.drawImage(video, 0, 0, scanCanvas.width, scanCanvas.height);
            source = scanCanvas;
          }
          const codes = await det.detect(source);
          const match = (codes || []).find((c) => isValidAutoCode(c.rawValue));
          if (match) {
            done = true;
            if (frameEl) frameEl.classList.add("pix-ok");
            if (navigator.vibrate) {
              try { navigator.vibrate(80); } catch (_) {}
            }
            setStatus("✅ Código lido! Buscando...");
            stopCamera();
            if (startBtn) {
              startBtn.textContent = "🔄 Ler outro código";
              startBtn.style.display = "inline-block";
            }
            setTriggerValue("scanned", { valor: match.rawValue.trim(), ts: Date.now() });
            return;
          }
        }
      }
    } catch (_) {}
    if (!destroyed && !done && stream) {
      timerId = setTimeout(scanLoop, isNative ? 250 : 380);
    }
  }

  async function startCamera() {
    if (destroyed) return;
    if (detailsEl && !detailsEl.open) return;
    stopCamera();
    done = false;
    if (frameEl) frameEl.classList.remove("pix-ok");
    if (startBtn) startBtn.style.display = "none";
    setStatus(facingMode === "environment" ? "📡 Câmera traseira • Aponte o código" : "🤳 Câmera frontal ativa");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus("Câmera indisponível neste navegador.");
      return;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      if (destroyed) {
        stopCamera();
        return;
      }
      video.srcObject = stream;
      await video.play().catch(() => {});

      const track = stream.getVideoTracks()[0];
      if (track && track.getCapabilities) {
        const caps = track.getCapabilities();
        if (caps && caps.torch && torchBtn) {
          torchBtn.style.display = "inline-block";
        }
      }

      const det = await ensureDetector();
      if (!det) {
        setStatus("📸 Aponte e toque em Ler Cupom / Etiqueta");
      }
      scanLoop();
    } catch (err) {
      setStatus("Toque abaixo para liberar a câmera");
      if (startBtn) {
        startBtn.textContent = "📷 Ativar Câmera Traseira";
        startBtn.style.display = "inline-block";
      }
    }
  }

  if (snapBtn) {
    snapBtn.onclick = () => {
      if (!video || !video.videoWidth) {
        startCamera();
        return;
      }
      const c = document.createElement("canvas");
      const maxW = 1400;
      const scale = Math.min(1, maxW / video.videoWidth);
      c.width = Math.round(video.videoWidth * scale);
      c.height = Math.round(video.videoHeight * scale);
      c.getContext("2d").drawImage(video, 0, 0, c.width, c.height);
      const dataUrl = c.toDataURL("image/jpeg", 0.9);
      done = true;
      setStatus("🔍 Lendo imagem...");
      stopCamera();
      setTriggerValue("captured", { image_b64: dataUrl, ts: Date.now() });
    };
  }

  if (flipBtn) {
    flipBtn.onclick = () => {
      facingMode = facingMode === "environment" ? "user" : "environment";
      startCamera();
    };
  }

  if (torchBtn) {
    torchBtn.onclick = async () => {
      const track = stream && stream.getVideoTracks ? stream.getVideoTracks()[0] : null;
      if (!track || !track.applyConstraints) return;
      torchOn = !torchOn;
      try {
        await track.applyConstraints({ advanced: [{ torch: torchOn }] });
        torchBtn.textContent = torchOn ? "💡" : "🔦";
      } catch (_) {}
    };
  }

  if (startBtn) {
    startBtn.onclick = () => startCamera();
  }

  function onToggle() {
    if (!detailsEl) return;
    if (detailsEl.open) {
      startCamera();
    } else {
      stopCamera();
    }
  }

  if (detailsEl) {
    detailsEl.addEventListener("toggle", onToggle);
    if (detailsEl.open) startCamera();
  } else {
    startCamera();
  }

  return () => {
    destroyed = true;
    if (detailsEl) detailsEl.removeEventListener("toggle", onToggle);
    stopCamera();
  };
}
"""

_SCANNER_PIX_V2 = (
    st.components.v2.component(
        "listai_scanner_pix",
        html=_SCANNER_HTML,
        css=_SCANNER_CSS,
        js=_SCANNER_JS,
    )
    if hasattr(getattr(st, "components", None), "v2")
    else None
)


def _processar_leitura_automatica_pix(valor, api_key, versao):
    txt = str(valor or "").strip()
    if not txt:
        return

    if txt.lower().startswith(("http://", "https://")):
        if not api_key:
            st.warning("QR Code de nota lido! Configure a Chave Gemini em **👤 Perfil → Inteligência Artificial** para extrair os itens.")
            return
        with st.spinner("🧾 QR Code da nota lido! Buscando itens..."):
            try:
                res_qr = reconhecer_compra_por_texto_ou_link(txt, api_key)
                if res_qr.get("itens"):
                    st.session_state["itens_foto_lidos"] = res_qr
                    st.rerun()
                    return
                st.warning("QR Code lido, mas o portal não retornou os itens. Use **📸 Ler Cupom / Etiqueta** para fotografar a nota.")
            except Exception as err_qr:
                st.warning(f"⚠️ Não foi possível abrir esse QR Code ({err_qr}). Use **📸 Ler Cupom / Etiqueta** para fotografar a nota.")
        return

    cod_limpo = re.sub(r"\D", "", txt)
    if len(cod_limpo) in (8, 12, 13, 14):
        with st.spinner(f"🏷️ Código {cod_limpo} lido! Identificando produto..."):
            info_bc = consultar_produto_por_codigo_barras(cod_limpo, api_key or "")
        if info_bc and info_bc.get("produto"):
            _aplicar_produto_barcode_no_form(info_bc, versao)
            return
        st.warning(f"Código **{cod_limpo}** lido automaticamente, mas esse produto ainda não está na base gratuita. Digite o nome dele acima!")


def renderizar_leitor_pix(api_key, merc_atual, versao):
    """Renderiza o leitor estilo Pix (Câmera traseira automática, Galeria, Código de Barras e NFC-e)."""
    lidos_foto = st.session_state.get("itens_foto_lidos")
    with st.expander("📷 Leitor estilo Pix (Código de Barras, Nota ou NFC-e)", expanded=bool(lidos_foto)):
        st.markdown(
            '<div class="listai-pix-banner">'
            '<div><div class="listai-pix-title">⚡ Leitor Inteligente</div>'
            '<div class="listai-pix-sub">Código de barras, etiqueta, cupom fiscal ou link NFC-e</div></div>'
            '<span class="listai-pix-pill">IA • EAN</span></div>',
            unsafe_allow_html=True,
        )

        if not lidos_foto:
            modo = st.radio(
                "Como deseja ler?",
                ["📷 Câmera", "🖼️ Galeria", "🔢 Código", "📋 Link NFC-e"],
                horizontal=True,
                key="leitor_pix_modo",
                label_visibility="collapsed",
            )

            if modo == "📷 Câmera":
                st.caption("Aponte a **câmera traseira** para ler código de barras/QR automaticamente, ou toque em **📸 Ler Cupom / Etiqueta**:")
                if _SCANNER_PIX_V2 is not None:
                    res_cam = _SCANNER_PIX_V2(
                        key=f"scanner_pix_v2_{versao}",
                        on_scanned_change=lambda: None,
                        on_captured_change=lambda: None,
                    )
                    if scanned := getattr(res_cam, "scanned", None):
                        ts = scanned.get("ts")
                        if ts and ts != st.session_state.get("_pix_last_ts"):
                            st.session_state["_pix_last_ts"] = ts
                            _processar_leitura_automatica_pix(scanned.get("valor", ""), api_key, versao)
                    if captured := getattr(res_cam, "captured", None):
                        ts = captured.get("ts")
                        if ts and ts != st.session_state.get("_pix_last_ts"):
                            st.session_state["_pix_last_ts"] = ts
                            b64 = str(captured.get("image_b64") or "")
                            if "," in b64:
                                b64 = b64.split(",", 1)[1]
                            if b64:
                                _processar_imagem_pix(base64.b64decode(b64), api_key, versao)
                else:
                    with st.container(key="leitor_pix_cam"):
                        cam_foto = st.camera_input("Câmera do Leitor", key=f"cam_cupom_{versao}", label_visibility="collapsed")
                    if cam_foto is not None:
                        _processar_imagem_pix(cam_foto.getvalue(), api_key, versao)

            elif modo == "🖼️ Galeria":
                with st.container(key="leitor_pix_gal"):
                    f_cup = st.file_uploader("Escolha uma foto (JPG, PNG ou WEBP)", type=["jpg", "jpeg", "png", "webp"], key=f"up_cupom_{versao}")
                if f_cup is not None:
                    _processar_imagem_pix(f_cup.getvalue(), api_key, versao)

            elif modo == "🔢 Código":
                st.caption("Digite os números do código de barras (ou use um leitor USB/Bluetooth) para identificar o produto grátis:")
                cod_dig = st.text_input("Código de barras (EAN)", placeholder="Ex: 7891910000197", key=f"ean_in_{versao}", label_visibility="collapsed")
                if st.button("🔎 Buscar produto pelo código", type="primary", use_container_width=True, key=f"btn_ean_{versao}"):
                    cod_limpo = re.sub(r"\D", "", cod_dig)
                    if len(cod_limpo) not in (8, 12, 13, 14):
                        st.warning("Informe um código válido (8, 12, 13 ou 14 dígitos).")
                    else:
                        with st.spinner("Consultando produto..."):
                            info_bc = consultar_produto_por_codigo_barras(cod_limpo, api_key or "")
                        if info_bc and info_bc.get("produto"):
                            _aplicar_produto_barcode_no_form(info_bc, versao)
                        else:
                            st.warning(f"Código **{cod_limpo}** não encontrado na base gratuita. Digite o nome do produto acima.")

            else:
                st.caption("Igual ao **Pix Copia e Cola**: cole o link do QR Code da Nota Fiscal (SEFAZ) ou o texto do cupom.")
                entrada_nfce = st.text_area(
                    "Link NFC-e ou texto da nota",
                    placeholder="https://nfce.fazenda... ou cole o texto dos itens do cupom",
                    height=88,
                    key=f"nfce_in_{versao}",
                    label_visibility="collapsed",
                )
                if st.button("🔍 Ler Nota / Link", type="primary", use_container_width=True, key=f"btn_ler_nfce_{versao}"):
                    if not entrada_nfce.strip():
                        st.warning("Cole um link NFC-e ou texto do cupom.")
                    elif not api_key:
                        st.warning("Configure a Chave Gemini em **👤 Perfil → Inteligência Artificial**.")
                    else:
                        with st.spinner("Consultando e extraindo itens..."):
                            try:
                                res_txt = reconhecer_compra_por_texto_ou_link(entrada_nfce, api_key)
                                if not res_txt.get("itens"):
                                    st.warning("Nenhum item com preço encontrado. Tente fotografar a nota pela aba **📷 Câmera** ou **🖼️ Galeria**.")
                                else:
                                    st.session_state["itens_foto_lidos"] = res_txt
                                    st.rerun()
                            except Exception as err_nfce:
                                st.warning(f"⚠️ Não foi possível ler esse link/texto: {err_nfce} — tente pela **📷 Câmera**.")
            return None

        # --- Revisão e Edição dos Itens Lidos (Etiqueta / Cupom com preço) ---
        merc_padrao = lidos_foto.get("supermercado") or merc_atual or "Supermercado"
        st.success(f"📸 **{len(lidos_foto['itens'])} item(ns)** identificado(s)! Confira abaixo antes de salvar:")
        merc_edit = st.text_input("🏪 Supermercado", value=merc_padrao, key=f"pix_merc_ed_{versao}").strip() or merc_atual or "Supermercado"

        selecionados = []
        editar_inline = len(lidos_foto["itens"]) <= 3
        for idx_f, it_f in enumerate(lidos_foto["itens"]):
            ico_f = ICONES_CATEGORIA.get(it_f["categoria"], "📦")
            sub_it = it_f["quantidade"] * it_f["preco_unitario"]
            lbl_f = f"{ico_f} **{it_f['produto']}** (x{it_f['quantidade']}) — {formatar_reais(it_f['preco_unitario'])}/un · Total {formatar_reais(sub_it)}"
            marcado = st.checkbox(lbl_f, value=True, key=f"chk_foto_item_{versao}_{idx_f}")
            if marcado:
                if editar_inline:
                    with st.container(key=f"edit_qp_pix_{idx_f}"):
                        cq_p, cp_p = st.columns(2)
                        q_ok = cq_p.number_input("Qtd", min_value=1, value=int(it_f["quantidade"]), step=1, key=f"pix_q_{versao}_{idx_f}")
                        p_ok = cp_p.number_input("Preço (R$)", min_value=0.01, value=float(it_f["preco_unitario"]), step=0.01, format="%.2f", key=f"pix_p_{versao}_{idx_f}")
                    selecionados.append({**it_f, "quantidade": int(q_ok), "preco_unitario": float(p_ok)})
                else:
                    selecionados.append(it_f)

        if not editar_inline:
            with st.expander("✏️ Ajustar quantidade ou preço de um item"):
                ops_aj = {i: f"{it['produto']} (x{it['quantidade']} · {formatar_reais(it['preco_unitario'])})" for i, it in enumerate(lidos_foto["itens"])}
                i_aj = st.selectbox("Item:", list(ops_aj.keys()), format_func=lambda x: ops_aj[x], key=f"pix_sel_aj_{versao}")
                it_sel = lidos_foto["itens"][i_aj]
                aj_nome = st.text_input("Nome", value=it_sel["produto"], key=f"pix_aj_n_{versao}_{i_aj}")
                with st.container(key="edit_qp_pix_lote"):
                    cq_l, cp_l = st.columns(2)
                    aj_q = cq_l.number_input("Qtd", min_value=1, value=int(it_sel["quantidade"]), step=1, key=f"pix_aj_q_{versao}_{i_aj}")
                    aj_p = cp_l.number_input("Preço (R$)", min_value=0.01, value=float(it_sel["preco_unitario"]), step=0.01, format="%.2f", key=f"pix_aj_p_{versao}_{i_aj}")
                if st.button("💾 Aplicar ajuste", use_container_width=True, key=f"pix_btn_aj_{versao}"):
                    lidos_foto["itens"][i_aj].update({"produto": aj_nome.strip() or it_sel["produto"], "quantidade": int(aj_q), "preco_unitario": float(aj_p)})
                    st.rerun()

        tot_prev = sum(it["quantidade"] * it["preco_unitario"] for it in selecionados)
        st.caption(f"💰 Soma dos selecionados: **{formatar_reais(tot_prev)}**")

        with st.container(key="kpi_2cols_foto_ocr"):
            b_ok, b_no = st.columns(2)
            confirmou = b_ok.button(f"✅ Salvar ({len(selecionados)})", type="primary", disabled=(not selecionados), use_container_width=True, key="btn_salvar_foto_itens")
            descartou = b_no.button("✖️ Descartar", use_container_width=True, key="btn_descartar_foto_itens")

        if descartou:
            st.session_state.pop("itens_foto_lidos", None)
            st.session_state.pop("ultimo_cupom_hash", None)
            st.session_state["form_versao"] = versao + 1
            st.rerun()
        if confirmou:
            return selecionados, merc_edit
    return None