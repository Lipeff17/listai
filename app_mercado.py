from datetime import date
import hashlib
import json
import math
import os
import random
import secrets
import unicodedata
import urllib.parse

import pandas as pd
import requests
import streamlit as st
from google import genai
from google.genai import types

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

st.set_page_config(
    page_title="Listaí — Preços e Compras",
    page_icon="🛒",
    layout="wide",
)

# --- Estilo visual mais moderno ---
st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            background-color: rgba(128, 128, 128, 0.08);
            border: 1px solid rgba(128, 128, 128, 0.18);
            padding: 12px 16px;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Configurações e Constantes ---
ARQUIVO_CSV = "compras_mercado.csv"
ARQUIVO_COMUNIDADE = "precos_comunidade.csv"
ARQUIVO_MERCADOS = "supermercados.json"
ARQUIVO_USUARIOS = "usuarios.json"

COLUNAS = [
    "Data", "Região", "Supermercado", "Produto",
    "Categoria", "Quantidade", "Preço Unitário", "Total",
]
COLUNAS_COMUNIDADE = [
    "Data", "Região", "Supermercado", "Produto",
    "Categoria", "Preço Unitário", "Usuário",
]

# Coloque aqui os usuários/e-mails que podem ver o Painel Admin
USUARIOS_ADMIN = {"admin", "seuemail@gmail.com"}

OVERPASS_SERVERS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

ANUNCIOS = [
    {
        "titulo": "🔥 Ofertas de Supermercado na Amazon",
        "descricao": "Descontos em limpeza, café, bebidas e despensa com entrega rápida.",
        "texto_botao": "Ver ofertas",
        "url": "https://www.amazon.com.br/",
    },
    {
        "titulo": "🛒 Mercado Livre — Compras do Mês",
        "descricao": "Compare preços e aproveite cupons e frete grátis na sua compra.",
        "texto_botao": "Abrir ofertas",
        "url": "https://www.mercadolivre.com.br/",
    },
    {
        "titulo": "🏷️ Achadinhos e Ofertas na Shopee",
        "descricao": "Utilidades domésticas e itens para casa com super desconto.",
        "texto_botao": "Conferir",
        "url": "https://shopee.com.br/",
    },
]

LISTA_CATEGORIAS = [
    "Alimentos", "Bebidas", "Hortifruti", "Açougue e Peixaria",
    "Frios e Laticínios", "Padaria", "Limpeza", "Higiene Pessoal",
    "Pet Shop", "Utilidades Domésticas", "Outros",
]

CATEGORIAS_FALLBACK = {
    "Limpeza": [
        "agua sanitaria", "papel higienico", "detergente", "sabao",
        "desinfetante", "amaciante", "esponja", "alvejante",
        "limpador", "vassoura", "rodo",
    ],
    "Bebidas": [
        "agua", "refrigerante", "suco", "cerveja", "vinho",
        "leite", "cafe", "cha", "energetico", "achocolatado",
    ],
    "Hortifruti": [
        "banana", "maca", "laranja", "uva", "mamao",
        "melancia", "abacaxi", "tomate", "cebola", "batata",
        "cenoura", "alface", "couve", "pepino", "abobora",
    ],
    "Alimentos": [
        "arroz", "feijao", "macarrao", "carne", "frango",
        "peixe", "ovo", "farinha", "acucar", "sal",
        "biscoito", "bolacha", "pao", "queijo", "presunto",
        "manteiga", "margarina", "iogurte", "oleo",
        "molho", "milho", "ervilha",
    ],
}

TRADUCAO_LOJA = {
    "supermarket": "Supermercado",
    "wholesale": "Atacarejo",
    "convenience": "Mercearia / Minimercado",
    "greengrocer": "Hortifruti / Sacolão",
}


# --- Sessão HTTP reutilizável (mais rápida) ---
@st.cache_resource
def obter_http_session():
    sess = requests.Session()
    sess.headers.update({"User-Agent": "ListaiApp/1.0"})
    return sess


# --- Autenticação (Google OAuth + Usuário/Senha) ---
def google_auth_configurado():
    try:
        return "auth" in st.secrets and bool(st.secrets["auth"].get("client_id"))
    except Exception:
        return False


def usuario_google_logado():
    return google_auth_configurado() and bool(getattr(st.user, "is_logged_in", False))


def gerar_hash_senha(senha, salt=None):
    salt = salt or secrets.token_hex(16)
    hash_hex = hashlib.sha256((salt + senha).encode("utf-8")).hexdigest()
    return f"{salt}${hash_hex}"


def verificar_senha(senha_digitada, senha_salva):
    if "$" not in senha_salva:
        return False
    salt, hash_esperado = senha_salva.split("$", 1)
    hash_digitado = hashlib.sha256((salt + senha_digitada).encode("utf-8")).hexdigest()
    return secrets.compare_digest(hash_digitado, hash_esperado)


@st.cache_data(show_spinner=False)
def carregar_usuarios():
    if os.path.exists(ARQUIVO_USUARIOS) and os.path.getsize(ARQUIVO_USUARIOS) > 0:
        try:
            with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass

    iniciais = {
        "teste": {
            "tipo": "senha",
            "hash": gerar_hash_senha("1234"),
            "nome": "Conta Teste",
            "criado_em": date.today().isoformat(),
        }
    }
    salvar_usuarios(iniciais)
    return iniciais


def salvar_usuarios(usuarios):
    with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)
    carregar_usuarios.clear()


