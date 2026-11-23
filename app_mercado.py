from datetime import date
import hashlib
import json
import math
import os
import random
import secrets
import unicodedata
import urllib.parse

import altair as alt
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
    initial_sidebar_state="auto",
)

# --- Tema Visual Listaí (Azul da Logo + Verde) ---
st.markdown(
"""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; color: #0F2942; }
.block-container { padding-top: 1.1rem; padding-bottom: 2.2rem; max-width: 1120px; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #EFF6FF 0%, #ECFDF5 100%); border-right: 1px solid #CBE7E3; }
.listai-user-box { background: #FFFFFF; border: 1px solid #BFDBFE; border-left: 5px solid #0077E6; border-radius: 12px; padding: 0.7rem 0.9rem; margin-bottom: 0.75rem; box-shadow: 0 2px 6px rgba(0, 74, 153, 0.06); }
.listai-user-box strong { color: #004A99; font-size: 0.98rem; }
.listai-user-box small { color: #475569; display: block; margin-top: 2px; }
.listai-header { background: linear-gradient(135deg, #004A99 0%, #0077E6 38%, #00B8B0 72%, #16A34A 100%); padding: 1.15rem 1.5rem; border-radius: 16px; color: #FFFFFF; margin-bottom: 0.65rem; box-shadow: 0 8px 24px rgba(0, 119, 230, 0.22); }
.listai-header-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.6rem; }
.listai-brand { display: flex; align-items: center; gap: 0.75rem; }
.listai-logo-badge { background: #FFFFFF; width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 10px rgba(0, 0, 0, 0.14); flex-shrink: 0; }
.listai-header h1 { margin: 0; font-size: 1.75rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.5px; }
.listai-header p { margin: 0.35rem 0 0 0; font-size: 0.92rem; color: #E0F2FE; }
.listai-pills { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.listai-pill { background: rgba(255, 255, 255, 0.2); color: #FFFFFF; padding: 0.22rem 0.75rem; border-radius: 999px; font-size: 0.76rem; font-weight: 700; border: 1px solid rgba(255, 255, 255, 0.3); }
.listai-beta-strip { background: #FEFCE8; border: 1px solid #FDE047; border-left: 4px solid #CA8A04; color: #713F12; padding: 0.5rem 0.95rem; border-radius: 10px; font-size: 0.84rem; margin-bottom: 1rem; }
.listai-winner-card { background: linear-gradient(135deg, #EFF6FF 0%, #ECFDF5 100%); border: 1px solid #93C5FD; border-left: 6px solid #16A34A; border-radius: 14px; padding: 1rem 1.25rem; color: #0F2942; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0, 119, 230, 0.08); }
.listai-winner-card h3 { margin: 0 0 0.25rem 0; font-size: 1.15rem; color: #004A99; }
.listai-mini-card { background: #FFFFFF; border: 1px solid #DBEAFE; border-top: 4px solid #0077E6; border-radius: 14px; padding: 0.85rem; text-align: center; color: #0F2942; margin-bottom: 0.8rem; box-shadow: 0 3px 10px rgba(0, 74, 153, 0.05); }
.listai-mini-card strong { display: block; font-size: 0.92rem; color: #004A99; margin-top: 0.2rem; }
.listai-mini-card span { font-size: 0.8rem; color: #475569; }
div[data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #DBEAFE; border-left: 5px solid #16A34A; padding: 14px 18px; border-radius: 14px; box-shadow: 0 3px 10px rgba(0, 74, 153, 0.05); }
div[data-testid="stMetricValue"] { color: #004A99 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 14px !important; }
.stButton > button, .stLinkButton > a, .stFormSubmitButton > button { border-radius: 10px !important; font-weight: 600 !important; transition: all 0.15s ease; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background: linear-gradient(135deg, #0077E6 0%, #00B8B0 55%, #16A34A 100%) !important; border: none !important; color: #FFFFFF !important; }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover { filter: brightness(1.06); box-shadow: 0 4px 12px rgba(0, 119, 230, 0.25); }
.stButton > button[kind="secondary"] { background-color: #FFFFFF !important; border: 1px solid #BFDBFE !important; color: #004A99 !important; }
.stButton > button[kind="secondary"]:hover { border-color: #16A34A !important; background: linear-gradient(135deg, #EFF6FF 0%, #ECFDF5 100%) !important; color: #004A99 !important; }
div[data-testid="stProgress"] > div > div > div > div { background: linear-gradient(90deg, #0077E6 0%, #00B8B0 50%, #16A34A 100%) !important; }
.listai-ad-badge { display: inline-block; background: linear-gradient(90deg, #DBEAFE, #DCFCE7); color: #004A99; font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 6px; margin-bottom: 0.25rem; }
</style>""",
unsafe_allow_html=True,
)

LOGO_SVG = (
    '<div class="listai-logo-badge">'
    '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<defs><linearGradient id="lg" x1="0" y1="12" x2="24" y2="4" gradientUnits="userSpaceOnUse">'
    '<stop offset="0%" stop-color="#0077E6"/><stop offset="55%" stop-color="#00B8B0"/><stop offset="100%" stop-color="#16A34A"/>'
    '</linearGradient></defs>'
    '<path d="M2 4H5L7.4 14.5C7.6 15.4 8.4 16 9.3 16H17.5C18.4 16 19.2 15.4 19.4 14.5L21 7H6" stroke="url(#lg)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M9.5 10.2L12 12.6L19.5 4.8" stroke="url(#lg)" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="9.5" cy="19.5" r="1.6" fill="#0077E6"/><circle cx="17" cy="19.5" r="1.6" fill="#00B8B0"/>'
    '</svg></div>'
)

# --- Configurações e Constantes ---
ARQUIVO_CSV = "compras_mercado.csv"
ARQUIVO_PRE_LISTA = "pre_lista_compras.csv"
ARQUIVO_COMUNIDADE = "precos_comunidade.csv"
ARQUIVO_MERCADOS = "supermercados.json"
ARQUIVO_USUARIOS = "usuarios.json"
ARQUIVO_PREFS_GPS = "preferencias_gps.json"

PAGINAS = ["🛒 Nova Compra", "📝 Pré-Lista", "📊 Gráficos", "🧾 Histórico", "🏆 Preços", "🗺️ Mercados"]
COLUNAS = ["Data", "Região", "Supermercado", "Produto", "Categoria", "Quantidade", "Preço Unitário", "Total"]
COLUNAS_PRE_LISTA = ["ID", "Produto", "Quantidade", "Categoria", "Comprado"]
COLUNAS_COMUNIDADE = ["Data", "Região", "Supermercado", "Produto", "Categoria", "Preço Unitário", "Usuário"]

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
        "texto_botao": "Ver na Amazon",
        "url": "https://www.amazon.com.br/",
    },
    {
        "titulo": "🛒 Mercado Livre — Compras do Mês",
        "descricao": "Compare preços e aproveite cupons e frete grátis na sua compra.",
        "texto_botao": "Abrir Ofertas",
        "url": "https://www.mercadolivre.com.br/",
    },
    {
        "titulo": "🏷️ Achadinhos e Ofertas na Shopee",
        "descricao": "Utilidades domésticas e itens para casa com super desconto.",
        "texto_botao": "Ver na Shopee",
        "url": "https://shopee.com.br/",
    },
]

