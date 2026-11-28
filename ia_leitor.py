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


# --- Leitor Inteligente Estilo Pix (Câmera, Galeria, QR Code e Link NFC-e) ---
_SCHEMA_COMPRA = {
    "type": "OBJECT",
    "properties": {
        "supermercado": {"type": "STRING"},
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
    "required": ["supermercado", "itens"],
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
    return {"supermercado": str(dados.get("supermercado", "")).strip(), "itens": itens_ok}


def tentar_ler_qrcode_imagem(img_bytes):
    """Tenta ler um QR Code localmente caso OpenCV esteja instalado (opcional)."""
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(img_bytes, np.uint8)
        mat = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if mat is None:
            return ""
        det = cv2.QRCodeDetector()
        texto, _, _ = det.detectAndDecode(mat)
        return (texto or "").strip()
    except Exception:
        return ""


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
        f"Analise a imagem (etiqueta de preço de gôndola ou cupom/nota fiscal no Brasil). "
        f"Extraia o nome do supermercado (se visível, senão '') e todos os itens com: "
        f"produto (nome claro e legível), categoria (UMA de: {', '.join(LISTA_CATEGORIAS)}), "
        f"quantidade (inteiro >= 1) e preco_unitario (preço de 1 unidade em reais). "
        f"Ignore subtotais, descontos totais, troco e tributos."
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
        return {"supermercado": "", "itens": []}

    prompt = (
        f"Extraia desta Nota Fiscal / Cupom do Brasil o supermercado (ou '') e os itens comprados com: "
        f"produto (nome claro), categoria (UMA de: {', '.join(LISTA_CATEGORIAS)}), quantidade (inteiro >= 1) "
        f"e preco_unitario (preço unitário em reais). Conteúdo:\n\n{conteudo_nota}"
    )
    resp = obter_gemini_client(api_key).models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=_SCHEMA_COMPRA),
    )
    return _normalizar_itens_ia(json.loads(resp.text))


def _processar_imagem_pix(raw_bytes, api_key):
    hc = hashlib.sha256(raw_bytes).hexdigest()
    if hc == st.session_state.get("ultimo_cupom_hash"):
        return
    if not api_key:
        st.warning("Configure a Chave Gemini em **👤 Perfil → Inteligência Artificial** para ler fotos com IA.")
        return

    with st.spinner("🔍 Lendo etiqueta, QR Code ou cupom fiscal..."):
        try:
            img_ocr = preparar_imagem_base(raw_bytes, max_lado=1600, quality=90, melhorar_contraste=True) or raw_bytes
            res_ocr = None

            if qr_texto := tentar_ler_qrcode_imagem(img_ocr):
                if qr_texto.lower().startswith(("http://", "https://")):
                    try:
                        res_qr = reconhecer_compra_por_texto_ou_link(qr_texto, api_key)
                        if res_qr.get("itens"):
                            res_ocr = res_qr
                    except Exception:
                        pass

            if res_ocr is None:
                res_ocr = reconhecer_compra_por_foto(img_ocr, api_key, mime_type="image/jpeg")

            if not res_ocr.get("itens"):
                st.warning("Não consegui identificar produtos com preço nessa imagem. Aproxime mais ou melhore a iluminação.")
                return

            st.session_state["ultimo_cupom_hash"] = hc
            st.session_state["itens_foto_lidos"] = res_ocr
            st.rerun()
        except Exception as err_ocr:
            st.warning(f"⚠️ Não foi possível ler a imagem: {err_ocr}")


def renderizar_leitor_pix(api_key, merc_atual, versao):
    """Renderiza o leitor estilo Pix (Câmera, Galeria e Link NFC-e). Retorna (itens, supermercado) ao confirmar."""
    lidos_foto = st.session_state.get("itens_foto_lidos")
    with st.expander("📷 Leitor estilo Pix (Câmera, Nota Fiscal ou QR/NFC-e)", expanded=bool(lidos_foto)):
        st.markdown(
            '<div class="listai-pix-banner">'
            '<div><div class="listai-pix-title">⚡ Leitor Inteligente</div>'
            '<div class="listai-pix-sub">Aponte para a etiqueta, cupom fiscal ou cole o link NFC-e</div></div>'
            '<span class="listai-pix-pill">IA • PIX</span></div>',
            unsafe_allow_html=True,
        )

        if not lidos_foto:
            modo = st.radio(
                "Como deseja ler?",
                ["📷 Câmera", "🖼️ Galeria", "📋 Link NFC-e"],
                horizontal=True,
                key="leitor_pix_modo",
                label_visibility="collapsed",
            )

            if modo == "📷 Câmera":
                st.caption("Enquadre o cupom fiscal, QR Code ou etiqueta de preço dentro da moldura verde:")
                with st.container(key="leitor_pix_cam"):
                    cam_foto = st.camera_input("Câmera do Leitor", key=f"cam_cupom_{versao}", label_visibility="collapsed")
                if cam_foto is not None:
                    _processar_imagem_pix(cam_foto.getvalue(), api_key)

            elif modo == "🖼️ Galeria":
                with st.container(key="leitor_pix_gal"):
                    f_cup = st.file_uploader("Escolha uma foto da galeria (JPG, PNG ou WEBP)", type=["jpg", "jpeg", "png", "webp"], key=f"up_cupom_{versao}")
                if f_cup is not None:
                    _processar_imagem_pix(f_cup.getvalue(), api_key)

            else:
                st.caption("Igual ao **Pix Copia e Cola**: cole o link do QR Code da Nota Fiscal (SEFAZ) ou o texto copiado do cupom.")
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

        # --- Revisão e Edição dos Itens Lidos ---
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