def registrar_usuario_google_se_novo():
    email = (getattr(st.user, "email", None) or "").strip().lower()
    nome = (getattr(st.user, "name", None) or email).strip()
    if not email:
        return "usuario_google", "Usuário Google"

    usuarios = carregar_usuarios().copy()
    if email not in usuarios:
        usuarios[email] = {
            "tipo": "google",
            "nome": nome,
            "criado_em": date.today().isoformat(),
        }
        salvar_usuarios(usuarios)
    return email, nome


def exibir_tela_login():
    st.title("🛒 Listaí — Controle e Preços da Região")
    st.subheader("🔐 Acesse ou crie sua conta")

    _, col_centro, _ = st.columns([1, 2, 1])
    with col_centro:
        if google_auth_configurado():
            st.button(
                "🔵 Entrar ou criar conta com Google (Gmail)",
                on_click=st.login,
                type="primary",
                use_container_width=True,
            )
        else:
            st.info(
                "💡 Para ativar o botão **Entrar com Gmail**, configure `[auth]` "
                "no arquivo `.streamlit/secrets.toml`."
            )

        st.divider()
        aba_entrar, aba_cadastrar = st.tabs(["Entrar com senha", "Criar conta com senha"])
        usuarios = carregar_usuarios()

        with aba_entrar:
            with st.form("form_login"):
                usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
                senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                if st.form_submit_button("Entrar", use_container_width=True):
                    user_limpo = usuario.strip().lower()
                    registro = usuarios.get(user_limpo)

                    if registro is None:
                        st.error("Usuário ou senha incorretos.")
                    elif isinstance(registro, dict) and registro.get("tipo") == "google":
                        st.warning("Conta vinculada ao Gmail. Use o botão azul acima.")
                    else:
                        hash_salvo = registro["hash"] if isinstance(registro, dict) else registro
                        if verificar_senha(senha, hash_salvo):
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_logado"] = user_limpo
                            st.session_state["nome_usuario"] = (
                                registro.get("nome", user_limpo)
                                if isinstance(registro, dict)
                                else user_limpo
                            )
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")

            st.caption("Conta padrão para teste — Usuário: `teste` | Senha: `1234`")

        with aba_cadastrar:
            with st.form("form_cadastro"):
                novo_user = st.text_input("Novo Usuário", placeholder="Ex: maria")
                nova_senha = st.text_input("Nova Senha", type="password", placeholder="Mínimo 4 caracteres")
                conf_senha = st.text_input("Confirmar Senha", type="password")
                if st.form_submit_button("Criar conta", use_container_width=True):
                    novo_limpo = novo_user.strip().lower()
                    if not novo_limpo:
                        st.warning("Digite um nome de usuário.")
                    elif novo_limpo in usuarios:
                        st.error("Esse usuário já existe. Escolha outro.")
                    elif len(nova_senha) < 4:
                        st.warning("A senha deve ter pelo menos 4 caracteres.")
                    elif nova_senha != conf_senha:
                        st.error("As senhas não coincidem.")
                    else:
                        usuarios_edit = usuarios.copy()
                        usuarios_edit[novo_limpo] = {
                            "tipo": "senha",
                            "hash": gerar_hash_senha(nova_senha),
                            "nome": novo_limpo,
                            "criado_em": date.today().isoformat(),
                        }
                        salvar_usuarios(usuarios_edit)
                        st.success("Conta criada! Vá para a aba **Entrar com senha**.")


# --- Bloqueio antes do Login ---
logado_google = usuario_google_logado()
logado_local = bool(st.session_state.get("autenticado", False))

if not (logado_google or logado_local):
    exibir_tela_login()
    st.stop()

if logado_google:
    usuario_atual, nome_usuario = registrar_usuario_google_se_novo()
    st.session_state["usuario_logado"] = usuario_atual
    st.session_state["nome_usuario"] = nome_usuario
else:
    usuario_atual = st.session_state.get("usuario_logado", "usuario")
    nome_usuario = st.session_state.get("nome_usuario", usuario_atual)