LISTA_CATEGORIAS = [
    "Alimentos", "Bebidas", "Hortifruti", "Açougue e Peixaria",
    "Frios e Laticínios", "Padaria", "Limpeza", "Higiene Pessoal",
    "Pet Shop", "Utilidades Domésticas", "Outros",
]

CATEGORIAS_FALLBACK = {
    "Limpeza": ["agua sanitaria", "papel higienico", "detergente", "sabao", "desinfetante", "amaciante", "esponja", "alvejante", "limpador", "vassoura", "rodo"],
    "Bebidas": ["agua", "refrigerante", "suco", "cerveja", "vinho", "leite", "cafe", "cha", "energetico", "achocolatado"],
    "Hortifruti": ["banana", "maca", "laranja", "uva", "mamao", "melancia", "abacaxi", "tomate", "cebola", "batata", "cenoura", "alface", "couve", "pepino", "abobora"],
    "Alimentos": ["arroz", "feijao", "macarrao", "carne", "frango", "peixe", "ovo", "farinha", "acucar", "sal", "biscoito", "bolacha", "pao", "queijo", "presunto", "manteiga", "margarina", "iogurte", "oleo", "molho", "milho", "ervilha"],
}

TRADUCAO_LOJA = {
    "supermarket": "Supermercado",
    "wholesale": "Atacarejo",
    "convenience": "Mercearia / Minimercado",
    "greengrocer": "Hortifruti / Sacolão",
}


# --- Clientes em Cache ---
@st.cache_resource
def obter_http_session():
    sess = requests.Session()
    sess.headers.update({"User-Agent": "ListaiApp/1.0"})
    return sess


@st.cache_resource
def obter_gemini_client(api_key):
    return genai.Client(api_key=api_key)


# --- Autenticação ---
def google_auth_configurado():
    try:
        return "auth" in st.secrets and bool(st.secrets["auth"].get("client_id"))
    except Exception:
        return False


def usuario_google_logado():
    return google_auth_configurado() and bool(getattr(st.user, "is_logged_in", False))


def gerar_hash_senha(senha, salt=None):
    salt = salt or secrets.token_hex(16)
    return f"{salt}${hashlib.sha256((salt + senha).encode('utf-8')).hexdigest()}"


def verificar_senha(senha_digitada, senha_salva):
    if "$" not in senha_salva:
        return False
    salt, hash_esperado = senha_salva.split("$", 1)
    return secrets.compare_digest(
        hashlib.sha256((salt + senha_digitada).encode("utf-8")).hexdigest(), hash_esperado
    )


@st.cache_data(show_spinner=False)
def carregar_usuarios():
    if os.path.exists(ARQUIVO_USUARIOS) and os.path.getsize(ARQUIVO_USUARIOS) > 0:
        try:
            with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    iniciais = {"teste": {"tipo": "senha", "hash": gerar_hash_senha("1234"), "nome": "Conta Teste", "criado_em": date.today().isoformat()}}
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
        usuarios[email] = {"tipo": "google", "nome": nome, "criado_em": date.today().isoformat()}
        salvar_usuarios(usuarios)
    return email, nome


def exibir_tela_login():
    st.markdown(
        f'<div class="listai-header">'
        f'<div class="listai-header-top"><div class="listai-brand">{LOGO_SVG}<h1>Listaí</h1></div>'
        f'<div class="listai-pills"><span class="listai-pill">ECONOMIA NO MERCADO</span></div></div>'
        f'<p>Anote compras por voz, monte sua pré-lista e ache o menor preço da região.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown('<div class="listai-mini-card">📍<strong>GPS Automático</strong><span>Encontra os mercados perto de você</span></div>', unsafe_allow_html=True)
    with f2:
        st.markdown('<div class="listai-mini-card">🎤<strong>Voz + IA</strong><span>Fale o item e ele categoriza sozinho</span></div>', unsafe_allow_html=True)
    with f3:
        st.markdown('<div class="listai-mini-card">🏆<strong>Menor Preço</strong><span>Compare valores e mande no WhatsApp</span></div>', unsafe_allow_html=True)

    _, col_centro, _ = st.columns([1, 2, 1])
    with col_centro:
        with st.container(border=True):
            st.subheader("🔐 Entre ou crie sua conta")
            if google_auth_configurado():
                st.button("🔵 Continuar com Google (Gmail)", on_click=st.login, type="primary", use_container_width=True)
                st.divider()

            aba_entrar, aba_cadastrar = st.tabs(["Entrar", "Criar conta"])
            usuarios = carregar_usuarios()

            with aba_entrar:
                with st.form("form_login"):
                    usuario = st.text_input("Usuário", placeholder="Seu usuário")
                    senha = st.text_input("Senha", type="password", placeholder="Sua senha")
                    if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                        u = usuario.strip().lower()
                        reg = usuarios.get(u)
                        if reg is None:
                            st.error("Usuário ou senha incorretos.")
                        elif isinstance(reg, dict) and reg.get("tipo") == "google":
                            st.warning("Conta vinculada ao Gmail. Use o botão azul acima.")
                        else:
                            h = reg["hash"] if isinstance(reg, dict) else reg
                            if verificar_senha(senha, h):
                                st.session_state["autenticado"] = True
                                st.session_state["usuario_logado"] = u
                                st.session_state["nome_usuario"] = reg.get("nome", u) if isinstance(reg, dict) else u
                                st.rerun()
                            else:
                                st.error("Usuário ou senha incorretos.")
                st.caption("Teste rápido — Usuário: `teste` | Senha: `1234`")

            with aba_cadastrar:
                with st.form("form_cadastro"):
                    novo_user = st.text_input("Novo Usuário", placeholder="Ex: maria")
                    nova_senha = st.text_input("Nova Senha", type="password", placeholder="Mínimo 4 caracteres")
                    conf_senha = st.text_input("Confirmar Senha", type="password")
                    if st.form_submit_button("Criar conta", type="primary", use_container_width=True):
                        nl = novo_user.strip().lower()
                        if not nl:
                            st.warning("Digite um nome de usuário.")
                        elif nl in usuarios:
                            st.error("Esse usuário já existe. Escolha outro.")
                        elif len(nova_senha) < 4:
                            st.warning("A senha deve ter pelo menos 4 caracteres.")
                        elif nova_senha != conf_senha:
                            st.error("As senhas não coincidem.")
                        else:
                            u_edit = usuarios.copy()
                            u_edit[nl] = {"tipo": "senha", "hash": gerar_hash_senha(nova_senha), "nome": nl, "criado_em": date.today().isoformat()}
                            salvar_usuarios(u_edit)
                            st.success("Conta criada! Faça login na aba **Entrar**.")


if not (usuario_google_logado() or st.session_state.get("autenticado", False)):
    exibir_tela_login()
    st.stop()

logado_google = usuario_google_logado()
if logado_google:
    usuario_atual, nome_usuario = registrar_usuario_google_se_novo()
    st.session_state["usuario_logado"] = usuario_atual
    st.session_state["nome_usuario"] = nome_usuario
else:
    usuario_atual = st.session_state.get("usuario_logado", "usuario")
    nome_usuario = st.session_state.get("nome_usuario", usuario_atual)


# --- Localização, Preferência Salva e Supermercados ---
def carregar_preferencias_gps():
    if os.path.exists(ARQUIVO_PREFS_GPS) and os.path.getsize(ARQUIVO_PREFS_GPS) > 0:
        try:
            with open(ARQUIVO_PREFS_GPS, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}


def salvar_preferencias_gps(lat, lon, regiao):
    with open(ARQUIVO_PREFS_GPS, "w", encoding="utf-8") as f:
        json.dump({"lat": lat, "lon": lon, "regiao": regiao}, f, ensure_ascii=False, indent=2)


def calcular_distancia_metros(lat1, lon1, lat2, lon2):
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return int(2 * 6371000 * math.asin(math.sqrt(a)))


def _extrair_lista_mercados(elementos, lat, lon):
    encontrados = {}
    for elem in elementos:
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
        end = ", ".join(p for p in [f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip(), tags.get("addr:suburb", "")] if p) or "-"
        chave = f"{nome}|{round(elat, 4)}|{round(elon, 4)}"
        if chave not in encontrados or dist < encontrados[chave]["Distância (m)"]:
            encontrados[chave] = {"Supermercado": nome, "Tipo": tipo, "Endereço": end, "Distância (m)": dist, "lat": elat, "lon": elon}
    return sorted(encontrados.values(), key=lambda x: x["Distância (m)"])


def consultar_photon_mercados(lat, lon, raio_metros):
    http = obter_http_session()
    d_lat = raio_metros / 111320.0
    d_lon = raio_metros / (111320.0 * max(0.2, abs(math.cos(math.radians(lat)))))
    bbox = f"{lon - d_lon},{lat - d_lat},{lon + d_lon},{lat + d_lat}"
    encontrados, ok = {}, False

    for termo in ["supermercado", "atacadao", "mercado"]:
        try:
            resp = http.get("https://photon.komoot.io/api/", params={"q": termo, "lat": lat, "lon": lon, "bbox": bbox, "limit": 25}, timeout=8)
            if resp.status_code != 200:
                continue
            ok = True
            for feat in resp.json().get("features", []):
                props, coords = feat.get("properties", {}), feat.get("geometry", {}).get("coordinates", [])
                if len(coords) < 2 or (props.get("osm_key") != "shop" and props.get("osm_value") not in TRADUCAO_LOJA):
                    continue
                nome = (props.get("name") or "").strip()
                if not nome:
                    continue
                elon, elat = float(coords[0]), float(coords[1])
                dist = calcular_distancia_metros(lat, lon, elat, elon)
                if dist > raio_metros:
                    continue
                tipo = TRADUCAO_LOJA.get(props.get("osm_value", ""), "Supermercado")
                end = ", ".join(p for p in [props.get("street", ""), props.get("district") or props.get("locality") or ""] if p) or "-"
                chave = f"{nome}|{round(elat, 4)}|{round(elon, 4)}"
                if chave not in encontrados or dist < encontrados[chave]["Distância (m)"]:
                    encontrados[chave] = {"Supermercado": nome, "Tipo": tipo, "Endereço": end, "Distância (m)": dist, "lat": elat, "lon": elon}
        except Exception:
            continue
    return sorted(encontrados.values(), key=lambda x: x["Distância (m)"]) if ok else None


@st.cache_data(ttl=600, show_spinner=False)
def consultar_overpass_mercados(lat, lon, raio_metros):
    http = obter_http_session()
    query = (
        f'[out:json][timeout:10];('
        f'nw(around:{raio_metros},{lat},{lon})["shop"="supermarket"];'
        f'nw(around:{raio_metros},{lat},{lon})["shop"="wholesale"];'
        f'nw(around:{raio_metros},{lat},{lon})["shop"="convenience"];'
        f'nw(around:{raio_metros},{lat},{lon})["shop"="greengrocer"];'
        f');out center tags;'
    )
    for servidor in OVERPASS_SERVERS:
        try:
            resp = http.post(servidor, data={"data": query}, timeout=10)
            if resp.status_code == 200:
                return _extrair_lista_mercados(resp.json().get("elements", []), lat, lon)
        except Exception:
            continue

    res_photon = consultar_photon_mercados(lat, lon, raio_metros)
    if res_photon is not None:
        return res_photon
    raise RuntimeError("Servidores de mapa ocupados no momento. Tente novamente em instantes.")


@st.cache_data(ttl=600, show_spinner=False)
def buscar_regiao_e_mercados_proximos(lat, lon):
    http, regiao = obter_http_session(), ""
    try:
        r = http.get("https://nominatim.openstreetmap.org/reverse", params={"lat": lat, "lon": lon, "format": "json", "accept-language": "pt-BR"}, timeout=6)
        if r.status_code == 200:
            addr = r.json().get("address", {})
            cid = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village") or ""
            bai = addr.get("suburb") or addr.get("neighbourhood") or addr.get("city_district") or ""
            regiao = f"{cid} - {bai}" if (cid and bai) else (cid or bai)
    except Exception:
        pass

    regiao = regiao or "Minha Região (GPS)"
    detalhes = consultar_overpass_mercados(lat, lon, 3000)
    return regiao, _resumir_mercados(detalhes), detalhes


@st.cache_data(ttl=600, show_spinner=False)
def buscar_supermercados_por_regiao(texto_regiao, raio_metros=3000):
    http = obter_http_session()
    r = http.get("https://nominatim.openstreetmap.org/search", params={"q": texto_regiao, "countrycodes": "br", "format": "json", "limit": 1, "accept-language": "pt-BR"}, timeout=8)
    if r.status_code != 200 or not r.json():
        return None, []
    lugar = r.json()[0]
    return lugar.get("display_name", texto_regiao), consultar_overpass_mercados(float(lugar["lat"]), float(lugar["lon"]), raio_metros)


def _resumir_mercados(lista_completa):
    vistos, resumo = set(), []
    for item in lista_completa:
        if item["Supermercado"] not in vistos:
            vistos.add(item["Supermercado"])
            resumo.append((item["Supermercado"], item["Distância (m)"]))
    return resumo


# --- Helpers ---
def normalizar_texto(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower().strip()) if unicodedata.category(c) != "Mn")