# --- Localização e Supermercados (OpenStreetMap + Failover) ---
def calcular_distancia_metros(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return int(2 * 6371000 * math.asin(math.sqrt(a)))


def consultar_photon_mercados(lat, lon, raio_metros):
    http = obter_http_session()
    delta_lat = raio_metros / 111320.0
    delta_lon = raio_metros / (111320.0 * max(0.2, abs(math.cos(math.radians(lat)))))
    bbox = f"{lon - delta_lon},{lat - delta_lat},{lon + delta_lon},{lat + delta_lat}"

    encontrados = {}
    algum_sucesso = False

    for termo in ["supermercado", "atacadao", "mercado"]:
        try:
            resp = http.get(
                "https://photon.komoot.io/api/",
                params={"q": termo, "lat": lat, "lon": lon, "bbox": bbox, "limit": 25},
                timeout=8,
            )
            if resp.status_code != 200:
                continue
            algum_sucesso = True

            for feat in resp.json().get("features", []):
                props = feat.get("properties", {})
                coords = feat.get("geometry", {}).get("coordinates", [])
                if len(coords) < 2:
                    continue
                if props.get("osm_key") != "shop" and props.get("osm_value") not in TRADUCAO_LOJA:
                    continue
                nome = (props.get("name") or "").strip()
                if not nome:
                    continue

                elon, elat = float(coords[0]), float(coords[1])
                dist = calcular_distancia_metros(lat, lon, elat, elon)
                if dist > raio_metros:
                    continue

                tipo = TRADUCAO_LOJA.get(props.get("osm_value", ""), "Supermercado")
                rua = props.get("street", "")
                bairro = props.get("district") or props.get("locality") or ""
                endereco = ", ".join([p for p in [rua, bairro] if p]) or "-"
                chave = f"{nome}|{round(elat, 4)}|{round(elon, 4)}"

                if chave not in encontrados or dist < encontrados[chave]["Distância (m)"]:
                    encontrados[chave] = {
                        "Supermercado": nome,
                        "Tipo": tipo,
                        "Endereço": endereco,
                        "Distância (m)": dist,
                        "lat": elat,
                        "lon": elon,
                    }
        except Exception:
            continue

    return sorted(encontrados.values(), key=lambda x: x["Distância (m)"]) if algum_sucesso else None


@st.cache_data(ttl=600, show_spinner=False)
def consultar_overpass_mercados(lat, lon, raio_metros):
    http = obter_http_session()
    query = f"""
    [out:json][timeout:10];
    (
      nw(around:{raio_metros},{lat},{lon})["shop"="supermarket"];
      nw(around:{raio_metros},{lat},{lon})["shop"="wholesale"];
      nw(around:{raio_metros},{lat},{lon})["shop"="convenience"];
      nw(around:{raio_metros},{lat},{lon})["shop"="greengrocer"];
    );
    out center tags;
    """

    dados_json = None
    for servidor in OVERPASS_SERVERS:
        try:
            resp = http.post(servidor, data={"data": query}, timeout=10)
            if resp.status_code == 200:
                dados_json = resp.json()
                break
        except Exception:
            continue

    if dados_json is not None:
        encontrados = {}
        for elem in dados_json.get("elements", []):
            tags = elem.get("tags", {})
            nome = (tags.get("name") or tags.get("brand") or "").strip()
            if not nome:
                continue

            elat = elem.get("lat") or elem.get("center", {}).get("lat")
            elon = elem.get("lon") or elem.get("center", {}).get("lon")
            if elat is None or elon is None:
                continue

            elat, elon = float(elat), float(elon)
            dist = calcular_distancia_metros(lat, lon, elat, elon)
            tipo = TRADUCAO_LOJA.get(tags.get("shop", "supermarket"), "Supermercado")

            rua = tags.get("addr:street", "")
            numero = tags.get("addr:housenumber", "")
            bairro = tags.get("addr:suburb", "")
            endereco = ", ".join([p for p in [f"{rua} {numero}".strip(), bairro] if p]) or "-"
            chave = f"{nome}|{round(elat, 4)}|{round(elon, 4)}"

            if chave not in encontrados or dist < encontrados[chave]["Distância (m)"]:
                encontrados[chave] = {
                    "Supermercado": nome,
                    "Tipo": tipo,
                    "Endereço": endereco,
                    "Distância (m)": dist,
                    "lat": elat,
                    "lon": elon,
                }
        return sorted(encontrados.values(), key=lambda x: x["Distância (m)"])

    res_photon = consultar_photon_mercados(lat, lon, raio_metros)
    if res_photon is not None:
        return res_photon

    raise RuntimeError("Servidores de mapa ocupados no momento. Tente novamente em instantes.")


@st.cache_data(ttl=600, show_spinner=False)
def buscar_regiao_e_mercados_proximos(lat, lon):
    http = obter_http_session()
    regiao = ""
    try:
        resp_geo = http.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "accept-language": "pt-BR"},
            timeout=6,
        )
        if resp_geo.status_code == 200:
            addr = resp_geo.json().get("address", {})
            cidade = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village") or ""
            bairro = addr.get("suburb") or addr.get("neighbourhood") or addr.get("city_district") or ""
            regiao = f"{cidade} - {bairro}" if (cidade and bairro) else (cidade or bairro)
    except Exception:
        pass

    regiao = regiao or "Minha Região (GPS)"
    lista_completa = consultar_overpass_mercados(lat, lon, 3000)
    mercados_proximos, vistos = [], set()
    for item in lista_completa:
        if item["Supermercado"] not in vistos:
            vistos.add(item["Supermercado"])
            mercados_proximos.append((item["Supermercado"], item["Distância (m)"]))

    return regiao, mercados_proximos, lista_completa


@st.cache_data(ttl=600, show_spinner=False)
def buscar_supermercados_por_regiao(texto_regiao, raio_metros=3000):
    http = obter_http_session()
    resp_geo = http.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": texto_regiao, "countrycodes": "br", "format": "json", "limit": 1, "accept-language": "pt-BR"},
        timeout=8,
    )
    if resp_geo.status_code != 200 or not resp_geo.json():
        return None, []

    lugar = resp_geo.json()[0]
    mercados = consultar_overpass_mercados(float(lugar["lat"]), float(lugar["lon"]), raio_metros)
    return lugar.get("display_name", texto_regiao), mercados


# --- Helpers ---
def normalizar_texto(texto):
    texto = str(texto).lower().strip()
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def exibir_banner_anuncio():
    anuncio = random.choice(ANUNCIOS)
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.caption("📢 Publicidade • Parceiro Listaí")
            st.markdown(f"**{anuncio['titulo']}** — {anuncio['descricao']}")
        with c2:
            st.write("")
            st.link_button(anuncio["texto_botao"], anuncio["url"], use_container_width=True)


def exibir_tabela_e_mapa_regiao(lista_mercados, msg_sucesso):
    df_m = pd.DataFrame(lista_mercados)
    st.success(msg_sucesso)
    col_l, col_m = st.columns([3, 2])
    with col_l:
        st.dataframe(
            df_m[["Supermercado", "Tipo", "Endereço", "Distância (m)"]],
            hide_index=True,
            use_container_width=True,
        )
    with col_m:
        st.map(df_m, latitude="lat", longitude="lon")


# --- Supermercados Salvos ---
@st.cache_data(show_spinner=False)
def carregar_mercados():
    if os.path.exists(ARQUIVO_MERCADOS) and os.path.getsize(ARQUIVO_MERCADOS) > 0:
        try:
            with open(ARQUIVO_MERCADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, dict) and dados:
                    return dados
        except json.JSONDecodeError:
            pass

    iniciais = {"Centro (Exemplo)": ["Atacadão", "Carrefour", "Supermercado Local"]}
    salvar_mercados(iniciais)
    return iniciais


def salvar_mercados(mercados):
    with open(ARQUIVO_MERCADOS, "w", encoding="utf-8") as f:
        json.dump(mercados, f, ensure_ascii=False, indent=2)
    carregar_mercados.clear()


def registrar_varios_mercados(regiao, nomes_supermercados):
    regiao = regiao.strip()
    if not regiao or not nomes_supermercados:
        return 0

    mercados = carregar_mercados().copy()
    lista_atual = set(mercados.get(regiao, []))
    antes = len(lista_atual)
    for nome in nomes_supermercados:
        if nome.strip():
            lista_atual.add(nome.strip())

    if len(lista_atual) > antes or regiao not in mercados:
        mercados[regiao] = sorted(lista_atual)
        salvar_mercados(mercados)
    return len(lista_atual) - antes


# --- IA (Categorização + Voz) ---
def identificar_categoria_local(produto):
    prod_norm = normalizar_texto(produto)
    for cat, palavras in CATEGORIAS_FALLBACK.items():
        if any(normalizar_texto(p) in prod_norm for p in palavras):
            return cat
    return "Outros"


@st.cache_data(ttl=86400, show_spinner=False)
def classificar_com_ia(produto_normalizado, api_key):
    client = genai.Client(api_key=api_key)
    instrucao = (
        "Você é um classificador automático de produtos de supermercado no Brasil. "
        "Identifique o produto (mesmo marcas ou apelidos) e responda APENAS com o nome exato "
        f"de UMA destas categorias: {', '.join(LISTA_CATEGORIAS)}. Sem pontuação ou explicações."
    )
    resp = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"Produto: {produto_normalizado}",
        config=types.GenerateContentConfig(system_instruction=instrucao),
    )
    limpa = normalizar_texto(resp.text)
    for cat in LISTA_CATEGORIAS:
        if normalizar_texto(cat) in limpa:
            return cat
    return "Outros"


def identificar_categoria(produto, api_key):
    if not api_key:
        return identificar_categoria_local(produto), "Local"
    try:
        return classificar_com_ia(normalizar_texto(produto), api_key), "API Gemini"
    except Exception as erro:
        st.warning(f"API indisponível ({erro}). Usando regra local.")
        return identificar_categoria_local(produto), "Local"


def reconhecer_produto_por_voz(audio_bytes, api_key):
    client = genai.Client(api_key=api_key)
    schema = {
        "type": "OBJECT",
        "properties": {
            "transcricao": {"type": "STRING"},
            "produto": {"type": "STRING"},
            "categoria": {"type": "STRING"},
            "quantidade": {"type": "INTEGER"},
            "preco_unitario": {"type": "NUMBER"},
            "supermercado": {"type": "STRING"},
        },
        "required": ["transcricao", "produto", "categoria", "quantidade", "preco_unitario", "supermercado"],
    }
    prompt = (
        "Ouça o áudio em português do Brasil sobre uma compra de supermercado e extraia: "
        "transcricao (texto falado), produto (nome limpo), "
        f"categoria (exatamente uma de: {', '.join(LISTA_CATEGORIAS)}), "
        "quantidade (inteiro, 1 se não falar), preco_unitario (reais, 0 se não falar), "
        "supermercado (nome se falar, ou '')."
    )
    resp = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=[types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema),
    )
    dados = json.loads(resp.text)

    cat_norm = normalizar_texto(dados.get("categoria", ""))
    cat_final = next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in cat_norm), "Outros")

    return {
        "transcricao": str(dados.get("transcricao", "")).strip(),
        "produto": str(dados.get("produto", "")).strip(),
        "categoria": cat_final,
        "quantidade": max(1, int(dados.get("quantidade") or 1)),
        "preco_unitario": max(0.0, float(dados.get("preco_unitario") or 0.0)),
        "supermercado": str(dados.get("supermercado", "")).strip(),
    }


# --- Persistência em Cache (leitura instantânea) ---
def _ler_csv_seguro(caminho, colunas, cols_num):
    if not (os.path.exists(caminho) and os.path.getsize(caminho) > 0):
        return pd.DataFrame(columns=colunas)
    df = pd.read_csv(caminho)
    alterou = False
    for col in colunas:
        if col not in df.columns:
            alterou = True
            df[col] = 0.0 if col in cols_num else ""
    df = df[colunas]
    for col in cols_num:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if alterou:
        df.to_csv(caminho, index=False)
    return df


@st.cache_data(show_spinner=False)
def carregar_dados():
    return _ler_csv_seguro(ARQUIVO_CSV, COLUNAS, ["Quantidade", "Preço Unitário", "Total"])


@st.cache_data(show_spinner=False)
def carregar_comunidade():
    return _ler_csv_seguro(ARQUIVO_COMUNIDADE, COLUNAS_COMUNIDADE, ["Preço Unitário"])