def formatar_reais(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def exibir_rodape_anuncio():
    anuncio = random.choice(ANUNCIOS)
    st.divider()
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown('<span class="listai-ad-badge">OFERTA PARCEIRA • PUBLICIDADE</span>', unsafe_allow_html=True)
            st.markdown(f"**{anuncio['titulo']}** — {anuncio['descricao']}")
        with c2:
            st.link_button(anuncio["texto_botao"], anuncio["url"], use_container_width=True)


def exibir_tabela_e_mapa_regiao(lista_mercados, msg_sucesso):
    df_m = pd.DataFrame(lista_mercados)
    st.success(msg_sucesso)
    col_l, col_m = st.columns([3, 2])
    with col_l:
        st.dataframe(df_m[["Supermercado", "Tipo", "Endereço", "Distância (m)"]], hide_index=True, use_container_width=True)
    with col_m:
        st.map(df_m, latitude="lat", longitude="lon")


# --- Gráficos Profissionais ---
def renderizar_graficos_compras(df, df_validos):
    if df_validos.empty:
        st.info("Adicione compras com data para visualizar os gráficos.")
        return

    visao = st.radio("Agrupar evolução mensal por:", ["Total do Mês", "Por Categoria", "Por Supermercado"], horizontal=True)
    paleta = ["#004A99", "#0077E6", "#00B8B0", "#16A34A", "#22C55E", "#38BDF8", "#0D9488", "#15803D"]
    col_g, col_c = st.columns([3, 2])

    with col_g:
        df_v = df_validos.copy()
        meses_ord = sorted(df_v["Mês"].unique().tolist())
        mapa_lbl = {m: f"{m[5:]}/{m[:4]}" for m in meses_ord}
        ord_lbls = [mapa_lbl[m] for m in meses_ord]
        df_v["Mês_Label"] = df_v["Mês"].map(mapa_lbl)

        if visao in ("Por Categoria", "Por Supermercado"):
            col_cor = "Categoria" if visao == "Por Categoria" else "Mercado"
            if col_cor == "Mercado":
                df_v["Mercado"] = df_v["Supermercado"].replace("", "Não informado").fillna("Não informado")
            g = df_v.groupby(["Mês", "Mês_Label", col_cor], as_index=False)["Total"].sum()
            g["Valor_fmt"] = g["Total"].apply(formatar_reais)
            chart_mensal = (
                alt.Chart(g)
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                .encode(
                    x=alt.X("Mês_Label:N", sort=ord_lbls, title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Total:Q", title="Gasto (R$)"),
                    color=alt.Color(f"{col_cor}:N", scale=alt.Scale(range=paleta), legend=alt.Legend(orient="bottom", columns=3, title=None)),
                    tooltip=[alt.Tooltip("Mês_Label:N", title="Mês"), alt.Tooltip(f"{col_cor}:N", title=col_cor), alt.Tooltip("Valor_fmt:N", title="Total")],
                )
                .properties(height=320, title=f"Gastos Mensais ({visao})")
            )
        else:
            g = df_v.groupby(["Mês", "Mês_Label"], as_index=False)["Total"].sum()
            g["Valor_fmt"] = g["Total"].apply(formatar_reais)
            barras = (
                alt.Chart(g)
                .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7, color="#16A34A", size=38)
                .encode(
                    x=alt.X("Mês_Label:N", sort=ord_lbls, title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Total:Q", title="Gasto (R$)", scale=alt.Scale(domain=[0, max(g["Total"].max() * 1.18, 10)])),
                    tooltip=[alt.Tooltip("Mês_Label:N", title="Mês"), alt.Tooltip("Valor_fmt:N", title="Total Gasto")],
                )
            )
            rotulos = barras.mark_text(align="center", baseline="bottom", dy=-5, fontWeight="bold", color="#004A99").encode(text="Valor_fmt:N")
            if len(g) >= 2:
                media = g["Total"].mean()
                linha = alt.Chart(pd.DataFrame({"Media": [media]})).mark_rule(strokeDash=[5, 4], color="#0077E6", size=2).encode(y="Media:Q")
                chart_mensal = (barras + rotulos + linha).properties(height=320, title=f"Evolução Mensal (média: {formatar_reais(media)})")
            else:
                chart_mensal = (barras + rotulos).properties(height=320, title="Evolução Mensal")

        st.altair_chart(chart_mensal, use_container_width=True)

    with col_c:
        res_cat = df.groupby("Categoria", as_index=False)["Total"].sum().sort_values("Total", ascending=False)
        res_cat["Pct"] = (res_cat["Total"] / max(res_cat["Total"].sum(), 0.01)) * 100
        res_cat["Label"] = res_cat.apply(lambda r: f"{formatar_reais(r['Total'])} ({r['Pct']:.0f}%)", axis=1)
        barras_cat = (
            alt.Chart(res_cat)
            .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
            .encode(
                y=alt.Y("Categoria:N", sort="-x", title=None),
                x=alt.X("Total:Q", title=None, axis=None, scale=alt.Scale(domain=[0, res_cat["Total"].max() * 1.45])),
                color=alt.Color("Total:Q", scale=alt.Scale(range=["#0077E6", "#00B8B0", "#16A34A"]), legend=None),
                tooltip=[alt.Tooltip("Categoria:N", title="Categoria"), alt.Tooltip("Label:N", title="Gasto")],
            )
        )
        txt_cat = barras_cat.mark_text(align="left", baseline="middle", dx=6, fontSize=12, fontWeight="bold", color="#004A99").encode(text="Label:N")
        st.altair_chart((barras_cat + txt_cat).properties(height=320, title="Onde você gastou mais"), use_container_width=True)


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


def registrar_varios_mercados(regiao, nomes):
    regiao = regiao.strip()
    if not regiao or not nomes:
        return 0
    mercados = carregar_mercados().copy()
    atual = set(mercados.get(regiao, []))
    antes = len(atual)
    atual.update(n.strip() for n in nomes if n.strip())
    if len(atual) > antes or regiao not in mercados:
        mercados[regiao] = sorted(atual)
        salvar_mercados(mercados)
    return len(atual) - antes


# --- IA (Categorização + Voz) ---
def identificar_categoria_local(produto):
    p_norm = normalizar_texto(produto)
    for cat, palavras in CATEGORIAS_FALLBACK.items():
        if any(normalizar_texto(p) in p_norm for p in palavras):
            return cat
    return "Outros"


@st.cache_data(ttl=86400, show_spinner=False)
def classificar_com_ia(produto_normalizado, api_key):
    client = obter_gemini_client(api_key)
    resp = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"Produto: {produto_normalizado}",
        config=types.GenerateContentConfig(
            system_instruction=(
                "Você é um classificador automático de produtos de supermercado no Brasil. "
                f"Responda APENAS com o nome exato de UMA destas categorias: {', '.join(LISTA_CATEGORIAS)}. Sem pontuação."
            )
        ),
    )
    limpa = normalizar_texto(resp.text)
    return next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in limpa), "Outros")


def identificar_categoria(produto, api_key):
    if not api_key:
        return identificar_categoria_local(produto), "Local"
    try:
        return classificar_com_ia(normalizar_texto(produto), api_key), "API Gemini"
    except Exception as erro:
        st.warning(f"API indisponível ({erro}). Usando regra local.")
        return identificar_categoria_local(produto), "Local"


def reconhecer_produto_por_voz(audio_bytes, api_key):
    client = obter_gemini_client(api_key)
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
        "Ouça o áudio em português do Brasil sobre compra de mercado e extraia: transcricao, produto, "
        f"categoria (exatamente uma de: {', '.join(LISTA_CATEGORIAS)}), quantidade (1 se não falar), "
        "preco_unitario (0 se não falar) e supermercado ('' se não falar)."
    )
    resp = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=[types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema),
    )
    dados = json.loads(resp.text)
    cat_norm = normalizar_texto(dados.get("categoria", ""))
    return {
        "transcricao": str(dados.get("transcricao", "")).strip(),
        "produto": str(dados.get("produto", "")).strip(),
        "categoria": next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in cat_norm), "Outros"),
        "quantidade": max(1, int(dados.get("quantidade") or 1)),
        "preco_unitario": max(0.0, float(dados.get("preco_unitario") or 0.0)),
        "supermercado": str(dados.get("supermercado", "")).strip(),
    }


# --- Persistência em Cache ---
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