def salvar_linha_csv(caminho, novo_df, loader_fn):
    atual = loader_fn()
    pd.concat([atual, novo_df], ignore_index=True).to_csv(caminho, index=False)
    loader_fn.clear()


# --- Barra Lateral (Conta, API Key e Painel Admin) ---
def renderizar_sidebar():
    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        try:
            chave = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            chave = None

    with st.sidebar:
        st.markdown(f"👤 Olá, **{nome_usuario}**!")
        if logado_google:
            st.caption(f"Gmail: {usuario_atual}")
            st.button("🚪 Sair", on_click=st.logout, use_container_width=True)
        else:
            if st.button("🚪 Sair", use_container_width=True):
                st.session_state["autenticado"] = False
                st.session_state["usuario_logado"] = ""
                for k in [
                    "aviso_voz", "ultimo_audio_hash", "msg_sucesso",
                    "gps_coords", "gps_regiao", "gps_mercados", "gps_detalhes", "gps_novos_salvos",
                ]:
                    st.session_state.pop(k, None)
                st.rerun()

        st.divider()
        st.header("⚙️ Chave da API")
        if chave:
            st.success("API Gemini configurada.")
        else:
            chave = st.text_input(
                "Chave da API Gemini",
                type="password",
                placeholder="Cole sua GEMINI_API_KEY",
                help="Crie grátis em aistudio.google.com/apikey",
            )

        if usuario_atual in USUARIOS_ADMIN:
            st.divider()
            with st.expander("👑 Admin — Usuários"):
                users = carregar_usuarios()
                st.metric("Cadastrados", len(users))
                linhas = [
                    {
                        "Usuário": k,
                        "Tipo": "Gmail" if isinstance(v, dict) and v.get("tipo") == "google" else "Senha",
                    }
                    for k, v in sorted(users.items())
                ]
                st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)

    return chave


# --- Inicialização Segura de Estado ---
st.session_state.setdefault("form_versao", 0)
st.session_state.setdefault("valor_produto", "")
st.session_state.setdefault("valor_quantidade", 1)
st.session_state.setdefault("valor_preco", 1.00)
st.session_state.setdefault("valor_supermercado", "")

# --- Cabeçalho ---
st.title("🛒 Listaí")
st.caption("Controle de compras inteligente, reconhecimento por voz e preços da sua região.")
api_key = renderizar_sidebar()

st.info(
    "🚧 **Fase de testes:** Aproveite o aplicativo gratuitamente! "
    "Em breve poderemos implementar planos e cobranças pelo uso do app."
)

if msg := st.session_state.pop("msg_sucesso", None):
    st.success(msg)

# --- GPS Global ---
with st.container(border=True):
    col_gps_txt, col_gps_btn = st.columns([4, 1])
    with col_gps_txt:
        st.markdown("**📍 Localização GPS**")
        st.caption("Clique ao lado para usar sua região e cadastrar os supermercados próximos automaticamente.")
    with col_gps_btn:
        if streamlit_geolocation is not None:
            localizacao = streamlit_geolocation()
        else:
            localizacao = None
            st.caption("`pip install streamlit-geolocation`")

    if localizacao and localizacao.get("latitude") is not None and localizacao.get("longitude") is not None:
        lat = round(float(localizacao["latitude"]), 4)
        lon = round(float(localizacao["longitude"]), 4)

        if st.session_state.get("gps_coords") != (lat, lon):
            with st.spinner("Detectando região e cadastrando supermercados..."):
                try:
                    regiao_gps, mercados_gps, detalhes = buscar_regiao_e_mercados_proximos(lat, lon)
                    novos = (
                        registrar_varios_mercados(regiao_gps, [m["Supermercado"] for m in detalhes])
                        if detalhes else 0
                    )
                    st.session_state["gps_coords"] = (lat, lon)
                    st.session_state["gps_regiao"] = regiao_gps
                    st.session_state["gps_mercados"] = mercados_gps
                    st.session_state["gps_detalhes"] = detalhes
                    st.session_state["gps_raio_atual"] = 3
                    st.session_state["gps_novos_salvos"] = novos
                except Exception as erro:
                    st.warning(f"⚠️ {erro}")

    gps_coords = st.session_state.get("gps_coords")
    gps_regiao = st.session_state.get("gps_regiao", "")
    gps_mercados = st.session_state.get("gps_mercados", [])

    if gps_coords:
        if gps_mercados:
            mais_perto, dist_m = gps_mercados[0]
            st.success(
                f"📡 **{gps_regiao}** • Mais próximo: **{mais_perto} ({dist_m} m)** "
                f"• {len(gps_mercados)} mercados disponíveis"
            )
        else:
            st.info(f"📡 **{gps_regiao}** — amplie o raio na aba **🗺️ Supermercados** se precisar.")

# --- Abas Principais ---
aba_compras, aba_comunidade, aba_mapa = st.tabs([
    "🛒 Compras & Gráfico",
    "🏪 Preços & WhatsApp",
    "🗺️ Supermercados",
])

# ==============================================================================
# ABA 1: COMPRAS & GRÁFICO
# ==============================================================================
with aba_compras:
    audio_gravado = st.audio_input("🎤 Ditar produto (ex: '2 sabões Omo de 18 reais no Atacadão')")

    if audio_gravado is not None:
        audio_bytes = audio_gravado.getvalue()
        audio_hash = hashlib.sha256(audio_bytes).hexdigest()

        if audio_hash != st.session_state.get("ultimo_audio_hash"):
            st.session_state["ultimo_audio_hash"] = audio_hash
            if not api_key:
                st.warning("Configure sua Chave da API Gemini na barra lateral para usar voz.")
            else:
                with st.spinner("Ouvindo e preenchendo..."):
                    try:
                        dados_voz = reconhecer_produto_por_voz(audio_bytes, api_key)
                        if not dados_voz["produto"]:
                            st.warning("Não entendi o produto. Tente falar mais perto do microfone.")
                        else:
                            st.session_state["valor_produto"] = dados_voz["produto"]
                            st.session_state["valor_quantidade"] = dados_voz["quantidade"]
                            st.session_state["valor_preco"] = (
                                dados_voz["preco_unitario"] if dados_voz["preco_unitario"] > 0 else 1.00
                            )
                            if dados_voz["supermercado"]:
                                st.session_state["valor_supermercado"] = dados_voz["supermercado"]
                            st.session_state["aviso_voz"] = dados_voz
                            st.session_state["form_versao"] += 1
                            st.rerun()
                    except Exception as erro:
                        st.error(f"Erro no áudio: {erro}")

    if aviso := st.session_state.get("aviso_voz"):
        txt_voz = f"🎤 **Ouvi:** *\"{aviso['transcricao']}\"* • Categoria: **{aviso['categoria']}**"
        if aviso.get("supermercado"):
            txt_voz += f" • Mercado: **{aviso['supermercado']}**"
        if aviso["preco_unitario"] <= 0:
            txt_voz += " *(ajuste o preço antes de enviar)*"
        st.info(txt_voz)

    mercados_por_regiao = carregar_mercados()
    regioes = sorted(mercados_por_regiao.keys())
    if gps_regiao and gps_regiao not in regioes:
        regioes = [gps_regiao] + regioes

    versao = st.session_state["form_versao"]
    distancias_gps = dict(gps_mercados)

    col_reg, col_merc = st.columns(2)
    with col_reg:
        opcoes_reg = regioes + ["➕ Nova região..."]
        idx_reg = opcoes_reg.index(gps_regiao) if gps_regiao in opcoes_reg else 0
        reg_esc = st.selectbox(
            "📍 Região", opcoes_reg, index=idx_reg, key=f"sel_reg_{gps_regiao}_{len(regioes)}"
        )
        regiao_final = (
            st.text_input("Nome da Região", placeholder="Ex: Campinas - Centro").strip()
            if reg_esc == "➕ Nova região..." else reg_esc
        )

    with col_merc:
        lista_merc = []
        if mv := st.session_state.get("valor_supermercado", "").strip():
            lista_merc.append(mv)
        for m in [n for n, _ in gps_mercados] + list(mercados_por_regiao.get(regiao_final, [])):
            if m not in lista_merc:
                lista_merc.append(m)

        opcoes_merc = lista_merc + ["➕ Novo supermercado..."]
        merc_esc = st.selectbox(
            "🏪 Supermercado",
            opcoes_merc,
            index=0,
            key=f"sel_merc_{regiao_final}_{len(lista_merc)}_{versao}",
            format_func=lambda m: f"{m} ({distancias_gps[m]} m)" if m in distancias_gps else m,
        )
        mercado_final = (
            st.text_input("Nome do Supermercado", placeholder="Ex: Atacadão, Mercado Central").strip()
            if merc_esc == "➕ Novo supermercado..." else merc_esc
        )

    with st.form("form_compras", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns([2, 3, 1, 1])
        with c1:
            data_compra = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
        with c2:
            produto = st.text_input(
                "Produto",
                value=st.session_state["valor_produto"],
                placeholder="Ex: Sabão Omo, Picanha...",
                key=f"input_produto_{versao}",
            )
        with c3:
            quantidade = st.number_input(
                "Qtd", min_value=1, value=int(st.session_state["valor_quantidade"]), step=1,
                key=f"input_qtd_{versao}",
            )
        with c4:
            preco = st.number_input(
                "Preço (R$)", min_value=0.01, value=float(st.session_state["valor_preco"]),
                step=0.01, format="%.2f", key=f"input_preco_{versao}",
            )

        compartilhar = st.checkbox("📢 Compartilhar preço com a comunidade da região", value=True)
        if st.form_submit_button("Enviar", type="primary", use_container_width=True):
            produto = produto.strip()
            if not produto:
                st.warning("Digite ou fale o nome do produto.")
            elif not regiao_final or not mercado_final:
                st.warning("Informe a Região e o Supermercado.")
            else:
                with st.spinner("Categorizando..."):
                    categoria, origem = identificar_categoria(produto, api_key)

                registrar_varios_mercados(regiao_final, [mercado_final])

                novo = pd.DataFrame(
                    [[data_compra.isoformat(), regiao_final, mercado_final, produto, categoria, quantidade, preco, quantidade * preco]],
                    columns=COLUNAS,
                )
                salvar_linha_csv(ARQUIVO_CSV, novo, carregar_dados)

                extra = ""
                if compartilhar:
                    novo_com = pd.DataFrame(
                        [[data_compra.isoformat(), regiao_final, mercado_final, produto, categoria, preco, nome_usuario]],
                        columns=COLUNAS_COMUNIDADE,
                    )
                    salvar_linha_csv(ARQUIVO_COMUNIDADE, novo_com, carregar_comunidade)
                    extra = " Preço compartilhado!"

                st.session_state["msg_sucesso"] = f"'{produto}' salvo em **{mercado_final}** ({categoria} • {origem}).{extra}"
                st.session_state["valor_produto"] = ""
                st.session_state["valor_quantidade"] = 1
                st.session_state["valor_preco"] = 1.00
                st.session_state["valor_supermercado"] = ""
                st.session_state["form_versao"] += 1
                st.session_state.pop("aviso_voz", None)
                st.rerun()

    exibir_banner_anuncio()

    try:
        df = carregar_dados().copy()
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        st.error("Erro ao ler o arquivo CSV.")
        df = pd.DataFrame(columns=COLUNAS)

    if not df.empty:
        df["Data_dt"] = pd.to_datetime(df["Data"], errors="coerce")
        df_validos = df.dropna(subset=["Data_dt"]).copy()
        mes_atual = date.today().strftime("%Y-%m")

        gasto_mes = 0.0
        if not df_validos.empty:
            df_validos["Mês"] = df_validos["Data_dt"].dt.strftime("%Y-%m")
            gasto_mes = df_validos.loc[df_validos["Mês"] == mes_atual, "Total"].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Total Geral", f"R$ {df['Total'].sum():.2f}")
        m2.metric("📅 Mês Atual", f"R$ {gasto_mes:.2f}")
        m3.metric("🛍️ Itens", len(df))

        st.subheader("📊 Gráficos de Gastos")
        if not df_validos.empty:
            visao = st.radio("Agrupar gráfico mensal por:", ["Total", "Categoria", "Supermercado"], horizontal=True)
            col_g, col_c = st.columns([2, 1])

            with col_g:
                if visao == "Categoria":
                    g = df_validos.groupby(["Mês", "Categoria"], as_index=False)["Total"].sum().sort_values("Mês")
                    st.bar_chart(g, x="Mês", y="Total", color="Categoria")
                elif visao == "Supermercado":
                    df_validos["Mercado"] = df_validos["Supermercado"].replace("", "Não informado").fillna("Não informado")
                    g = df_validos.groupby(["Mês", "Mercado"], as_index=False)["Total"].sum().sort_values("Mês")
                    st.bar_chart(g, x="Mês", y="Total", color="Mercado")
                else:
                    g = df_validos.groupby("Mês", as_index=False)["Total"].sum().sort_values("Mês")
                    st.bar_chart(g, x="Mês", y="Total")

            with col_c:
                res_cat = (
                    df.groupby("Categoria", as_index=False)["Total"]
                    .sum()
                    .sort_values("Total", ascending=False)
                )
                st.dataframe(
                    res_cat,
                    hide_index=True,
                    use_container_width=True,
                    column_config={"Total": st.column_config.NumberColumn("Por Categoria", format="R$ %.2f")},
                )

        st.subheader("📋 Itens na Planilha")
        df_exib = df.copy()
        if not df_validos.empty:
            meses = ["Todos"] + sorted(df_validos["Mês"].unique().tolist(), reverse=True)
            mes_sel = st.selectbox("Filtrar por mês", meses)
            if mes_sel != "Todos":
                df_exib = df_exib[df_exib["Data_dt"].dt.strftime("%Y-%m") == mes_sel]

        df_exib = df_exib.sort_values(by="Data_dt", ascending=False, na_position="last")
        df_exib["Data"] = df_exib["Data_dt"]

        st.dataframe(
            df_exib[COLUNAS],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Preço Unitário": st.column_config.NumberColumn("Preço Unit.", format="R$ %.2f"),
                "Total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
            },
        )

        with st.expander("🗑️ Excluir ou Limpar Compras"):
            opcoes_del = {
                i: f"{r['Data'] or 'Sem data'} | {r['Supermercado'] or '-'} | {r['Produto']} | R$ {r['Total']:.2f}"
                for i, r in df.iterrows()
            }
            sels = st.multiselect("Excluir itens específicos:", list(opcoes_del.keys()), format_func=lambda i: opcoes_del[i])
            if st.button("Excluir selecionados", disabled=not sels):
                df.drop(index=sels)[COLUNAS].to_csv(ARQUIVO_CSV, index=False)
                carregar_dados.clear()
                st.rerun()

            st.divider()
            if st.checkbox("Confirmo apagar TODAS as minhas compras") and st.button("🗑️ Limpar tudo", type="primary"):
                if os.path.exists(ARQUIVO_CSV):
                    os.remove(ARQUIVO_CSV)
                carregar_dados.clear()
                st.rerun()
    else:
        st.info("Nenhum item cadastrado ainda. Use o GPS ou preencha acima!")