@st.cache_data(show_spinner=False)
def carregar_pre_lista():
    if not (os.path.exists(ARQUIVO_PRE_LISTA) and os.path.getsize(ARQUIVO_PRE_LISTA) > 0):
        return pd.DataFrame(columns=COLUNAS_PRE_LISTA)
    df = pd.read_csv(ARQUIVO_PRE_LISTA)
    for col in COLUNAS_PRE_LISTA:
        if col not in df.columns:
            df[col] = 1 if col == "Quantidade" else (False if col == "Comprado" else ([secrets.token_hex(4) for _ in range(len(df))] if col == "ID" else ""))
    df = df[COLUNAS_PRE_LISTA]
    df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(1).astype(int)
    df["Comprado"] = df["Comprado"].map(lambda v: str(v).strip().lower() in ("true", "1", "sim"))
    df["ID"] = df["ID"].astype(str)
    return df


def salvar_pre_lista(df_pre):
    df_pre[COLUNAS_PRE_LISTA].to_csv(ARQUIVO_PRE_LISTA, index=False)
    carregar_pre_lista.clear()


def adicionar_itens_pre_lista(texto_itens, qtd, api_key):
    itens = [i.strip() for i in texto_itens.split(",") if i.strip()]
    if not itens:
        return 0
    df_atual = carregar_pre_lista().copy()
    novas = [{"ID": secrets.token_hex(4), "Produto": p, "Quantidade": max(1, int(qtd)), "Categoria": identificar_categoria(p, api_key)[0], "Comprado": False} for p in itens]
    salvar_pre_lista(pd.concat([df_atual, pd.DataFrame(novas, columns=COLUNAS_PRE_LISTA)], ignore_index=True))
    return len(novas)


def salvar_linha_csv(caminho, novo_df, loader_fn):
    pd.concat([loader_fn(), novo_df], ignore_index=True).to_csv(caminho, index=False)
    loader_fn.clear()


def obter_compras_com_datas():
    try:
        df = carregar_dados().copy()
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        st.error("Erro ao ler o arquivo CSV.")
        return pd.DataFrame(columns=COLUNAS), pd.DataFrame(columns=COLUNAS)
    if df.empty:
        return df, pd.DataFrame(columns=COLUNAS)
    df["Data_dt"] = pd.to_datetime(df["Data"], errors="coerce")
    df_validos = df.dropna(subset=["Data_dt"]).copy()
    if not df_validos.empty:
        df_validos["Mês"] = df_validos["Data_dt"].dt.strftime("%Y-%m")
    return df, df_validos


# --- Carrega automaticamente a última região salva ao entrar ---
if "gps_coords" not in st.session_state:
    prefs = carregar_preferencias_gps()
    if prefs.get("lat") is not None and prefs.get("lon") is not None:
        reg_salva = prefs.get("regiao", "")
        mercs_salvos = carregar_mercados().get(reg_salva, [])
        st.session_state.update({
            "gps_coords": (float(prefs["lat"]), float(prefs["lon"])),
            "gps_regiao": reg_salva,
            "gps_mercados": [(m, None) for m in mercs_salvos],
            "gps_raio_atual": 3,
        })


# --- Barra Lateral ---
def renderizar_sidebar():
    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        try:
            chave = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            chave = None

    with st.sidebar:
        sub_user = usuario_atual if logado_google else "Conta Listaí"
        st.markdown(f'<div class="listai-user-box"><strong>👤 {nome_usuario}</strong><small>{sub_user}</small></div>', unsafe_allow_html=True)

        st.markdown("**📌 Menu do Aplicativo**")
        for idx, pag in enumerate(PAGINAS):
            if st.button(pag, key=f"side_nav_{idx}", type="primary" if st.session_state["pagina_atual"] == pag else "secondary", use_container_width=True):
                st.session_state["pagina_atual"] = pag
                st.rerun()

        st.divider()

        # GPS na barra lateral em largura total (sem colunas apertadas para não travar o clique)
        with st.expander("📍 Localização GPS", expanded=False):
            with st.container(border=True):
                st.markdown("**🎯 Atualizar minha posição agora**")
                st.caption("Toque no ícone abaixo e clique em **Permitir** no navegador:")
                localizacao = streamlit_geolocation() if streamlit_geolocation else None
                if streamlit_geolocation is None:
                    st.warning("Pacote `streamlit-geolocation` não instalado.")

            if localizacao and localizacao.get("latitude") is not None and localizacao.get("longitude") is not None:
                lat, lon = round(float(localizacao["latitude"]), 4), round(float(localizacao["longitude"]), 4)
                if st.session_state.get("gps_ultima_leitura") != (lat, lon):
                    with st.spinner("Localizando supermercados próximos..."):
                        try:
                            reg_g, mercs_g, det_g = buscar_regiao_e_mercados_proximos(lat, lon)
                            novos = registrar_varios_mercados(reg_g, [m["Supermercado"] for m in det_g]) if det_g else 0
                            salvar_preferencias_gps(lat, lon, reg_g)
                            st.session_state.update({
                                "gps_ultima_leitura": (lat, lon),
                                "gps_coords": (lat, lon),
                                "gps_regiao": reg_g,
                                "gps_mercados": mercs_g,
                                "gps_detalhes": det_g,
                                "gps_raio_atual": 3,
                                "gps_novos_salvos": novos,
                            })
                            st.rerun()
                        except Exception as erro:
                            st.warning(f"⚠️ {erro}")

            if st.session_state.get("gps_coords"):
                reg_atual, mercs_atual = st.session_state.get("gps_regiao", ""), st.session_state.get("gps_mercados", [])
                if mercs_atual and mercs_atual[0][1] is not None:
                    st.success(f"📌 **{reg_atual}**\n\nMais próximo: **{mercs_atual[0][0]} ({mercs_atual[0][1]} m)**")
                elif reg_atual:
                    st.info(f"📌 Região ativa: **{reg_atual}**")

            st.caption("Se não abrir o pedido de permissão, verifique o cadeado 🔒 na barra de endereço do navegador e libere a Localização.")

        with st.expander("⚙️ Inteligência Artificial", expanded=not bool(chave)):
            if chave:
                st.success("API Gemini conectada.")
            else:
                chave = st.text_input("Chave da API Gemini", type="password", placeholder="Cole sua GEMINI_API_KEY", help="Crie grátis em aistudio.google.com/apikey")

        st.divider()
        oferta_lat = ANUNCIOS[0]
        with st.container(border=True):
            st.caption("📢 Parceiro Listaí")
            st.markdown(f"**{oferta_lat['titulo']}**")
            st.caption(oferta_lat["descricao"])
            st.link_button(oferta_lat["texto_botao"], oferta_lat["url"], use_container_width=True)

        if usuario_atual in USUARIOS_ADMIN:
            with st.expander("👑 Admin — Usuários"):
                users = carregar_usuarios()
                st.metric("Cadastrados", len(users))
                st.dataframe(
                    pd.DataFrame([{"Usuário": k, "Tipo": "Gmail" if isinstance(v, dict) and v.get("tipo") == "google" else "Senha"} for k, v in sorted(users.items())]),
                    hide_index=True,
                    use_container_width=True,
                )

        st.divider()
        if logado_google:
            st.button("🚪 Sair da conta", on_click=st.logout, use_container_width=True)
        elif st.button("🚪 Sair da conta", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["usuario_logado"] = ""
            for k in ["aviso_voz", "ultimo_audio_hash", "msg_sucesso", "gps_ultima_leitura", "gps_coords", "gps_regiao", "gps_mercados", "gps_detalhes", "gps_novos_salvos"]:
                st.session_state.pop(k, None)
            st.rerun()

    return chave


# --- Estado Inicial ---
st.session_state.setdefault("pagina_atual", PAGINAS[0])
st.session_state.setdefault("form_versao", 0)
st.session_state.setdefault("valor_produto", "")
st.session_state.setdefault("valor_quantidade", 1)
st.session_state.setdefault("valor_preco", 1.00)
st.session_state.setdefault("valor_supermercado", "")

# --- Renderização Principal ---
api_key = renderizar_sidebar()
gps_coords = st.session_state.get("gps_coords")
gps_regiao = st.session_state.get("gps_regiao", "")
gps_mercados = st.session_state.get("gps_mercados", [])

pill_gps = f'<span class="listai-pill">📍 {gps_regiao}</span>' if gps_regiao else ""
st.markdown(
    f'<div class="listai-header"><div class="listai-header-top"><div class="listai-brand">{LOGO_SVG}<h1>Listaí</h1></div>'
    f'<div class="listai-pills">{pill_gps}<span class="listai-pill">BETA GRATUITO</span></div></div>'
    f'<p>Sua lista inteligente • Voz + IA • Menor preço da região</p></div>'
    f'<div class="listai-beta-strip">🚧 <strong>Fase de testes:</strong> O uso é gratuito agora; logo mais para frente poderemos implementar cobranças no aplicativo.</div>',
    unsafe_allow_html=True,
)

if msg := st.session_state.pop("msg_sucesso", None):
    st.success(msg)

pagina = st.session_state["pagina_atual"]

# ==============================================================================
# PÁGINA 1: NOVA COMPRA
# ==============================================================================
if pagina == PAGINAS[0]:
    mercados_por_regiao = carregar_mercados()
    regioes = sorted(mercados_por_regiao.keys())
    if gps_regiao and gps_regiao not in regioes:
        regioes = [gps_regiao] + regioes

    versao, distancias_gps = st.session_state["form_versao"], dict(gps_mercados)

    with st.container(border=True):
        st.markdown("#### 📝 Registrar Nova Compra")

        col_reg, col_merc = st.columns(2)
        with col_reg:
            opcoes_reg = regioes + ["➕ Nova região..."]
            reg_esc = st.selectbox("📍 Região", opcoes_reg, index=opcoes_reg.index(gps_regiao) if gps_regiao in opcoes_reg else 0, key=f"sel_reg_{gps_regiao}_{len(regioes)}")
            regiao_final = st.text_input("Nome da Região", placeholder="Ex: Campinas - Centro").strip() if reg_esc == "➕ Nova região..." else reg_esc

        with col_merc:
            lista_merc = []
            if mv := st.session_state.get("valor_supermercado", "").strip():
                lista_merc.append(mv)
            for m in [n for n, _ in gps_mercados] + list(mercados_por_regiao.get(regiao_final, [])):
                if m not in lista_merc:
                    lista_merc.append(m)

            merc_esc = st.selectbox(
                "🏪 Supermercado", lista_merc + ["➕ Novo supermercado..."], index=0,
                key=f"sel_merc_{regiao_final}_{len(lista_merc)}_{versao}",
                format_func=lambda m: f"{m} ({distancias_gps[m]} m)" if distancias_gps.get(m) is not None else m,
            )
            mercado_final = st.text_input("Nome do Supermercado", placeholder="Ex: Atacadão, Mercado Central").strip() if merc_esc == "➕ Novo supermercado..." else merc_esc

        audio_gravado = st.audio_input("🎤 Falar produto (opcional — ex: '2 sabões Omo de 18 reais')")
        if audio_gravado is not None:
            audio_bytes = audio_gravado.getvalue()
            audio_hash = hashlib.sha256(audio_bytes).hexdigest()
            if audio_hash != st.session_state.get("ultimo_audio_hash"):
                st.session_state["ultimo_audio_hash"] = audio_hash
                if not api_key:
                    st.warning("Configure sua Chave da API Gemini no menu lateral para usar voz.")
                else:
                    with st.spinner("Ouvindo e preenchendo..."):
                        try:
                            dv = reconhecer_produto_por_voz(audio_bytes, api_key)
                            if not dv["produto"]:
                                st.warning("Não entendi o produto. Tente falar mais perto do microfone.")
                            else:
                                st.session_state.update({
                                    "valor_produto": dv["produto"],
                                    "valor_quantidade": dv["quantidade"],
                                    "valor_preco": dv["preco_unitario"] if dv["preco_unitario"] > 0 else 1.00,
                                    "aviso_voz": dv,
                                    "form_versao": versao + 1,
                                })
                                if dv["supermercado"]:
                                    st.session_state["valor_supermercado"] = dv["supermercado"]
                                st.rerun()
                        except Exception as erro:
                            st.error(f"Erro no áudio: {erro}")

        if aviso := st.session_state.get("aviso_voz"):
            txt_voz = f"🎤 **Ouvi:** *\"{aviso['transcricao']}\"* • Categoria: **{aviso['categoria']}**"
            if aviso.get("supermercado"):
                txt_voz += f" • Mercado: **{aviso['supermercado']}**"
            if aviso["preco_unitario"] <= 0:
                txt_voz += " *(ajuste o preço abaixo)*"
            st.info(txt_voz)

        with st.form("form_compras", clear_on_submit=False, border=False):
            c1, c2, c3, c4 = st.columns([2, 3, 1, 1])
            with c1:
                data_compra = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            with c2:
                produto = st.text_input("Produto", value=st.session_state["valor_produto"], placeholder="Ex: Arroz 5kg, Sabão Omo, Café...", key=f"input_produto_{versao}")
            with c3:
                quantidade = st.number_input("Qtd", min_value=1, value=int(st.session_state["valor_quantidade"]), step=1, key=f"input_qtd_{versao}")
            with c4:
                preco = st.number_input("Preço (R$)", min_value=0.01, value=float(st.session_state["valor_preco"]), step=0.01, format="%.2f", key=f"input_preco_{versao}")

            col_chk, col_btn = st.columns([2, 1])
            with col_chk:
                compartilhar = st.checkbox("📢 Compartilhar preço com a região", value=True)
            with col_btn:
                enviado = st.form_submit_button("✅ Salvar Compra", type="primary", use_container_width=True)

            if enviado:
                produto = produto.strip()
                if not produto:
                    st.warning("Digite ou fale o nome do produto.")
                elif not regiao_final or not mercado_final:
                    st.warning("Informe a Região e o Supermercado.")
                else:
                    with st.spinner("Salvando..."):
                        categoria, _ = identificar_categoria(produto, api_key)

                    registrar_varios_mercados(regiao_final, [mercado_final])
                    salvar_linha_csv(
                        ARQUIVO_CSV,
                        pd.DataFrame([[data_compra.isoformat(), regiao_final, mercado_final, produto, categoria, quantidade, preco, quantidade * preco]], columns=COLUNAS),
                        carregar_dados,
                    )

                    extra = ""
                    if compartilhar:
                        salvar_linha_csv(
                            ARQUIVO_COMUNIDADE,
                            pd.DataFrame([[data_compra.isoformat(), regiao_final, mercado_final, produto, categoria, preco, nome_usuario]], columns=COLUNAS_COMUNIDADE),
                            carregar_comunidade,
                        )
                        extra = " Preço compartilhado!"

                    st.session_state.update({
                        "msg_sucesso": f"'{produto}' salvo em **{mercado_final}** ({categoria}).{extra}",
                        "valor_produto": "", "valor_quantidade": 1, "valor_preco": 1.00, "valor_supermercado": "",
                        "form_versao": versao + 1,
                    })
                    st.session_state.pop("aviso_voz", None)
                    st.rerun()

# ==============================================================================
# PÁGINA 2: PRÉ-LISTA DE COMPRAS (CHECKLIST)
# ==============================================================================
elif pagina == PAGINAS[1]:
    st.subheader("📝 Pré-Lista de Compras (Checklist)")
    st.caption("Anote antes de ir ao mercado e vá marcando cada item quando encontrar na prateleira.")

    with st.container(border=True):
        with st.form("form_pre_lista", clear_on_submit=True, border=False):
            cp1, cp2, cp3 = st.columns([4, 1, 2])
            with cp1:
                itens_texto = st.text_input("O que precisa comprar?", placeholder="Ex: Arroz 5kg  (ou vários: Arroz, Feijão, Café, Leite)")
            with cp2:
                qtd_pre = st.number_input("Qtd", min_value=1, value=1, step=1)
            with cp3:
                st.write("")
                st.write("")
                add_pre = st.form_submit_button("➕ Adicionar à Lista", type="primary", use_container_width=True)

            if add_pre:
                if not itens_texto.strip():
                    st.warning("Digite pelo menos um produto.")
                else:
                    st.session_state["msg_sucesso"] = f"{adicionar_itens_pre_lista(itens_texto, qtd_pre, api_key)} item(ns) adicionado(s) na pré-lista!"
                    st.rerun()

        df_hist_sug, _ = obter_compras_com_datas()
        if not df_hist_sug.empty:
            frequentes = df_hist_sug["Produto"].value_counts().head(8).index.tolist()
            with st.expander("⚡ Adicionar rápido dos itens que você mais compra"):
                escolhidos = st.multiselect("Escolha os itens:", frequentes)
                if st.button("Adicionar selecionados na pré-lista", disabled=not escolhidos):
                    adicionar_itens_pre_lista(", ".join(escolhidos), 1, api_key)
                    st.rerun()

    df_pre = carregar_pre_lista().copy()
    if df_pre.empty:
        with st.container(border=True):
            st.info("Sua pré-lista está vazia! Adicione os itens acima antes de ir ao supermercado.")
    else:
        total_pre, pegos = len(df_pre), int(df_pre["Comprado"].sum())
        progresso = pegos / total_pre if total_pre else 0.0
        st.progress(progresso, text=f"✅ **{pegos} de {total_pre}** itens encontrados no supermercado ({int(progresso * 100)}%)")

        with st.container(border=True):
            alterou_check = False
            for idx, row in df_pre.sort_values(by="Comprado", ascending=True).iterrows():
                item_id, prod_nome, qtd_item = row["ID"], row["Produto"], int(row["Quantidade"])
                cat_item, ja_pego = row["Categoria"] or "Outros", bool(row["Comprado"])

                c_chk, c_lancar, c_del = st.columns([6, 2, 1])
                with c_chk:
                    lbl = f"~~{prod_nome} (x{qtd_item})~~ · *{cat_item}*" if ja_pego else f"**{prod_nome}** (x{qtd_item}) · *{cat_item}*"
                    marcado = st.checkbox(lbl, value=ja_pego, key=f"chk_pre_{item_id}")
                    if marcado != ja_pego:
                        df_pre.loc[idx, "Comprado"] = marcado
                        alterou_check = True
                with c_lancar:
                    if st.button("💰 Lançar preço", key=f"btn_lancar_{item_id}", use_container_width=True):
                        df_pre.loc[idx, "Comprado"] = True
                        salvar_pre_lista(df_pre)
                        st.session_state.update({
                            "valor_produto": prod_nome,
                            "valor_quantidade": qtd_item,
                            "form_versao": st.session_state["form_versao"] + 1,
                            "pagina_atual": PAGINAS[0],
                        })
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"btn_del_pre_{item_id}", help="Remover item", use_container_width=True):
                        salvar_pre_lista(df_pre.drop(index=idx))
                        st.rerun()

            if alterou_check:
                salvar_pre_lista(df_pre)
                st.rerun()

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if st.button("🧹 Limpar itens já marcados (✅)", disabled=(pegos == 0), use_container_width=True):
                salvar_pre_lista(df_pre[~df_pre["Comprado"]])
                st.rerun()
        with col_a2:
            if st.button("🗑️ Limpar toda a pré-lista", use_container_width=True):
                if os.path.exists(ARQUIVO_PRE_LISTA):
                    os.remove(ARQUIVO_PRE_LISTA)
                carregar_pre_lista.clear()
                st.rerun()