# ==============================================================================
# ABA 2: PREÇOS DA REGIÃO & WHATSAPP
# ==============================================================================
with aba_comunidade:
    st.subheader("🏪 Comparador de Preços da Região")
    df_com = carregar_comunidade().copy()

    if df_com.empty:
        st.info("Ainda não há preços compartilhados. Cadastre uma compra na primeira aba!")
    else:
        c1, c2 = st.columns(2)
        with c1:
            regs_com = ["Todas"] + sorted([r for r in df_com["Região"].dropna().unique() if str(r).strip()])
            idx_com = regs_com.index(gps_regiao) if gps_regiao in regs_com else 0
            reg_filtro = st.selectbox("Região", regs_com, index=idx_com, key=f"f_com_{gps_regiao}")
        with c2:
            busca_prod = st.text_input("🔎 Buscar produto", placeholder="Ex: arroz, omo, cafe...").strip()

        df_f = df_com if reg_filtro == "Todas" else df_com[df_com["Região"] == reg_filtro]
        if busca_prod:
            termo = normalizar_texto(busca_prod)
            df_f = df_f[df_f["Produto"].apply(lambda x: termo in normalizar_texto(x))]

        df_f = df_f.copy()
        df_f["Data_dt"] = pd.to_datetime(df_f["Data"], errors="coerce")
        df_ord = df_f.sort_values(by=["Preço Unitário", "Data_dt"], ascending=[True, False])

        if df_ord.empty:
            st.warning("Nenhum preço encontrado com esses filtros.")
        else:
            melhor = df_ord.iloc[0]
            st.success(
                f"🏆 **Menor preço:** **{melhor['Produto']}** por **R$ {melhor['Preço Unitário']:.2f}** "
                f"no **{melhor['Supermercado']}** ({melhor['Região']})"
            )

            df_tab = df_ord.copy()
            df_tab["Data"] = df_tab["Data_dt"]
            st.dataframe(
                df_tab[COLUNAS_COMUNIDADE],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "Preço Unitário": st.column_config.NumberColumn("Preço Unit.", format="R$ %.2f"),
                },
            )

            st.subheader("📲 Compartilhar no WhatsApp")
            linhas_zap = ["🛒 *Melhores preços no Listaí:*", ""] + [
                f"• *{r['Produto']}*: R$ {r['Preço Unitário']:.2f} ({r['Supermercado']} - {r['Região']})"
                for _, r in df_ord.head(5).iterrows()
            ]
            texto_zap = "\n".join(linhas_zap)
            st.code(texto_zap, language=None)
            st.link_button(
                "📲 Enviar no WhatsApp",
                f"https://wa.me/?text={urllib.parse.quote(texto_zap)}",
                type="primary",
                use_container_width=True,
            )

        if usuario_atual in USUARIOS_ADMIN:
            with st.expander("👑 Admin — Limpar comunidade"):
                if st.button("Apagar preços compartilhados"):
                    if os.path.exists(ARQUIVO_COMUNIDADE):
                        os.remove(ARQUIVO_COMUNIDADE)
                    carregar_comunidade.clear()
                    st.rerun()

# ==============================================================================
# ABA 3: SUPERMERCADOS DA REGIÃO
# ==============================================================================
with aba_mapa:
    st.subheader("🗺️ Supermercados na Região")
    raio_km = st.radio("Raio de busca:", [3, 5, 10], index=0, horizontal=True, format_func=lambda x: f"{x} km")

    if gps_coords:
        lat_g, lon_g = gps_coords
        if st.button("🔄 Buscar e cadastrar neste raio", use_container_width=True):
            with st.spinner(f"Buscando em {raio_km} km..."):
                try:
                    nova = consultar_overpass_mercados(lat_g, lon_g, raio_km * 1000)
                    novos = registrar_varios_mercados(gps_regiao, [m["Supermercado"] for m in nova]) if nova else 0

                    mercs, vistos = [], set()
                    for item in nova:
                        if item["Supermercado"] not in vistos:
                            vistos.add(item["Supermercado"])
                            mercs.append((item["Supermercado"], item["Distância (m)"]))

                    st.session_state["gps_detalhes"] = nova
                    st.session_state["gps_mercados"] = mercs
                    st.session_state["gps_raio_atual"] = raio_km
                    st.session_state["gps_novos_salvos"] = novos
                    st.rerun()
                except Exception as erro:
                    st.warning(f"⚠️ {erro}")

        if lista_gps := st.session_state.get("gps_detalhes", []):
            exibir_tabela_e_mapa_regiao(
                lista_gps,
                f"✅ **{len(lista_gps)}** estabelecimentos em **{gps_regiao}** "
                f"({st.session_state.get('gps_raio_atual', 3)} km) cadastrados automaticamente!",
            )
        else:
            st.warning("Nenhum mercado nesse raio. Tente 5 km ou 10 km.")
    else:
        st.info("👆 Clique no botão de **GPS** no topo para detectar sua região automaticamente!")

    st.divider()
    with st.expander("🔎 Pesquisar outra Cidade / Bairro / CEP"):
        cb1, cb2 = st.columns([3, 1])
        with cb1:
            reg_busca = st.text_input("Cidade, Bairro ou CEP", placeholder="Ex: Campinas - Taquaral, 01310-100").strip()
        with cb2:
            st.write("")
            st.write("")
            btn_busca = st.button("Buscar e cadastrar", type="primary", use_container_width=True)

        if btn_busca and reg_busca:
            with st.spinner("Procurando supermercados..."):
                try:
                    nome_loc, lista_m = buscar_supermercados_por_regiao(reg_busca, raio_km * 1000)
                    novos_m = registrar_varios_mercados(reg_busca, [m["Supermercado"] for m in lista_m]) if (nome_loc and lista_m) else 0
                    st.session_state["res_manual"] = {
                        "regiao": reg_busca, "nome_local": nome_loc, "lista": lista_m, "novos": novos_m
                    }
                    st.rerun()
                except Exception as erro:
                    st.warning(f"⚠️ {erro}")

        if res := st.session_state.get("res_manual"):
            if not res["nome_local"]:
                st.error("Localização não encontrada. Tente Cidade e Estado.")
            elif not res["lista"]:
                st.warning("Nenhum supermercado encontrado nesse raio.")
            else:
                exibir_tabela_e_mapa_regiao(
                    res["lista"],
                    f"✅ **{len(res['lista'])}** em **{res['nome_local']}** "
                    f"(+{res['novos']} salvos em **'{res['regiao']}'**).",
                )