# ==============================================================================
# PÁGINA 3: GRÁFICOS E ANÁLISE
# ==============================================================================
elif pagina == PAGINAS[2]:
    st.subheader("📊 Gráficos e Análise de Gastos")
    df_compras, df_validos = obter_compras_com_datas()

    if df_compras.empty:
        with st.container(border=True):
            st.info("Você ainda não tem compras registradas. Adicione sua primeira compra em **🛒 Nova Compra**!")
    else:
        mes_atual = date.today().strftime("%Y-%m")
        gasto_mes, media_mensal, delta_mes = 0.0, 0.0, None
        if not df_validos.empty:
            totais_mes = df_validos.groupby("Mês")["Total"].sum()
            gasto_mes, media_mensal = float(totais_mes.get(mes_atual, 0.0)), float(totais_mes.mean())
            meses_ant = [m for m in sorted(totais_mes.index) if m < mes_atual]
            if meses_ant and gasto_mes > 0:
                m_ant = meses_ant[-1]
                delta_mes = f"R$ {gasto_mes - float(totais_mes[m_ant]):+.2f} vs {m_ant[5:]}/{m_ant[:4]}"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Total Geral", formatar_reais(df_compras["Total"].sum()))
        m2.metric("📅 Mês Atual", formatar_reais(gasto_mes), delta=delta_mes, delta_color="inverse")
        m3.metric("📈 Média Mensal", formatar_reais(media_mensal))
        m4.metric("🛍️ Itens", len(df_compras))

        st.write("")
        with st.container(border=True):
            renderizar_graficos_compras(df_compras, df_validos)

# ==============================================================================
# PÁGINA 4: HISTÓRICO DE COMPRAS
# ==============================================================================
elif pagina == PAGINAS[3]:
    st.subheader("🧾 Histórico de Compras")
    df_compras, df_validos = obter_compras_com_datas()

    if df_compras.empty:
        with st.container(border=True):
            st.info("Nenhuma compra no histórico ainda. Cadastre itens em **🛒 Nova Compra**!")
    else:
        with st.container(border=True):
            col_h1, col_h2 = st.columns(2)
            df_exib = df_compras.copy()

            with col_h1:
                if not df_validos.empty:
                    meses = ["Todos"] + sorted(df_validos["Mês"].unique().tolist(), reverse=True)
                    mes_sel = st.selectbox("Filtrar por mês", meses)
                    if mes_sel != "Todos":
                        df_exib = df_exib[df_exib["Data_dt"].dt.strftime("%Y-%m") == mes_sel]

            with col_h2:
                busca_hist = st.text_input("🔎 Buscar no histórico", placeholder="Produto, supermercado ou categoria...").strip()
                if busca_hist:
                    th = normalizar_texto(busca_hist)
                    df_exib = df_exib[df_exib.apply(lambda r: th in normalizar_texto(r["Produto"]) or th in normalizar_texto(r["Supermercado"]) or th in normalizar_texto(r["Categoria"]), axis=1)]

            df_exib = df_exib.sort_values(by="Data_dt", ascending=False, na_position="last")
            df_exib["Data"] = df_exib["Data_dt"]

            st.caption(f"Mostrando **{len(df_exib)}** registros • Total filtrado: **{formatar_reais(df_exib['Total'].sum())}**")
            st.dataframe(
                df_exib[COLUNAS], hide_index=True, use_container_width=True,
                column_config={"Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "Preço Unitário": st.column_config.NumberColumn("Preço Unit.", format="R$ %.2f"), "Total": st.column_config.NumberColumn("Total", format="R$ %.2f")},
            )

        with st.expander("🗑️ Excluir ou Limpar Compras"):
            opcoes_del = {i: f"{r['Data'] or 'Sem data'} | {r['Supermercado'] or '-'} | {r['Produto']} | R$ {r['Total']:.2f}" for i, r in df_compras.iterrows()}
            sels = st.multiselect("Excluir itens específicos:", list(opcoes_del.keys()), format_func=lambda i: opcoes_del[i])
            if st.button("Excluir selecionados", disabled=not sels):
                df_compras.drop(index=sels)[COLUNAS].to_csv(ARQUIVO_CSV, index=False)
                carregar_dados.clear()
                st.rerun()

            st.divider()
            if st.checkbox("Confirmo apagar TODAS as minhas compras") and st.button("🗑️ Limpar tudo", type="primary"):
                if os.path.exists(ARQUIVO_CSV):
                    os.remove(ARQUIVO_CSV)
                carregar_dados.clear()
                st.rerun()

# ==============================================================================
# PÁGINA 5: MENOR PREÇO DA REGIÃO & WHATSAPP
# ==============================================================================
elif pagina == PAGINAS[4]:
    st.subheader("🏆 Comparador de Preços da Região")
    df_com = carregar_comunidade().copy()

    if df_com.empty:
        with st.container(border=True):
            st.info("Ainda não há preços compartilhados. Cadastre uma compra em **🛒 Nova Compra**!")
    else:
        c1, c2 = st.columns(2)
        with c1:
            regs_com = ["Todas"] + sorted([r for r in df_com["Região"].dropna().unique() if str(r).strip()])
            reg_filtro = st.selectbox("Região", regs_com, index=regs_com.index(gps_regiao) if gps_regiao in regs_com else 0, key=f"f_com_{gps_regiao}")
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
            st.markdown(
                f'<div class="listai-winner-card"><h3>🏆 Menor preço: {melhor["Produto"]} por {formatar_reais(melhor["Preço Unitário"])}</h3>'
                f'<div>Encontrado no <strong>{melhor["Supermercado"]}</strong> • {melhor["Região"]}</div></div>',
                unsafe_allow_html=True,
            )

            df_tab = df_ord.copy()
            df_tab["Data"] = df_tab["Data_dt"]
            st.dataframe(
                df_tab[COLUNAS_COMUNIDADE], hide_index=True, use_container_width=True,
                column_config={"Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "Preço Unitário": st.column_config.NumberColumn("Preço Unit.", format="R$ %.2f")},
            )

            with st.container(border=True):
                st.markdown("#### 📲 Compartilhar Ofertas no WhatsApp")
                texto_zap = "\n".join(["🛒 *Melhores preços no Listaí:*", ""] + [f"• *{r['Produto']}*: R$ {r['Preço Unitário']:.2f} ({r['Supermercado']} - {r['Região']})" for _, r in df_ord.head(5).iterrows()])
                st.code(texto_zap, language=None)
                st.link_button("📲 Enviar no WhatsApp", f"https://wa.me/?text={urllib.parse.quote(texto_zap)}", type="primary", use_container_width=True)

        if usuario_atual in USUARIOS_ADMIN:
            with st.expander("👑 Admin — Limpar comunidade"):
                if st.button("Apagar preços compartilhados"):
                    if os.path.exists(ARQUIVO_COMUNIDADE):
                        os.remove(ARQUIVO_COMUNIDADE)
                    carregar_comunidade.clear()
                    st.rerun()

# ==============================================================================
# PÁGINA 6: SUPERMERCADOS DA REGIÃO
# ==============================================================================
elif pagina == PAGINAS[5]:
    st.subheader("🗺️ Supermercados na Região")
    raio_km = st.radio("Raio de busca:", [3, 5, 10], index=0, horizontal=True, format_func=lambda x: f"{x} km")

    if gps_coords:
        lat_g, lon_g = gps_coords
        if st.button("🔄 Buscar e cadastrar neste raio", type="primary", use_container_width=True):
            with st.spinner(f"Buscando em {raio_km} km..."):
                try:
                    nova = consultar_overpass_mercados(lat_g, lon_g, raio_km * 1000)
                    novos = registrar_varios_mercados(gps_regiao, [m["Supermercado"] for m in nova]) if nova else 0
                    salvar_preferencias_gps(lat_g, lon_g, gps_regiao)
                    st.session_state.update({
                        "gps_detalhes": nova,
                        "gps_mercados": _resumir_mercados(nova),
                        "gps_raio_atual": raio_km,
                        "gps_novos_salvos": novos,
                    })
                    st.rerun()
                except Exception as erro:
                    st.warning(f"⚠️ {erro}")

        if lista_gps := st.session_state.get("gps_detalhes", []):
            exibir_tabela_e_mapa_regiao(lista_gps, f"✅ **{len(lista_gps)}** estabelecimentos em **{gps_regiao}** ({st.session_state.get('gps_raio_atual', 3)} km) cadastrados automaticamente!")
        else:
            st.info(f"Região atual: **{gps_regiao}**. Clique em **🔄 Buscar e cadastrar neste raio** para ver o mapa completo.")
    else:
        st.info("Para usar o GPS automático, abra a barra lateral esquerda → **📍 Localização GPS** ou pesquise sua cidade manualmente logo abaixo.")

    st.divider()
    with st.expander("🔎 Pesquisar Cidade / Bairro / CEP manualmente"):
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
                    st.session_state["res_manual"] = {"regiao": reg_busca, "nome_local": nome_loc, "lista": lista_m, "novos": novos_m}
                    st.rerun()
                except Exception as erro:
                    st.warning(f"⚠️ {erro}")

        if res := st.session_state.get("res_manual"):
            if not res["nome_local"]:
                st.error("Localização não encontrada. Tente Cidade e Estado.")
            elif not res["lista"]:
                st.warning("Nenhum supermercado encontrado nesse raio.")
            else:
                exibir_tabela_e_mapa_regiao(res["lista"], f"✅ **{len(res['lista'])}** em **{res['nome_local']}** (+{res['novos']} salvos em **'{res['regiao']}'**).")

# --- Rodapé discreto ---
exibir_rodape_anuncio()