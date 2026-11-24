import base64
from datetime import date
import hashlib
import html
import io
import json
import math
import os
import random
import re
import secrets
import unicodedata
import urllib.parse

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

st.set_page_config(page_title="Listaí — Preços e Compras", page_icon="🛒", layout="wide", initial_sidebar_state="collapsed")

# --- Tema Fixo Verde Listaí + Topo Nubank + Voz WhatsApp + Barra Inferior Fixa ---
st.markdown(
"""<style>
html, body, .stApp { background-color: #F3F8F5 !important; color: #132A1E !important; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif !important; }
.block-container { padding-top: 1rem; padding-bottom: 6.5rem !important; max-width: 1100px; }
h1, h2, h3, h4 { color: #064E3B !important; font-weight: 800 !important; letter-spacing: -0.3px; }
label, .stMarkdown p, .stCheckbox p, .stRadio p { color: #132A1E !important; }
[data-testid="stCaptionContainer"] p, small { color: #475569 !important; font-size: 0.84rem !important; }
section[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* Topo Estilo Nubank */
.st-key-topo_nubank { background: linear-gradient(135deg, #064E3B 0%, #15803D 55%, #16A34A 100%) !important; border-radius: 18px !important; padding: 0.95rem 1.25rem !important; margin-bottom: 0.9rem !important; box-shadow: 0 8px 24px rgba(21, 128, 61, 0.24) !important; }
.st-key-topo_nubank [data-testid="stVerticalBlock"] { background: transparent !important; gap: 0 !important; }
.st-key-topo_nubank [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; align-items: center !important; justify-content: space-between !important; flex-wrap: nowrap !important; gap: 0.65rem !important; }
.st-key-topo_nubank [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; min-width: 0 !important; }
.st-key-topo_nubank [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; width: auto !important; }
.listai-nu-user { display: flex; align-items: center; gap: 0.85rem; min-width: 0; }
.listai-nu-texts { min-width: 0; }
.listai-nu-brand { font-size: 0.74rem; font-weight: 700; color: #BBF7D0; text-transform: uppercase; letter-spacing: 0.7px; }
.listai-nu-hello { font-size: 1.35rem; font-weight: 800; color: #FFFFFF; line-height: 1.15; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.listai-nu-sub { font-size: 0.82rem; color: #DCFCE7; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.st-key-topo_nubank .stButton > button, .st-key-topo_nubank button[kind="secondary"], .st-key-topo_nubank button[data-testid="stBaseButton-secondary"] {
    background: #FFFFFF !important; border: 2px solid #DCFCE7 !important; color: #064E3B !important; border-radius: 999px !important;
    padding: 0.44rem 1.05rem !important; font-size: 0.86rem !important; font-weight: 800 !important; white-space: nowrap !important; box-shadow: 0 3px 12px rgba(0, 0, 0, 0.20) !important; opacity: 1 !important;
}
.st-key-topo_nubank .stButton > button:hover, .st-key-topo_nubank button[kind="secondary"]:hover, .st-key-topo_nubank button[data-testid="stBaseButton-secondary"]:hover { background: #ECFDF5 !important; border-color: #FFFFFF !important; transform: translateY(-1px); }
.st-key-topo_nubank .stButton > button p, .st-key-topo_nubank .stButton > button span { color: #064E3B !important; font-weight: 800 !important; }

/* Botão de Voz Estilo WhatsApp */
.st-key-zap_voz { background: #ECFDF5 !important; border: 1px solid #86EFAC !important; border-radius: 999px !important; padding: 0.35rem 0.65rem 0.35rem 1rem !important; margin: 0.35rem 0 0.55rem 0 !important; }
.st-key-zap_voz [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; align-items: center !important; gap: 0.6rem !important; flex-wrap: nowrap !important; }
.st-key-zap_voz [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; min-width: 0 !important; }
.st-key-zap_voz [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; min-width: 155px !important; }
.listai-zap-hint { line-height: 1.15; }
.listai-zap-hint strong { display: block; font-size: 0.86rem; color: #064E3B; }
.listai-zap-hint small { display: block; font-size: 0.74rem !important; color: #15803D !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.st-key-zap_voz [data-testid="stAudioInput"] > div { background: #FFFFFF !important; border: 1px solid #BBF7D0 !important; border-radius: 999px !important; padding: 0.18rem 0.4rem !important; box-shadow: 0 2px 6px rgba(22, 163, 74, 0.10) !important; }
.st-key-zap_voz [data-testid="stAudioInput"] button:first-of-type { background: #25D366 !important; color: #FFFFFF !important; border-radius: 50% !important; border: none !important; box-shadow: 0 2px 8px rgba(37, 211, 102, 0.40) !important; }
.st-key-zap_voz [data-testid="stAudioInput"] button:first-of-type:hover { background: #16A34A !important; transform: scale(1.05); }
.st-key-zap_voz [data-testid="stAudioInput"] button:first-of-type svg { color: #FFFFFF !important; fill: #FFFFFF !important; }

/* Avatares e Foto Clicável no Perfil */
.listai-avatar { border-radius: 50%; background: rgba(255, 255, 255, 0.22); border: 2px solid rgba(255, 255, 255, 0.88); color: #FFFFFF; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.listai-avatar-solid { border-radius: 50%; background: linear-gradient(135deg, #064E3B, #16A34A); border: 2px solid #86EFAC; color: #FFFFFF; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.listai-avatar-img { border-radius: 50%; object-fit: cover; border: 2px solid rgba(255, 255, 255, 0.92); flex-shrink: 0; display: block; box-shadow: 0 3px 10px rgba(0, 0, 0, 0.18); }
.st-key-perfil_hero_top [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; align-items: center !important; gap: 1rem !important; flex-wrap: nowrap !important; }
.st-key-perfil_hero_top [data-testid="stColumn"]:first-child { flex: 0 0 84px !important; width: 84px !important; min-width: 84px !important; }
.st-key-perfil_hero_top [data-testid="stColumn"]:last-child { flex: 1 1 auto !important; min-width: 0 !important; }
.st-key-avatar_clicavel { position: relative !important; width: 84px !important; height: 84px !important; min-width: 84px !important; min-height: 84px !important; border-radius: 50% !important; cursor: pointer !important; }
.st-key-avatar_clicavel [data-testid="stVerticalBlock"] { position: relative !important; width: 84px !important; height: 84px !important; gap: 0 !important; }
.listai-avatar-wrap { position: relative; width: 84px; height: 84px; transition: transform 0.15s ease, filter 0.15s ease; }
.st-key-avatar_clicavel:hover .listai-avatar-wrap { transform: scale(1.03); filter: brightness(0.92); }
.listai-cam-badge { position: absolute; right: 0; bottom: 0; width: 28px; height: 28px; border-radius: 50%; background: #16A34A; border: 2px solid #FFFFFF; color: #FFFFFF; font-size: 13px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25); pointer-events: none; }
.st-key-avatar_clicavel [data-testid="stElementContainer"]:has([data-testid="stFileUploader"]),
.st-key-avatar_clicavel .element-container:has([data-testid="stFileUploader"]),
.st-key-avatar_clicavel [data-testid="stFileUploader"] { position: absolute !important; inset: 0 !important; width: 84px !important; height: 84px !important; opacity: 0.001 !important; z-index: 20 !important; margin: 0 !important; padding: 0 !important; overflow: hidden !important; border-radius: 50% !important; }
.st-key-avatar_clicavel [data-testid="stFileUploaderDropzone"],
.st-key-avatar_clicavel [data-testid="stFileUploaderDropzone"] > span,
.st-key-avatar_clicavel [data-testid="stFileUploaderDropzone"] button { position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; min-height: 84px !important; padding: 0 !important; margin: 0 !important; border: none !important; border-radius: 50% !important; cursor: pointer !important; }
.st-key-avatar_clicavel [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }

/* Header Login e Cards */
.listai-header { background: linear-gradient(135deg, #064E3B 0%, #15803D 55%, #16A34A 100%); padding: 1.15rem 1.4rem; border-radius: 16px; color: #FFFFFF !important; margin-bottom: 0.8rem; box-shadow: 0 8px 22px rgba(21, 128, 61, 0.22); }
.listai-header-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.6rem; }
.listai-brand { display: flex; align-items: center; gap: 0.75rem; }
.listai-logo-badge { background: #FFFFFF; width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 10px rgba(0, 0, 0, 0.14); flex-shrink: 0; }
.listai-header h1 { margin: 0 !important; font-size: 1.7rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
.listai-header p { margin: 0.25rem 0 0 0 !important; font-size: 0.9rem !important; color: #DCFCE7 !important; font-weight: 500; }
.listai-pill { background: rgba(255, 255, 255, 0.2); color: #FFFFFF !important; padding: 0.22rem 0.75rem; border-radius: 999px; font-size: 0.74rem; font-weight: 700; border: 1px solid rgba(255, 255, 255, 0.3); }
.listai-winner-card { background: linear-gradient(135deg, #ECFDF5 0%, #DCFCE7 100%); border: 1px solid #86EFAC; border-left: 6px solid #16A34A; border-radius: 16px; padding: 1rem 1.25rem; color: #064E3B; margin-bottom: 0.9rem; box-shadow: 0 4px 12px rgba(22, 163, 74, 0.10); display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; }
.listai-winner-card h3 { margin: 0 0 0.2rem 0 !important; font-size: 1.15rem !important; color: #064E3B !important; }
.listai-winner-price { font-size: 1.45rem; font-weight: 800; color: #15803D; text-align: right; }
.listai-eco-pill { display: inline-block; background: #16A34A; color: #FFFFFF; font-size: 0.74rem; font-weight: 700; padding: 0.18rem 0.6rem; border-radius: 999px; margin-top: 4px; }
.listai-profile-info h3 { margin: 0 !important; font-size: 1.2rem !important; color: #064E3B !important; }
.listai-profile-info span { color: #475569; font-size: 0.86rem; display: block; margin-top: 2px; }
.listai-foto-dica { color: #15803D !important; font-weight: 600; font-size: 0.82rem !important; margin-top: 4px !important; }
.listai-ad-badge { display: inline-block; background: #DCFCE7; color: #166534; font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 6px; margin-bottom: 0.25rem; }
.listai-mini-status { font-size: 0.81rem; color: #475569; margin: 0.35rem 0 0.2rem 0; }

/* Histórico, Lista Geral e Ranking de Preços */
.listai-hist-card { background: #FFFFFF; border: 1px solid #D1FAE5; border-left: 5px solid #16A34A; border-radius: 14px; padding: 0.85rem 1rem 0.65rem 1rem; margin-bottom: 0.35rem; box-shadow: 0 2px 10px rgba(6, 78, 59, 0.05); }
.listai-hist-head { display: flex; justify-content: space-between; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.listai-hist-title { font-size: 1.02rem; font-weight: 800; color: #064E3B; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; }
.listai-hist-badge { background: #ECFDF5; color: #15803D; border: 1px solid #BBF7D0; font-size: 0.73rem; font-weight: 700; padding: 0.12rem 0.55rem; border-radius: 999px; }
.listai-hist-total { font-size: 1.08rem; font-weight: 800; color: #15803D; }
.listai-hist-track { width: 100%; height: 6px; background: #ECFDF5; border-radius: 999px; overflow: hidden; margin-top: 0.55rem; }
.listai-hist-fill { height: 100%; background: linear-gradient(90deg, #22C55E, #15803D); border-radius: 999px; }
.listai-hist-item { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; padding: 0.52rem 0.2rem; border-bottom: 1px solid #F1F5F9; }
.listai-hist-item:last-child, .listai-feed-row:last-child { border-bottom: none; }
.listai-hist-prod, .listai-feed-name { font-weight: 700; color: #132A1E; font-size: 0.94rem; }
.listai-hist-meta { font-size: 0.80rem; color: #64748B; margin-top: 2px; }
.listai-hist-right { text-align: right; flex-shrink: 0; }
.listai-hist-val { font-weight: 800; color: #064E3B; font-size: 0.95rem; }
.listai-hist-unit { font-size: 0.76rem; color: #64748B; }
.listai-diff-up { font-size: 0.75rem; color: #B45309; font-weight: 700; }
.listai-diff-best { font-size: 0.75rem; color: #15803D; font-weight: 700; }
.listai-feed-day { display: flex; justify-content: space-between; align-items: center; margin: 0.85rem 0 0.35rem 0; padding: 0 0.25rem; font-size: 0.83rem; font-weight: 800; color: #064E3B; }
.listai-feed-day span:last-child { color: #15803D; }
.listai-feed-box { background: #FFFFFF; border: 1px solid #D1FAE5; border-radius: 16px; padding: 0.25rem 0.95rem; margin-bottom: 0.65rem; box-shadow: 0 2px 10px rgba(6, 78, 59, 0.05); }
.listai-feed-row { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; padding: 0.68rem 0; border-bottom: 1px solid #F1F5F9; }
.listai-feed-left { display: flex; align-items: center; gap: 0.75rem; min-width: 0; }
.listai-feed-ico { width: 38px; height: 38px; border-radius: 11px; background: #ECFDF5; border: 1px solid #BBF7D0; display: flex; align-items: center; justify-content: center; font-size: 1.05rem; font-weight: 800; color: #064E3B; flex-shrink: 0; }
.listai-feed-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 4px; align-items: center; }
.listai-feed-tag { background: #F1F5F9; color: #334155; font-size: 0.73rem; font-weight: 600; padding: 0.1rem 0.48rem; border-radius: 6px; }
.listai-feed-tag-cat { background: #ECFDF5; color: #15803D; }

/* Botões e Métricas */
div[data-testid="stMetric"] { background-color: #FFFFFF !important; border: 1px solid #D1FAE5 !important; border-left: 5px solid #16A34A !important; padding: 14px 18px; border-radius: 14px; box-shadow: 0 2px 8px rgba(6, 78, 59, 0.05); }
div[data-testid="stMetricLabel"] p { color: #334155 !important; font-weight: 600 !important; font-size: 0.88rem !important; }
div[data-testid="stMetricValue"] { color: #064E3B !important; font-weight: 800 !important; }
.stButton > button, .stLinkButton > a, .stFormSubmitButton > button { border-radius: 10px !important; font-weight: 600 !important; font-size: 0.92rem !important; transition: all 0.15s ease; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background-color: #16A34A !important; border: none !important; color: #FFFFFF !important; }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover { background-color: #15803D !important; box-shadow: 0 4px 12px rgba(22, 163, 74, 0.28); }
.stButton > button[kind="secondary"] { background-color: #FFFFFF !important; border: 1px solid #BBF7D0 !important; color: #064E3B !important; }
.stButton > button[kind="secondary"]:hover { border-color: #16A34A !important; background-color: #ECFDF5 !important; color: #064E3B !important; }
div[data-testid="stProgress"] > div > div > div > div { background-color: #16A34A !important; }

/* Barra Inferior Fixa */
.st-key-barra_inferior { position: fixed !important; bottom: 10px !important; left: 50% !important; transform: translateX(-50%) !important; width: min(1060px, calc(100vw - 24px)) !important; z-index: 99999 !important; background: rgba(255, 255, 255, 0.96) !important; backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important; border: 1px solid #86EFAC !important; border-radius: 18px !important; padding: 0.35rem 0.45rem !important; box-shadow: 0 8px 28px rgba(6, 78, 59, 0.22) !important; }
.st-key-barra_inferior [data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-key-barra_inferior [data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: repeat(6, minmax(0, 1fr)) !important; gap: 0.25rem !important; width: 100% !important; }
.st-key-barra_inferior [data-testid="stColumn"] { width: 100% !important; min-width: 0 !important; }
.st-key-barra_inferior .stButton > button { border-radius: 12px !important; padding: 0.38rem 0.2rem !important; min-height: 2.85rem !important; line-height: 1.15 !important; box-shadow: none !important; }
.st-key-barra_inferior .stButton > button p { font-size: 0.76rem !important; font-weight: 700 !important; line-height: 1.15 !important; margin: 0 !important; }
.st-key-barra_inferior .stButton > button[kind="secondary"] { background: transparent !important; border: none !important; color: #334155 !important; }
.st-key-barra_inferior .stButton > button[kind="secondary"]:hover { background: #ECFDF5 !important; color: #064E3B !important; }
.st-key-barra_inferior .stButton > button[kind="primary"] { background: linear-gradient(135deg, #15803D, #16A34A) !important; color: #FFFFFF !important; box-shadow: 0 3px 10px rgba(22, 163, 74, 0.28) !important; }
.st-key-barra_inferior .stButton > button[kind="primary"] p { color: #FFFFFF !important; }

@media (max-width: 680px) {
    .block-container { padding-bottom: 8.8rem !important; }
    .st-key-barra_inferior [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; }
    .st-key-zap_voz [data-testid="stColumn"]:last-child { min-width: 135px !important; }
}
</style>""",
unsafe_allow_html=True,
)

LOGO_SVG = (
    '<div class="listai-logo-badge"><svg width="26" height="26" viewBox="0 0 24 24" fill="none">'
    '<defs><linearGradient id="lg" x1="0" y1="12" x2="24" y2="4" gradientUnits="userSpaceOnUse">'
    '<stop offset="0%" stop-color="#0077E6"/><stop offset="55%" stop-color="#00B8B0"/><stop offset="100%" stop-color="#16A34A"/></linearGradient></defs>'
    '<path d="M2 4H5L7.4 14.5C7.6 15.4 8.4 16 9.3 16H17.5C18.4 16 19.2 15.4 19.4 14.5L21 7H6" stroke="url(#lg)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M9.5 10.2L12 12.6L19.5 4.8" stroke="url(#lg)" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="9.5" cy="19.5" r="1.6" fill="#0077E6"/><circle cx="17" cy="19.5" r="1.6" fill="#16A34A"/></svg></div>'
)

# --- Configurações e Constantes ---
PASTA_DADOS_USUARIOS, ARQUIVO_COMUNIDADE, ARQUIVO_MERCADOS, ARQUIVO_USUARIOS = "dados_usuarios", "precos_comunidade.csv", "supermercados.json", "usuarios.json"
NAV_ITENS = [("🛒", "Compra"), ("📝", "Lista"), ("📊", "Gráficos"), ("🧾", "Histórico"), ("🏆", "Preços"), ("🗺️", "Mercados")]
PAGINAS = [f"{ico} {txt}" for ico, txt in NAV_ITENS]
PAGINA_PERFIL = "👤 Perfil"

COLUNAS = ["Data", "Região", "Supermercado", "Produto", "Categoria", "Quantidade", "Preço Unitário", "Total"]
COLUNAS_PRE_LISTA = ["ID", "Produto", "Quantidade", "Categoria", "Comprado"]
COLUNAS_COMUNIDADE = ["Data", "Região", "Supermercado", "Produto", "Categoria", "Preço Unitário", "Usuário"]
OVERPASS_SERVERS = ["https://overpass.private.coffee/api/interpreter", "https://z.overpass-api.de/api/interpreter", "https://overpass-api.de/api/interpreter"]
TRADUCAO_LOJA = {"supermarket": "Supermercado", "wholesale": "Atacarejo", "convenience": "Mercearia / Minimercado", "greengrocer": "Hortifruti / Sacolão"}
EXTENSOES_FOTO = ("jpg", "png", "webp")

ANUNCIOS = [
    {"titulo": "🔥 Ofertas de Supermercado na Amazon", "descricao": "Descontos em limpeza, café, bebidas e despensa com entrega rápida.", "texto_botao": "Ver na Amazon", "url": "https://www.amazon.com.br/"},
    {"titulo": "🛒 Mercado Livre — Compras do Mês", "descricao": "Compare preços e aproveite cupons e frete grátis na sua compra.", "texto_botao": "Abrir Ofertas", "url": "https://www.mercadolivre.com.br/"},
    {"titulo": "🏷️ Achadinhos e Ofertas na Shopee", "descricao": "Utilidades domésticas e itens para casa com super desconto.", "texto_botao": "Ver na Shopee", "url": "https://shopee.com.br/"},
]

ICONES_CATEGORIA = {
    "Alimentos": "🍚", "Bebidas": "🥤", "Hortifruti": "🥬", "Açougue e Peixaria": "🥩",
    "Frios e Laticínios": "🧀", "Padaria": "🥖", "Limpeza": "🧽", "Higiene Pessoal": "🧴",
    "Pet Shop": "🐾", "Utilidades Domésticas": "🏠", "Outros": "📦",
}
LISTA_CATEGORIAS = list(ICONES_CATEGORIA.keys())

CATEGORIAS_FALLBACK = {
    "Açougue e Peixaria": ["carne", "picanha", "alcatra", "patinho", "acem", "bisteca", "costela", "linguica", "salsicha", "frango", "peixe", "tilapia", "salmao", "camarao", "bacalhau"],
    "Frios e Laticínios": ["queijo", "mussarela", "requeijao", "presunto", "mortadela", "manteiga", "margarina", "iogurte", "creme de leite", "leite condensado", "nata"],
    "Padaria": ["pao", "pao de forma", "bisnaguinha", "bolo", "torta", "croissant", "broa", "rosquinha"],
    "Higiene Pessoal": ["papel higienico", "sabonete", "shampoo", "condicionador", "creme dental", "pasta de dente", "escova de dente", "desodorante", "absorvente", "fralda", "barbeador"],
    "Limpeza": ["agua sanitaria", "detergente", "sabao", "desinfetante", "amaciante", "esponja", "alvejante", "limpador", "multiuso", "saco de lixo", "vassoura", "rodo"],
    "Pet Shop": ["racao", "petisco", "areia higienica", "tapete higienico", "coleira"],
    "Utilidades Domésticas": ["papel aluminio", "papel toalha", "filme pvc", "guardanapo", "vela", "fosforo", "lampada", "pilha"],
    "Bebidas": ["agua", "refrigerante", "suco", "cerveja", "vinho", "leite", "cafe", "cha", "energetico", "achocolatado"],
    "Hortifruti": ["banana", "maca", "laranja", "uva", "mamao", "melancia", "abacaxi", "limao", "morango", "tomate", "cebola", "batata", "cenoura", "alface", "couve", "pepino", "abobora", "alho", "brocolis"],
    "Alimentos": ["arroz", "feijao", "macarrao", "ovo", "farinha", "acucar", "sal", "biscoito", "bolacha", "oleo", "azeite", "vinagre", "molho", "milho", "ervilha", "atum", "sardinha", "aveia", "chocolate"],
}


# --- Utilitários ---
def ler_json(caminho, padrao):
    if os.path.exists(caminho) and os.path.getsize(caminho) > 0:
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return padrao() if callable(padrao) else padrao


def salvar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def obter_arquivo_usuario(usuario, nome_arquivo):
    u_norm = str(usuario or "usuario").strip().lower()
    slug = re.sub(r"[^a-z0-9_-]", "_", u_norm).strip("_") or "usuario"
    pasta = os.path.join(PASTA_DADOS_USUARIOS, f"{slug[:32]}_{hashlib.sha256(u_norm.encode()).hexdigest()[:8]}")
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, nome_arquivo)


def normalizar_texto(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower().strip()) if unicodedata.category(c) != "Mn")


def formatar_reais(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_delta_reais(valor):
    return f"{'+' if valor >= 0 else '-'}{formatar_reais(abs(valor))}"


def obter_iniciais(nome):
    p = [x for x in str(nome or "").strip().split() if x]
    return "US" if not p else (p[0][:2].upper() if len(p) == 1 else (p[0][0] + p[-1][0]).upper())


def rolar_para_topo():
    components.html("<script>setTimeout(()=>{const d=window.parent.document,m=d.querySelector('section[data-testid=\"stMain\"]')||d.querySelector('section.main');if(m)m.scrollTo({top:0,behavior:'smooth'});window.parent.scrollTo({top:0,behavior:'smooth'});},40);</script>", height=0)


def obter_usuarios_admin():
    admins = {"admin"}
    if env := os.getenv("LISTAI_ADMINS", ""):
        admins.update(a.strip().lower() for a in env.split(",") if a.strip())
    try:
        sec = st.secrets.get("ADMIN_USERS", [])
        if isinstance(sec, str):
            admins.update(a.strip().lower() for a in sec.split(",") if a.strip())
        elif isinstance(sec, (list, tuple, set)):
            admins.update(str(a).strip().lower() for a in sec if str(a).strip())
    except Exception:
        pass
    return admins


def obter_api_key_gemini():
    if chave := os.getenv("GEMINI_API_KEY"):
        return chave.strip() or None, "ambiente"
    try:
        if chave := st.secrets.get("GEMINI_API_KEY"):
            return str(chave).strip() or None, "secrets"
    except Exception:
        pass
    chave = st.session_state.get("gemini_api_key_usuario", "").strip()
    return (chave or None), ("perfil" if chave else "")


def limpar_estado_usuario(incluir_auth=False):
    chaves = {"aviso_voz", "ultimo_audio_hash", "msg_sucesso", "msg_limite_alerta", "gps_ultima_leitura", "gps_coords", "gps_regiao", "gps_mercados", "gps_detalhes", "gps_raio_atual", "gps_usuario_owner", "sel_reg_compra", "sel_merc_compra", "regiao_para_selecionar", "merc_para_selecionar", "input_nova_regiao", "res_manual", "ultima_foto_hash", "foto_versao"}
    if incluir_auth:
        st.session_state.update({"autenticado": False, "usuario_logado": ""})
        chaves.update({"modo_login", "gemini_api_key_usuario", "pagina_atual", "pagina_anterior"})
    for k in list(st.session_state.keys()):
        if k.startswith(("num_lim_", "chk_bloq_", "up_foto_", "audio_zap_")) or k in chaves:
            st.session_state.pop(k, None)


# --- Foto de Perfil ---
@st.cache_data(show_spinner=False)
def carregar_foto_perfil_base64(usuario):
    for ext in EXTENSOES_FOTO:
        p = obter_arquivo_usuario(usuario, f"foto_perfil.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii"), f"image/{'jpeg' if ext == 'jpg' else ext}"
    return None


def remover_foto_perfil(usuario):
    for ext in EXTENSOES_FOTO:
        if os.path.exists(p := obter_arquivo_usuario(usuario, f"foto_perfil.{ext}")):
            os.remove(p)
    carregar_foto_perfil_base64.clear()


def salvar_foto_perfil(usuario, raw_bytes, nome_arquivo=""):
    remover_foto_perfil(usuario)
    try:
        from PIL import Image, ImageOps
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw_bytes)))
        lado = min(img.size)
        l, t = (img.width - lado) // 2, (img.height - lado) // 2
        img = img.crop((l, t, l + lado, t + lado)).resize((256, 256))
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.save(obter_arquivo_usuario(usuario, "foto_perfil.jpg"), format="JPEG", quality=88)
    except ImportError:
        ext = os.path.splitext(nome_arquivo.lower())[1].lstrip(".")
        ext = "jpg" if ext == "jpeg" else (ext if ext in EXTENSOES_FOTO else "jpg")
        with open(obter_arquivo_usuario(usuario, f"foto_perfil.{ext}"), "wb") as f:
            f.write(raw_bytes)
    carregar_foto_perfil_base64.clear()


def avatar_html(nome, usuario, tamanho=52, solido=False):
    if foto := carregar_foto_perfil_base64(usuario):
        borda = "border: 2px solid #86EFAC;" if solido else ""
        return f'<img src="data:{foto[1]};base64,{foto[0]}" class="listai-avatar-img" style="width:{tamanho}px;height:{tamanho}px;{borda}" alt="Foto">'
    classe = "listai-avatar-solid" if solido else "listai-avatar"
    return f'<div class="{classe}" style="width:{tamanho}px;height:{tamanho}px;font-size:{max(14, int(tamanho * 0.36))}px;">{obter_iniciais(nome)}</div>'


# --- Clientes em Cache ---
@st.cache_resource
def obter_http_session():
    import requests
    sess = requests.Session()
    sess.headers.update({"User-Agent": "ListaiApp/1.0"})
    return sess


@st.cache_resource
def obter_gemini_client(api_key):
    from google import genai
    return genai.Client(api_key=api_key)


# --- Autenticação ---
def gerar_hash_senha(senha, salt=None):
    salt = salt or secrets.token_hex(16)
    return f"{salt}${hashlib.sha256((salt + senha).encode()).hexdigest()}"


def verificar_senha(digitada, salva):
    if "$" not in salva:
        return False
    salt, esperado = salva.split("$", 1)
    return secrets.compare_digest(hashlib.sha256((salt + digitada).encode()).hexdigest(), esperado)


@st.cache_data(show_spinner=False)
def carregar_usuarios():
    if dados := ler_json(ARQUIVO_USUARIOS, dict):
        return dados
    iniciais = {"teste": {"tipo": "senha", "hash": gerar_hash_senha("1234"), "nome": "Conta Teste", "criado_em": date.today().isoformat()}}
    salvar_json(ARQUIVO_USUARIOS, iniciais)
    return iniciais


def salvar_usuarios(usuarios):
    salvar_json(ARQUIVO_USUARIOS, usuarios)
    carregar_usuarios.clear()


def exibir_tela_login():
    st.session_state.setdefault("modo_login", "entrar")
    _, col_c, _ = st.columns([1, 1.8, 1])
    with col_c:
        st.markdown(f'<div class="listai-header"><div class="listai-header-top"><div class="listai-brand">{LOGO_SVG}<h1>Listaí</h1></div><span class="listai-pill">PREÇOS E COMPRAS</span></div><p>Sua lista inteligente e os melhores preços da região.</p></div>', unsafe_allow_html=True)
        usuarios = carregar_usuarios()

        with st.container(border=True):
            if st.session_state["modo_login"] == "entrar":
                st.subheader("🔐 Entrar")
                with st.form("form_login", border=False):
                    u_in = st.text_input("Usuário", placeholder="Seu usuário")
                    s_in = st.text_input("Senha", type="password", placeholder="Sua senha")
                    if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                        u = u_in.strip().lower()
                        reg = usuarios.get(u)
                        h = reg.get("hash", "") if isinstance(reg, dict) else (reg or "")
                        if reg is not None and verificar_senha(s_in, h):
                            st.session_state.update({"autenticado": True, "usuario_logado": u, "nome_usuario": reg.get("nome", u) if isinstance(reg, dict) else u})
                            st.session_state.pop("modo_login", None)
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
                st.divider()
                if st.button("📝 Criar nova conta", use_container_width=True):
                    st.session_state["modo_login"] = "cadastro"
                    st.rerun()
            else:
                st.subheader("📝 Criar Conta")
                with st.form("form_cadastro", border=False):
                    st.markdown("**Informações Pessoais**")
                    nome_p = st.text_input("Nome completo *", placeholder="Ex: Maria Silva")
                    c1, c2 = st.columns(2)
                    email_p = c1.text_input("E-mail (opcional)", placeholder="maria@email.com")
                    tel_p = c2.text_input("Telefone / WhatsApp (opcional)", placeholder="(11) 99999-9999")
                    cid_p = st.text_input("Cidade / Bairro (opcional)", placeholder="Ex: Campinas - Centro")
                    st.markdown("**Dados de Acesso**")
                    a1, a2 = st.columns(2)
                    novo_u = a1.text_input("Usuário *", placeholder="Ex: maria")
                    nova_s = a2.text_input("Senha *", type="password", placeholder="Mín. 4 caracteres")

                    if st.form_submit_button("✅ Criar conta e entrar", type="primary", use_container_width=True):
                        nome_ok, nl = nome_p.strip(), novo_u.strip().lower()
                        if len(nome_ok) < 2:
                            st.warning("Digite seu nome completo.")
                        elif len(nl) < 2:
                            st.warning("O usuário deve ter pelo menos 2 caracteres.")
                        elif nl in usuarios:
                            st.error("Esse usuário já existe. Escolha outro.")
                        elif len(nova_s) < 4:
                            st.warning("A senha deve ter pelo menos 4 caracteres.")
                        else:
                            u_edit = usuarios.copy()
                            u_edit[nl] = {"tipo": "senha", "hash": gerar_hash_senha(nova_s), "nome": nome_ok, "email": email_p.strip(), "telefone": tel_p.strip(), "cidade": cid_p.strip(), "criado_em": date.today().isoformat()}
                            salvar_usuarios(u_edit)
                            st.session_state.update({"autenticado": True, "usuario_logado": nl, "nome_usuario": nome_ok, "msg_sucesso": f"Conta criada! Bem-vindo(a), **{nome_ok}**."})
                            st.session_state.pop("modo_login", None)
                            st.rerun()
                st.divider()
                if st.button("← Já tenho conta (Voltar para Entrar)", use_container_width=True):
                    st.session_state["modo_login"] = "entrar"
                    st.rerun()


if not st.session_state.get("autenticado", False):
    exibir_tela_login()
    st.stop()

usuario_atual = st.session_state.get("usuario_logado", "usuario")
nome_usuario = st.session_state.get("nome_usuario", usuario_atual)
USUARIOS_ADMIN = obter_usuarios_admin()


# --- Localização, Orçamento e Supermercados ---
@st.cache_data(show_spinner=False)
def carregar_preferencias_gps(usuario):
    return ler_json(obter_arquivo_usuario(usuario, "preferencias_gps.json"), dict)


def salvar_preferencias_gps(lat, lon, regiao, usuario):
    salvar_json(obter_arquivo_usuario(usuario, "preferencias_gps.json"), {"lat": lat, "lon": lon, "regiao": regiao})
    carregar_preferencias_gps.clear()


@st.cache_data(show_spinner=False)
def carregar_orcamento_mensal(usuario):
    dados = ler_json(obter_arquivo_usuario(usuario, "orcamento.json"), dict)
    try:
        return {"limite": max(0.0, float(dados.get("limite", 0.0))), "bloquear": bool(dados.get("bloquear", False))}
    except (TypeError, ValueError):
        return {"limite": 0.0, "bloquear": False}


def salvar_orcamento_mensal(limite, bloquear, usuario):
    salvar_json(obter_arquivo_usuario(usuario, "orcamento.json"), {"limite": max(0.0, float(limite)), "bloquear": bool(bloquear)})
    carregar_orcamento_mensal.clear()
    for k in list(st.session_state.keys()):
        if k.startswith(("num_lim_", "chk_bloq_")):
            st.session_state.pop(k, None)


def calcular_distancia_metros(lat1, lon1, lat2, lon2):
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return int(2 * 6371000 * math.asin(math.sqrt(a)))


def _registrar_ponto_mercado(enc, nome, tipo, end, elat, elon, dist):
    chave = f"{nome}|{round(elat, 4)}|{round(elon, 4)}"
    if chave not in enc or dist < enc[chave]["Distância (m)"]:
        enc[chave] = {"Supermercado": nome, "Tipo": tipo, "Endereço": end or "-", "Distância (m)": dist, "lat": elat, "lon": elon}


def consultar_photon_mercados(lat, lon, raio):
    http = obter_http_session()
    d_lat, d_lon = raio / 111320.0, raio / (111320.0 * max(0.2, abs(math.cos(math.radians(lat)))))
    bbox, enc, ok = f"{lon - d_lon},{lat - d_lat},{lon + d_lon},{lat + d_lat}", {}, False
    for termo in ("supermercado", "atacadao", "mercado"):
        try:
            resp = http.get("https://photon.komoot.io/api/", params={"q": termo, "lat": lat, "lon": lon, "bbox": bbox, "limit": 25}, timeout=5)
            if resp.status_code != 200:
                continue
            ok = True
            for feat in resp.json().get("features", []):
                props, coords = feat.get("properties", {}), feat.get("geometry", {}).get("coordinates", [])
                nome = (props.get("name") or "").strip()
                if not nome or len(coords) < 2 or (props.get("osm_key") != "shop" and props.get("osm_value") not in TRADUCAO_LOJA):
                    continue
                dist = calcular_distancia_metros(lat, lon, float(coords[1]), float(coords[0]))
                if dist <= raio:
                    end = ", ".join(p for p in [props.get("street", ""), props.get("district") or props.get("locality") or ""] if p)
                    _registrar_ponto_mercado(enc, nome, TRADUCAO_LOJA.get(props.get("osm_value", ""), "Supermercado"), end, float(coords[1]), float(coords[0]), dist)
        except Exception:
            continue
    return sorted(enc.values(), key=lambda x: x["Distância (m)"]) if ok else None


@st.cache_data(ttl=600, show_spinner=False)
def consultar_overpass_mercados(lat, lon, raio):
    http = obter_http_session()
    filtros = "".join(f'nw(around:{raio},{lat},{lon})["shop"="{s}"];' for s in TRADUCAO_LOJA)
    query = f"[out:json][timeout:6];({filtros});out center tags;"
    for srv in OVERPASS_SERVERS:
        try:
            resp = http.post(srv, data={"data": query}, timeout=6)
            if resp.status_code == 200:
                enc = {}
                for el in resp.json().get("elements", []):
                    tags = el.get("tags", {})
                    nome = (tags.get("name") or tags.get("brand") or "").strip()
                    elat, elon = el.get("lat") or el.get("center", {}).get("lat"), el.get("lon") or el.get("center", {}).get("lon")
                    if nome and elat is not None and elon is not None:
                        end = ", ".join(p for p in [f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip(), tags.get("addr:suburb", "")] if p)
                        _registrar_ponto_mercado(enc, nome, TRADUCAO_LOJA.get(tags.get("shop", "supermarket"), "Supermercado"), end, float(elat), float(elon), calcular_distancia_metros(lat, lon, float(elat), float(elon)))
                return sorted(enc.values(), key=lambda x: x["Distância (m)"])
        except Exception:
            continue
    if (res := consultar_photon_mercados(lat, lon, raio)) is not None:
        return res
    raise RuntimeError("Servidores de mapa ocupados no momento. Tente novamente em instantes.")


def _resumir_mercados(lista):
    vistos, out = set(), []
    for x in lista:
        if x["Supermercado"] not in vistos:
            vistos.add(x["Supermercado"])
            out.append((x["Supermercado"], x["Distância (m)"]))
    return out


@st.cache_data(ttl=600, show_spinner=False)
def buscar_regiao_e_mercados_proximos(lat, lon):
    regiao = ""
    try:
        r = obter_http_session().get("https://nominatim.openstreetmap.org/reverse", params={"lat": lat, "lon": lon, "format": "json", "accept-language": "pt-BR"}, timeout=5)
        if r.status_code == 200:
            a = r.json().get("address", {})
            cid = a.get("city") or a.get("town") or a.get("municipality") or a.get("village") or ""
            bai = a.get("suburb") or a.get("neighbourhood") or a.get("city_district") or ""
            regiao = f"{cid} - {bai}" if (cid and bai) else (cid or bai)
    except Exception:
        pass
    detalhes = consultar_overpass_mercados(lat, lon, 3000)
    return (regiao or "Minha Região (GPS)"), _resumir_mercados(detalhes), detalhes


@st.cache_data(ttl=600, show_spinner=False)
def buscar_supermercados_por_regiao(texto, raio=3000):
    r = obter_http_session().get("https://nominatim.openstreetmap.org/search", params={"q": texto, "countrycodes": "br", "format": "json", "limit": 1, "accept-language": "pt-BR"}, timeout=6)
    if r.status_code != 200 or not r.json():
        return None, []
    lugar = r.json()[0]
    return lugar.get("display_name", texto), consultar_overpass_mercados(float(lugar["lat"]), float(lugar["lon"]), raio)


@st.cache_data(show_spinner=False)
def carregar_mercados():
    dados = ler_json(ARQUIVO_MERCADOS, dict)
    if isinstance(dados, dict) and dados:
        return dados
    iniciais = {"Centro (Exemplo)": ["Atacadão", "Carrefour", "Supermercado Local"]}
    salvar_json(ARQUIVO_MERCADOS, iniciais)
    return iniciais


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
        salvar_json(ARQUIVO_MERCADOS, mercados)
        carregar_mercados.clear()
    return len(atual) - antes


def processar_leitura_gps(loc, usuario):
    if loc and loc.get("latitude") is not None and loc.get("longitude") is not None:
        lat, lon = round(float(loc["latitude"]), 4), round(float(loc["longitude"]), 4)
        if st.session_state.get("gps_ultima_leitura") != (lat, lon):
            with st.spinner("Localizando supermercados próximos..."):
                try:
                    reg_g, mercs_g, det_g = buscar_regiao_e_mercados_proximos(lat, lon)
                    if det_g:
                        registrar_varios_mercados(reg_g, [m["Supermercado"] for m in det_g])
                    salvar_preferencias_gps(lat, lon, reg_g, usuario)
                    st.session_state.update({"gps_ultima_leitura": (lat, lon), "gps_coords": (lat, lon), "gps_regiao": reg_g, "gps_mercados": mercs_g, "gps_detalhes": det_g, "gps_raio_atual": 3, "regiao_para_selecionar": reg_g, "msg_sucesso": f"Localização atualizada: **{reg_g}**."})
                    st.rerun()
                except Exception as erro:
                    st.warning(f"⚠️ {erro}")


# --- IA (Categorização + Voz) ---
def identificar_categoria_local(produto):
    p_norm = normalizar_texto(produto)
    for cat, palavras in CATEGORIAS_FALLBACK.items():
        if any(re.search(rf"\b{re.escape(normalizar_texto(p))}\b", p_norm) for p in palavras):
            return cat
    return "Outros"


@st.cache_data(ttl=86400, show_spinner=False)
def classificar_com_ia(prod_norm, api_key):
    from google.genai import types
    resp = obter_gemini_client(api_key).models.generate_content(
        model="gemini-3.5-flash-lite", contents=f"Produto: {prod_norm}",
        config=types.GenerateContentConfig(system_instruction=f"Classificador de produtos de mercado no Brasil. Responda APENAS com UMA categoria exata: {', '.join(LISTA_CATEGORIAS)}."),
    )
    limpa = normalizar_texto(resp.text)
    return next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in limpa), "Outros")


@st.cache_data(ttl=86400, show_spinner=False)
def classificar_lote_com_ia(prods_norm, api_key):
    from google.genai import types
    resp = obter_gemini_client(api_key).models.generate_content(
        model="gemini-3.5-flash-lite", contents="Produtos:\n" + "\n".join(f"{i + 1}. {p}" for i, p in enumerate(prods_norm)),
        config=types.GenerateContentConfig(
            system_instruction=f"Classificador de produtos no Brasil. Retorne 'categorias' na mesma ordem usando APENAS: {', '.join(LISTA_CATEGORIAS)}.",
            response_mime_type="application/json",
            response_schema={"type": "OBJECT", "properties": {"categorias": {"type": "ARRAY", "items": {"type": "STRING"}}}, "required": ["categorias"]},
        ),
    )
    cats = json.loads(resp.text).get("categorias", [])
    return [next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in (normalizar_texto(cats[i]) if i < len(cats) else "")), None) or identificar_categoria_local(p) for i, p in enumerate(prods_norm)]


def identificar_categoria(produto, api_key):
    if not api_key:
        return identificar_categoria_local(produto)
    try:
        return classificar_com_ia(normalizar_texto(produto), api_key)
    except Exception as erro:
        st.warning(f"API indisponível ({erro}). Usando regra local.")
        return identificar_categoria_local(produto)


def identificar_categorias_em_lote(produtos, api_key):
    if not produtos:
        return []
    if len(produtos) == 1:
        return [identificar_categoria(produtos[0], api_key)]
    if not api_key:
        return [identificar_categoria_local(p) for p in produtos]
    try:
        return classificar_lote_com_ia(tuple(normalizar_texto(p) for p in produtos), api_key)
    except Exception as erro:
        st.warning(f"API indisponível ({erro}). Usando regra local.")
        return [identificar_categoria_local(p) for p in produtos]


def reconhecer_produto_por_voz(audio_bytes, api_key, mime_type="audio/wav"):
    from google.genai import types
    schema = {"type": "OBJECT", "properties": {k: {"type": t} for k, t in [("transcricao", "STRING"), ("produto", "STRING"), ("categoria", "STRING"), ("quantidade", "INTEGER"), ("preco_unitario", "NUMBER"), ("supermercado", "STRING")]}, "required": ["transcricao", "produto", "categoria", "quantidade", "preco_unitario", "supermercado"]}
    prompt = f"Extraia do áudio de compra no Brasil: transcricao, produto, categoria (uma de: {', '.join(LISTA_CATEGORIAS)}), quantidade (1 padrão), preco_unitario (0 padrão) e supermercado ('' padrão)."
    resp = obter_gemini_client(api_key).models.generate_content(model="gemini-3.5-flash-lite", contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type), prompt], config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema))
    d = json.loads(resp.text)
    cat_n = normalizar_texto(d.get("categoria", ""))
    return {"transcricao": str(d.get("transcricao", "")).strip(), "produto": str(d.get("produto", "")).strip(), "categoria": next((c for c in LISTA_CATEGORIAS if normalizar_texto(c) in cat_n), "Outros"), "quantidade": max(1, int(d.get("quantidade") or 1)), "preco_unitario": max(0.0, float(d.get("preco_unitario") or 0.0)), "supermercado": str(d.get("supermercado", "")).strip()}


# --- Persistência CSV ---
def _ler_csv_seguro(caminho, colunas, cols_num):
    if not (os.path.exists(caminho) and os.path.getsize(caminho) > 0):
        return pd.DataFrame(columns=colunas)
    df, alt_cols = pd.read_csv(caminho), False
    for c in colunas:
        if c not in df.columns:
            alt_cols, df[c] = True, (0.0 if c in cols_num else "")
    df = df[colunas]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    if alt_cols:
        df.to_csv(caminho, index=False)
    return df


@st.cache_data(show_spinner=False)
def carregar_dados(usuario):
    return _ler_csv_seguro(obter_arquivo_usuario(usuario, "compras.csv"), COLUNAS, ["Quantidade", "Preço Unitário", "Total"])


@st.cache_data(show_spinner=False)
def obter_compras_com_datas(usuario):
    df = carregar_dados(usuario).copy()
    if df.empty:
        return df, pd.DataFrame(columns=COLUNAS)
    df["Data_dt"] = pd.to_datetime(df["Data"], errors="coerce")
    df_v = df.dropna(subset=["Data_dt"]).copy()
    if not df_v.empty:
        df_v["Mês"] = df_v["Data_dt"].dt.strftime("%Y-%m")
    return df, df_v


@st.cache_data(show_spinner=False)
def obter_gasto_mes_atual(usuario, mes_ref):
    _, df_v = obter_compras_com_datas(usuario)
    return 0.0 if df_v.empty else float(df_v.loc[df_v["Mês"] == mes_ref, "Total"].sum())


def limpar_cache_compras():
    carregar_dados.clear()
    obter_compras_com_datas.clear()
    obter_gasto_mes_atual.clear()


def salvar_compra_usuario(usuario, nova_df):
    pd.concat([carregar_dados(usuario), nova_df], ignore_index=True).to_csv(obter_arquivo_usuario(usuario, "compras.csv"), index=False)
    limpar_cache_compras()


@st.cache_data(show_spinner=False)
def carregar_comunidade():
    return _ler_csv_seguro(ARQUIVO_COMUNIDADE, COLUNAS_COMUNIDADE, ["Preço Unitário"])


@st.cache_data(show_spinner=False)
def carregar_comunidade_ordenada():
    df = carregar_comunidade().copy()
    if df.empty:
        return df
    df["Data_dt"] = pd.to_datetime(df["Data"], errors="coerce")
    return df.sort_values(by=["Preço Unitário", "Data_dt"], ascending=[True, False]).reset_index(drop=True)


def salvar_preco_comunidade(nova_df):
    pd.concat([carregar_comunidade(), nova_df], ignore_index=True).to_csv(ARQUIVO_COMUNIDADE, index=False)
    carregar_comunidade.clear()
    carregar_comunidade_ordenada.clear()


@st.cache_data(show_spinner=False)
def carregar_pre_lista(usuario):
    caminho = obter_arquivo_usuario(usuario, "pre_lista.csv")
    if not (os.path.exists(caminho) and os.path.getsize(caminho) > 0):
        return pd.DataFrame(columns=COLUNAS_PRE_LISTA)
    df = pd.read_csv(caminho)
    for col in COLUNAS_PRE_LISTA:
        if col not in df.columns:
            df[col] = 1 if col == "Quantidade" else (False if col == "Comprado" else ([secrets.token_hex(4) for _ in range(len(df))] if col == "ID" else ""))
    df = df[COLUNAS_PRE_LISTA]
    df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(1).astype(int)
    df["Comprado"] = df["Comprado"].map(lambda v: str(v).strip().lower() in ("true", "1", "sim"))
    df["ID"] = df["ID"].astype(str)
    return df


def salvar_pre_lista(df_pre, usuario):
    df_pre[COLUNAS_PRE_LISTA].to_csv(obter_arquivo_usuario(usuario, "pre_lista.csv"), index=False)
    carregar_pre_lista.clear()


def adicionar_itens_pre_lista(texto, qtd, api_key, usuario):
    itens = [i.strip() for i in texto.split(",") if i.strip()]
    if not itens:
        return 0
    novas = [{"ID": secrets.token_hex(4), "Produto": p, "Quantidade": max(1, int(qtd)), "Categoria": cat, "Comprado": False} for p, cat in zip(itens, identificar_categorias_em_lote(itens, api_key))]
    salvar_pre_lista(pd.concat([carregar_pre_lista(usuario), pd.DataFrame(novas, columns=COLUNAS_PRE_LISTA)], ignore_index=True), usuario)
    return len(novas)


# --- Componentes de UI ---
def renderizar_topo_nubank():
    p_nome = nome_usuario.strip().split()[0] if nome_usuario.strip() else usuario_atual
    sub_reg = f"📍 {gps_regiao}" if gps_regiao else "Sua lista inteligente e menor preço"
    no_perfil = st.session_state["pagina_atual"] == PAGINA_PERFIL

    with st.container(key="topo_nubank"):
        c_user, c_btn = st.columns([5, 1])
        c_user.markdown(
            f'<div class="listai-nu-user">{avatar_html(nome_usuario, usuario_atual, 52)}'
            f'<div class="listai-nu-texts"><div class="listai-nu-brand">Listaí • Beta Gratuito</div>'
            f'<div class="listai-nu-hello">Olá, {html.escape(p_nome)}</div>'
            f'<div class="listai-nu-sub">{html.escape(sub_reg)}</div></div></div>',
            unsafe_allow_html=True,
        )
        with c_btn:
            if no_perfil and st.button("← Voltar", key="nu_btn_voltar"):
                st.session_state.update({"pagina_atual": st.session_state.get("pagina_anterior", PAGINAS[0]), "rolar_topo": True})
                st.rerun()
            elif not no_perfil and st.button("👤 Perfil", key="nu_btn_perfil"):
                st.session_state.update({"pagina_anterior": st.session_state["pagina_atual"], "pagina_atual": PAGINA_PERFIL, "rolar_topo": True})
                st.rerun()


def renderizar_barra_inferior():
    with st.container(key="barra_inferior"):
        for idx, (col, (ico, txt), pag) in enumerate(zip(st.columns(len(NAV_ITENS), gap="small"), NAV_ITENS, PAGINAS)):
            ativo = st.session_state["pagina_atual"] == pag
            if col.button(f"{ico}  \n{txt}", key=f"bottom_nav_{idx}", type="primary" if ativo else "secondary", use_container_width=True) and not ativo:
                st.session_state.update({"pagina_atual": pag, "rolar_topo": True})
                st.rerun()


def renderizar_config_orcamento(usuario, pref):
    orc = carregar_orcamento_mensal(usuario)
    with st.form(f"form_orc_{pref}", border=False):
        novo_lim = st.number_input("Limite de compras no mês (R$)", min_value=0.0, value=float(orc["limite"]), step=50.0, format="%.2f", help="Deixe R$ 0,00 para desativar.", key=f"num_lim_{pref}")
        bloq = st.checkbox("Bloquear novas compras se ultrapassar o limite", value=bool(orc["bloquear"]), key=f"chk_bloq_{pref}")
        if st.form_submit_button("💾 Salvar limite", use_container_width=True):
            salvar_orcamento_mensal(novo_lim, bloq, usuario)
            st.session_state["msg_sucesso"] = "Limite mensal desativado." if novo_lim <= 0 else f"Limite mensal salvo: **{formatar_reais(novo_lim)}**."
            st.rerun()


def renderizar_painel_limite_mensal(usuario, pref, expandir_config=False, gasto_mes=None):
    limite = float(carregar_orcamento_mensal(usuario)["limite"])
    if limite <= 0:
        with st.expander("🎯 Definir limite de gasto mensal (opcional)", expanded=expandir_config):
            renderizar_config_orcamento(usuario, pref)
        return
    gasto = obter_gasto_mes_atual(usuario, date.today().strftime("%Y-%m")) if gasto_mes is None else gasto_mes
    pct, rest = gasto / limite, limite - gasto
    with st.container(border=True):
        if rest < 0:
            st.error(f"🚨 **Limite mensal ultrapassado!** Gasto: **{formatar_reais(gasto)}** de **{formatar_reais(limite)}** (excedeu **{formatar_reais(abs(rest))}**).")
        elif pct >= 0.80:
            st.warning(f"⚠️ **Atenção ao limite ({int(pct * 100)}%):** **{formatar_reais(gasto)}** de **{formatar_reais(limite)}** · Resta **{formatar_reais(rest)}**.")
        else:
            st.success(f"🎯 **Limite mensal ({int(pct * 100)}%):** **{formatar_reais(gasto)}** de **{formatar_reais(limite)}** · Resta **{formatar_reais(rest)}**.")
        st.progress(min(pct, 1.0))
        with st.expander("⚙️ Alterar limite mensal", expanded=expandir_config):
            renderizar_config_orcamento(usuario, pref)


def renderizar_graficos_compras(df, df_validos, limite_mensal=0.0):
    if df_validos.empty:
        st.info("Adicione compras com data para visualizar os gráficos.")
        return
    import altair as alt

    visao = st.radio("Agrupar evolução mensal por:", ["Total do Mês", "Por Categoria", "Por Supermercado"], horizontal=True)
    paleta = ["#064E3B", "#15803D", "#16A34A", "#22C55E", "#10B981", "#0D9488", "#4ADE80", "#86EFAC"]
    col_g, col_c = st.columns([3, 2])

    with col_g:
        df_v = df_validos.copy()
        meses_ord = sorted(df_v["Mês"].unique())
        mapa_lbl = {m: f"{m[5:]}/{m[:4]}" for m in meses_ord}
        ord_lbls, df_v["Mês_Label"] = [mapa_lbl[m] for m in meses_ord], df_v["Mês"].map(mapa_lbl)

        if visao in ("Por Categoria", "Por Supermercado"):
            col_cor = "Categoria" if visao == "Por Categoria" else "Mercado"
            if col_cor == "Mercado":
                df_v["Mercado"] = df_v["Supermercado"].replace("", "Não informado").fillna("Não informado")
            g = df_v.groupby(["Mês", "Mês_Label", col_cor], as_index=False)["Total"].sum()
            g["Valor_fmt"] = g["Total"].apply(formatar_reais)
            chart_m = alt.Chart(g).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X("Mês_Label:N", sort=ord_lbls, title=None, axis=alt.Axis(labelAngle=0, labelColor="#132A1E")),
                y=alt.Y("Total:Q", title="Gasto (R$)", axis=alt.Axis(labelColor="#132A1E", titleColor="#064E3B")),
                color=alt.Color(f"{col_cor}:N", scale=alt.Scale(range=paleta), legend=alt.Legend(orient="bottom", columns=3, title=None, labelColor="#132A1E")),
                tooltip=[alt.Tooltip("Mês_Label:N", title="Mês"), alt.Tooltip(f"{col_cor}:N", title=col_cor), alt.Tooltip("Valor_fmt:N", title="Total")],
            ).properties(height=320, title=f"Gastos Mensais ({visao})")
        else:
            g = df_v.groupby(["Mês", "Mês_Label"], as_index=False)["Total"].sum()
            g["Valor_fmt"] = g["Total"].apply(formatar_reais)
            teto_y = max(g["Total"].max() * 1.18, limite_mensal * 1.12 if limite_mensal > 0 else 0.0, 10.0)
            barras = alt.Chart(g).mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7, color="#16A34A", size=38).encode(
                x=alt.X("Mês_Label:N", sort=ord_lbls, title=None, axis=alt.Axis(labelAngle=0, labelColor="#132A1E")),
                y=alt.Y("Total:Q", title="Gasto (R$)", scale=alt.Scale(domain=[0, teto_y]), axis=alt.Axis(labelColor="#132A1E", titleColor="#064E3B")),
                tooltip=[alt.Tooltip("Mês_Label:N", title="Mês"), alt.Tooltip("Valor_fmt:N", title="Total Gasto")],
            )
            camadas, tit = [barras, barras.mark_text(align="center", baseline="bottom", dy=-5, fontWeight="bold", color="#064E3B").encode(text="Valor_fmt:N")], []
            if len(g) >= 2:
                media = g["Total"].mean()
                camadas.append(alt.Chart(pd.DataFrame({"Media": [media]})).mark_rule(strokeDash=[5, 4], color="#064E3B", size=2).encode(y="Media:Q"))
                tit.append(f"média: {formatar_reais(media)}")
            if limite_mensal > 0:
                camadas.append(alt.Chart(pd.DataFrame({"Limite": [limite_mensal]})).mark_rule(strokeDash=[3, 3], color="#DC2626", size=2).encode(y="Limite:Q"))
                tit.append(f"limite: {formatar_reais(limite_mensal)}")
            chart_m = alt.layer(*camadas).properties(height=320, title=f"Evolução Mensal ({' • '.join(tit)})" if tit else "Evolução Mensal")
        st.altair_chart(chart_m.configure(background="#FFFFFF"), use_container_width=True)

    with col_c:
        rc = df.groupby("Categoria", as_index=False)["Total"].sum().sort_values("Total", ascending=False)
        rc["Label"] = rc.apply(lambda r: f"{formatar_reais(r['Total'])} ({(r['Total'] / max(rc['Total'].sum(), 0.01)) * 100:.0f}%)", axis=1)
        bc = alt.Chart(rc).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
            y=alt.Y("Categoria:N", sort="-x", title=None, axis=alt.Axis(labelColor="#132A1E")),
            x=alt.X("Total:Q", title=None, axis=None, scale=alt.Scale(domain=[0, max(rc["Total"].max() * 1.48, 10)])),
            color=alt.Color("Total:Q", scale=alt.Scale(range=["#4ADE80", "#16A34A", "#064E3B"]), legend=None),
            tooltip=[alt.Tooltip("Categoria:N", title="Categoria"), alt.Tooltip("Label:N", title="Gasto")],
        )
        st.altair_chart((bc + bc.mark_text(align="left", baseline="middle", dx=6, fontSize=12, fontWeight="bold", color="#064E3B").encode(text="Label:N")).properties(height=320, title="Onde você gastou mais").configure(background="#FFFFFF"), use_container_width=True)


def _fmt_qtd(v):
    return int(v) if float(v).is_integer() else v


def _fmt_dt(dt):
    return dt.strftime("%d/%m/%Y") if pd.notna(dt) else "Sem data"


def renderizar_grupos_historico(df_exib, col_grupo, total_geral, modo="categoria"):
    df_g = df_exib.copy()
    resumo = df_g.groupby(col_grupo, as_index=False)["Total"].sum().sort_values("Total", ascending=False)
    total_base, abrir_todos = max(total_geral, 0.01), len(resumo) <= 4

    for idx, row_g in enumerate(resumo.itertuples(index=False)):
        nome_grp, total_grp = getattr(row_g, col_grupo), float(row_g.Total)
        pct = min(100.0, (total_grp / total_base) * 100)
        sub = df_g[df_g[col_grupo] == nome_grp].sort_values(
            by=("Data_dt" if modo == "categoria" else ["Categoria", "Data_dt"]),
            ascending=(False if modo == "categoria" else [True, False]),
            na_position="last",
        )
        ico = ICONES_CATEGORIA.get(nome_grp, "📦") if modo == "categoria" else "🏪"
        qtd = len(sub)
        plural = "item" if qtd == 1 else "itens"

        st.markdown(
            f'<div class="listai-hist-card"><div class="listai-hist-head">'
            f'<div class="listai-hist-title">{ico} {html.escape(str(nome_grp))} '
            f'<span class="listai-hist-badge">{qtd} {plural} • {pct:.0f}%</span></div>'
            f'<div class="listai-hist-total">{formatar_reais(total_grp)}</div></div>'
            f'<div class="listai-hist-track"><div class="listai-hist-fill" style="width:{pct:.1f}%"></div></div></div>',
            unsafe_allow_html=True,
        )
        with st.expander(f"Ver produtos de {nome_grp} ({qtd})", expanded=(abrir_todos or idx == 0)):
            itens = []
            for r in sub.to_dict("records"):
                dt_txt = _fmt_dt(r.get("Data_dt"))
                merc_str = html.escape(str(r.get("Supermercado") or "Não informado"))
                cat_str = str(r.get("Categoria") or "Outros")
                meta = f"🏪 {merc_str} · 📅 {dt_txt}" if modo == "categoria" else f"{ICONES_CATEGORIA.get(cat_str, '📦')} {html.escape(cat_str)} · 📅 {dt_txt}"
                prod_esc = html.escape(str(r.get("Produto", "")))
                qtd_fmt = _fmt_qtd(r.get("Quantidade", 1))
                tot_fmt = formatar_reais(float(r.get("Total", 0.0)))
                unit_fmt = formatar_reais(float(r.get("Preço Unitário", 0.0)))
                itens.append(
                    f'<div class="listai-hist-item"><div><div class="listai-hist-prod">{prod_esc} <small>(x{qtd_fmt})</small></div>'
                    f'<div class="listai-hist-meta">{meta}</div></div>'
                    f'<div class="listai-hist-right"><div class="listai-hist-val">{tot_fmt}</div>'
                    f'<div class="listai-hist-unit">{unit_fmt}/un</div></div></div>'
                )
            st.markdown("".join(itens), unsafe_allow_html=True)


def _montar_row_feed(r, mostrar_data=False):
    cat = str(r.get("Categoria") or "Outros")
    merc_esc = html.escape(str(r.get("Supermercado") or "Não informado"))
    tags = f'<span class="listai-feed-tag">🏪 {merc_esc}</span><span class="listai-feed-tag listai-feed-tag-cat">{html.escape(cat)}</span>'
    if mostrar_data:
        tags += f'<span class="listai-feed-tag">📅 {_fmt_dt(r.get("Data_dt"))}</span>'
    prod_esc = html.escape(str(r.get("Produto", "")))
    qtd_fmt = _fmt_qtd(r.get("Quantidade", 1))
    tot_fmt = formatar_reais(float(r.get("Total", 0.0)))
    unit_fmt = formatar_reais(float(r.get("Preço Unitário", 0.0)))
    return (
        f'<div class="listai-feed-row"><div class="listai-feed-left"><div class="listai-feed-ico">{ICONES_CATEGORIA.get(cat, "📦")}</div>'
        f'<div class="listai-feed-info"><div class="listai-feed-name">{prod_esc} <small>(x{qtd_fmt})</small></div>'
        f'<div class="listai-feed-tags">{tags}</div></div></div>'
        f'<div class="listai-hist-right"><div class="listai-hist-val">{tot_fmt}</div>'
        f'<div class="listai-hist-unit">{unit_fmt}/un</div></div></div>'
    )


def renderizar_lista_geral_historico(df_tab, agrupar_por_data=True):
    regs = df_tab.to_dict("records")
    if not agrupar_por_data:
        rows_html = "".join(_montar_row_feed(r, True) for r in regs)
        st.markdown(f'<div class="listai-feed-box">{rows_html}</div>', unsafe_allow_html=True)
        return
    blocos, mapa, hoje = [], {}, date.today().strftime("%d/%m/%Y")
    for r in regs:
        dia = _fmt_dt(r.get("Data_dt"))
        if dia not in mapa:
            mapa[dia] = {"dia": dia, "total": 0.0, "itens": []}
            blocos.append(mapa[dia])
        mapa[dia]["total"] += float(r.get("Total", 0.0))
        mapa[dia]["itens"].append(r)

    partes = []
    for g in blocos:
        dia_val = g["dia"]
        dia_lbl = f"Hoje ({dia_val})" if dia_val == hoje else dia_val
        tot_dia = formatar_reais(g["total"])
        rows_html = "".join(_montar_row_feed(r, False) for r in g["itens"])
        partes.append(f'<div class="listai-feed-day"><span>📅 {html.escape(dia_lbl)}</span><span>Total: {tot_dia}</span></div><div class="listai-feed-box">{rows_html}</div>')
    st.markdown("".join(partes), unsafe_allow_html=True)


def exibir_tabela_e_mapa_regiao(lista_m, msg_ok):
    df_m = pd.DataFrame(lista_m)
    st.success(msg_ok)
    c1, c2 = st.columns([3, 2])
    c1.dataframe(df_m[["Supermercado", "Tipo", "Endereço", "Distância (m)"]], hide_index=True, use_container_width=True)
    c2.map(df_m, latitude="lat", longitude="lon")


def exibir_rodape_anuncio():
    ad = ANUNCIOS[st.session_state.setdefault("anuncio_idx", random.randrange(len(ANUNCIOS)))]
    st.divider()
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        c1.markdown(f'<span class="listai-ad-badge">OFERTA PARCEIRA • PUBLICIDADE</span><br><strong>{ad["titulo"]}</strong> — {ad["descricao"]}', unsafe_allow_html=True)
        c2.link_button(ad["texto_botao"], ad["url"], use_container_width=True)


# --- Páginas ---
def pagina_compra():
    mes_hoje = date.today().strftime("%Y-%m")
    gasto_mes = obter_gasto_mes_atual(usuario_atual, mes_hoje)
    df_pre = carregar_pre_lista(usuario_atual)
    pend = int((~df_pre["Comprado"]).sum()) if not df_pre.empty else 0

    k1, k2 = st.columns(2)
    k1.metric("📅 Gasto neste mês", formatar_reais(gasto_mes))
    k2.metric("📝 Pendentes na lista", f"{pend} item(ns)" if pend else "Lista em dia ✅")
    renderizar_painel_limite_mensal(usuario_atual, "compra", gasto_mes=gasto_mes)

    mercados_reg = carregar_mercados()
    regioes = sorted(mercados_reg.keys())
    if gps_regiao and gps_regiao not in regioes:
        regioes = [gps_regiao] + regioes
    op_reg = regioes + ["➕ Nova região..."]

    if (rp := st.session_state.pop("regiao_para_selecionar", None)) in op_reg:
        st.session_state["sel_reg_compra"] = rp
    if st.session_state.get("sel_reg_compra") not in op_reg:
        st.session_state["sel_reg_compra"] = gps_regiao if gps_regiao in op_reg else op_reg[0]

    reg_sel = st.session_state["sel_reg_compra"]
    reg_ativa = st.session_state.get("input_nova_regiao", "").strip() if reg_sel == "➕ Nova região..." else reg_sel
    versao, dist_gps = st.session_state["form_versao"], dict(gps_mercados)

    with st.container(border=True):
        st.markdown("#### 🛒 Adicionar Produto")
        lista_m = [st.session_state["valor_supermercado"].strip()] if st.session_state.get("valor_supermercado", "").strip() else []
        for m in ([n for n, _ in gps_mercados] if reg_ativa == gps_regiao else []) + list(mercados_reg.get(reg_ativa, [])):
            if m not in lista_m:
                lista_m.append(m)
        op_merc = lista_m + ["➕ Novo supermercado..."]

        if (mp := st.session_state.pop("merc_para_selecionar", None)) in op_merc:
            st.session_state["sel_merc_compra"] = mp
        if st.session_state.get("sel_merc_compra") not in op_merc:
            st.session_state["sel_merc_compra"] = op_merc[0]

        merc_esc = st.selectbox("🏪 Supermercado", op_merc, key="sel_merc_compra", format_func=(lambda m: f"{m} ({dist_gps[m]} m)" if reg_ativa == gps_regiao and dist_gps.get(m) is not None else m))
        merc_final = st.text_input("Nome do Supermercado", placeholder="Ex: Atacadão, Mercado Central").strip() if merc_esc == "➕ Novo supermercado..." else merc_esc

        # Botão de Fala Estilo WhatsApp
        with st.container(key="zap_voz"):
            c_lbl, c_aud = st.columns([1.6, 1.4], vertical_alignment="center")
            c_lbl.markdown('<div class="listai-zap-hint"><strong>🎤 Falar compra</strong><small>Ex: "2 cafés de 18 reais"</small></div>', unsafe_allow_html=True)
            if (audio := c_aud.audio_input("Falar", label_visibility="collapsed", key=f"audio_zap_{versao}")) is not None:
                ab = audio.getvalue()
                ah = hashlib.sha256(ab).hexdigest()
                if ah != st.session_state.get("ultimo_audio_hash"):
                    st.session_state["ultimo_audio_hash"] = ah
                    if not api_key:
                        st.warning("Configure sua Chave da API Gemini no seu **Perfil → Inteligência Artificial**.")
                    else:
                        with st.spinner("Ouvindo e preenchendo..."):
                            try:
                                dv = reconhecer_produto_por_voz(ab, api_key, mime_type=getattr(audio, "type", None) or "audio/wav")
                                if not dv["produto"]:
                                    st.warning("Não entendi o produto. Tente falar mais perto do microfone.")
                                else:
                                    st.session_state.update({"valor_produto": dv["produto"], "valor_quantidade": dv["quantidade"], "valor_preco": dv["preco_unitario"] or 1.00, "aviso_voz": dv, "form_versao": versao + 1})
                                    if dv["supermercado"]:
                                        st.session_state.update({"valor_supermercado": dv["supermercado"], "merc_para_selecionar": dv["supermercado"]})
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erro no áudio: {e}")

        if aviso := st.session_state.get("aviso_voz"):
            txt_v = f"🎤 **Ouvi:** *\"{aviso['transcricao']}\"* • Categoria: **{aviso['categoria']}**"
            txt_v += f" • Mercado: **{aviso['supermercado']}**" if aviso.get("supermercado") else ""
            txt_v += " *(ajuste o preço abaixo)*" if aviso["preco_unitario"] <= 0 else ""
            st.info(txt_v)

        with st.form("form_compras", clear_on_submit=False, border=False):
            c1, c2, c3 = st.columns([3, 1, 1.3])
            prod = c1.text_input("Produto", value=st.session_state["valor_produto"], placeholder="Ex: Arroz 5kg, Sabão Omo, Café...", key=f"input_produto_{versao}")
            qtd = c2.number_input("Qtd", min_value=1, value=int(st.session_state["valor_quantidade"]), step=1, key=f"input_qtd_{versao}")
            preco = c3.number_input("Preço (R$)", min_value=0.01, value=float(st.session_state["valor_preco"]), step=0.01, format="%.2f", key=f"input_preco_{versao}")
            enviado = st.form_submit_button("✅ Adicionar", type="primary", use_container_width=True)
            with st.expander(f"📅 Data ({date.today().strftime('%d/%m/%Y')}) e compartilhamento", expanded=False):
                cd1, cd2 = st.columns(2, vertical_alignment="center")
                data_c = cd1.date_input("Data da compra", value=date.today(), format="DD/MM/YYYY")
                comp = cd2.checkbox("📢 Compartilhar preço com a região", value=True)

        st.markdown(f'<div class="listai-mini-status">📍 Região ativa: <strong>{html.escape(reg_ativa or "Definir abaixo")}</strong></div>', unsafe_allow_html=True)
        with st.expander("📍 Trocar ou criar região", expanded=(reg_sel == "➕ Nova região...")):
            reg_esc = st.selectbox("📍 Região", op_reg, key="sel_reg_compra")
            reg_final = st.text_input("Nome da nova região", placeholder="Ex: Campinas - Centro", key="input_nova_regiao").strip() if reg_esc == "➕ Nova região..." else reg_esc

        if enviado:
            prod = prod.strip()
            if not prod:
                st.warning("Digite ou fale o nome do produto.")
            elif not reg_final or not merc_final:
                st.warning("Informe a Região e o Supermercado.")
            else:
                v_tot, orc = float(qtd) * float(preco), carregar_orcamento_mensal(usuario_atual)
                lim, mes_c = float(orc["limite"]), data_c.strftime("%Y-%m")
                novo_tot = gasto_mes + (v_tot if mes_c == mes_hoje else 0.0)
                if lim > 0 and orc["bloquear"] and mes_c == mes_hoje and novo_tot > lim:
                    st.error(f"🚫 Compra bloqueada pelo seu limite mensal de **{formatar_reais(lim)}**! Essa compra elevaria o mês para **{formatar_reais(novo_tot)}**.")
                else:
                    av = st.session_state.get("aviso_voz")
                    cat = av["categoria"] if (av and normalizar_texto(prod) == normalizar_texto(av.get("produto", "")) and av.get("categoria") in LISTA_CATEGORIAS) else identificar_categoria(prod, api_key)
                    registrar_varios_mercados(reg_final, [merc_final])
                    salvar_compra_usuario(usuario_atual, pd.DataFrame([[data_c.isoformat(), reg_final, merc_final, prod, cat, qtd, preco, v_tot]], columns=COLUNAS))
                    extra = ""
                    if comp:
                        salvar_preco_comunidade(pd.DataFrame([[data_c.isoformat(), reg_final, merc_final, prod, cat, preco, nome_usuario]], columns=COLUNAS_COMUNIDADE))
                        extra = " Preço compartilhado!"
                    if lim > 0 and mes_c == mes_hoje and novo_tot > lim:
                        st.session_state["msg_limite_alerta"] = f"⚠️ Atenção: seus gastos no mês chegaram a **{formatar_reais(novo_tot)}**, ultrapassando o limite de **{formatar_reais(lim)}**!"
                    st.session_state.update({"msg_sucesso": f"'{prod}' adicionado em **{merc_final}** ({cat}).{extra}", "valor_produto": "", "valor_quantidade": 1, "valor_preco": 1.00, "valor_supermercado": "", "regiao_para_selecionar": reg_final, "merc_para_selecionar": merc_final, "form_versao": versao + 1})
                    st.session_state.pop("aviso_voz", None)
                    st.rerun()


def pagina_pre_lista():
    st.subheader("📝 Pré-Lista de Compras (Checklist)")
    st.caption("Anote antes de ir ao mercado e vá marcando cada item quando encontrar na prateleira.")
    with st.container(border=True):
        with st.form("form_pre_lista", clear_on_submit=True, border=False):
            c1, c2, c3 = st.columns([4, 1, 2], vertical_alignment="bottom")
            txt = c1.text_input("O que precisa comprar?", placeholder="Ex: Arroz 5kg  (ou vários: Arroz, Feijão, Café, Leite)")
            qtd_p = c2.number_input("Qtd", min_value=1, value=1, step=1)
            if c3.form_submit_button("➕ Adicionar à Lista", type="primary", use_container_width=True):
                if not txt.strip():
                    st.warning("Digite pelo menos um produto.")
                else:
                    st.session_state["msg_sucesso"] = f"{adicionar_itens_pre_lista(txt, qtd_p, api_key, usuario_atual)} item(ns) adicionado(s) na pré-lista!"
                    st.rerun()
        df_sug, _ = obter_compras_com_datas(usuario_atual)
        if not df_sug.empty:
            with st.expander("⚡ Adicionar rápido dos itens que você mais compra"):
                esc = st.multiselect("Escolha os itens:", df_sug["Produto"].value_counts().head(8).index.tolist())
                if st.button("Adicionar selecionados na pré-lista", disabled=not esc):
                    adicionar_itens_pre_lista(", ".join(esc), 1, api_key, usuario_atual)
                    st.rerun()

    df_pre = carregar_pre_lista(usuario_atual).copy()
    if df_pre.empty:
        with st.container(border=True):
            st.info("Sua pré-lista está vazia! Adicione os itens acima antes de ir ao supermercado.")
        return

    tot, pegos = len(df_pre), int(df_pre["Comprado"].sum())
    st.progress(pegos / tot, text=f"✅ **{pegos} de {tot}** itens encontrados no supermercado ({int((pegos / tot) * 100)}%)")
    with st.container(border=True):
        alt_chk = False
        for idx, row in df_pre.sort_values(by="Comprado", ascending=True).iterrows():
            iid, nome_i, qtd_i, cat_i, pego = row["ID"], row["Produto"], int(row["Quantidade"]), row["Categoria"] or "Outros", bool(row["Comprado"])
            c_chk, c_lnc, c_del = st.columns([6, 2, 1])
            lbl = f"~~{nome_i} (x{qtd_i})~~ · *{cat_i}*" if pego else f"**{nome_i}** (x{qtd_i}) · *{cat_i}*"
            if (mk := c_chk.checkbox(lbl, value=pego, key=f"chk_pre_{iid}")) != pego:
                df_pre.loc[idx, "Comprado"], alt_chk = mk, True
            if c_lnc.button("💰 Lançar preço", key=f"btn_lancar_{iid}", use_container_width=True):
                df_pre.loc[idx, "Comprado"] = True
                salvar_pre_lista(df_pre, usuario_atual)
                st.session_state.pop("aviso_voz", None)
                st.session_state.update({"valor_produto": nome_i, "valor_quantidade": qtd_i, "form_versao": st.session_state["form_versao"] + 1, "pagina_atual": PAGINAS[0], "rolar_topo": True})
                st.rerun()
            if c_del.button("🗑️", key=f"btn_del_pre_{iid}", help="Remover item", use_container_width=True):
                salvar_pre_lista(df_pre.drop(index=idx), usuario_atual)
                st.rerun()
        if alt_chk:
            salvar_pre_lista(df_pre, usuario_atual)
            st.rerun()

    a1, a2 = st.columns(2)
    if a1.button("🧹 Limpar itens já marcados (✅)", disabled=(pegos == 0), use_container_width=True):
        salvar_pre_lista(df_pre[~df_pre["Comprado"]], usuario_atual)
        st.rerun()
    if a2.button("🗑️ Limpar toda a pré-lista", use_container_width=True):
        if os.path.exists(cp := obter_arquivo_usuario(usuario_atual, "pre_lista.csv")):
            os.remove(cp)
        carregar_pre_lista.clear()
        st.rerun()


def pagina_graficos():
    st.subheader("📊 Gráficos e Análise de Gastos")
    df_c, df_v = obter_compras_com_datas(usuario_atual)
    mes_hoje = date.today().strftime("%Y-%m")
    gasto, media, delta = 0.0, 0.0, None
    if not df_v.empty:
        tot_m = df_v.groupby("Mês")["Total"].sum()
        gasto, media = float(tot_m.get(mes_hoje, 0.0)), float(tot_m.mean())
        if (ant := [m for m in sorted(tot_m.index) if m < mes_hoje]) and gasto > 0:
            delta = f"{formatar_delta_reais(gasto - float(tot_m[ant[-1]]))} vs {ant[-1][5:]}/{ant[-1][:4]}"

    renderizar_painel_limite_mensal(usuario_atual, "graficos", gasto_mes=gasto)
    if df_c.empty:
        with st.container(border=True):
            st.info("Você ainda não tem compras registradas. Adicione sua primeira compra em **🛒 Compra**!")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Total Geral", formatar_reais(df_c["Total"].sum()))
    m2.metric("📅 Mês Atual", formatar_reais(gasto), delta=delta, delta_color="inverse")
    m3.metric("📈 Média Mensal", formatar_reais(media))
    m4.metric("🛍️ Itens", len(df_c))
    st.write("")
    with st.container(border=True):
        renderizar_graficos_compras(df_c, df_v, limite_mensal=float(carregar_orcamento_mensal(usuario_atual)["limite"]))


def pagina_historico():
    st.subheader("🧾 Histórico de Compras")
    df_c, df_v = obter_compras_com_datas(usuario_atual)
    if df_c.empty:
        with st.container(border=True):
            st.info("Nenhuma compra no histórico ainda. Cadastre itens em **🛒 Compra**!")
        return

    with st.container(border=True):
        f1, f2, f3, f4 = st.columns(4)
        df_e = df_c.copy()
        df_e["Supermercado"] = df_e["Supermercado"].replace("", "Não informado").fillna("Não informado")
        df_e["Categoria"] = df_e["Categoria"].replace("", "Outros").fillna("Outros")
        mes_s = f1.selectbox("📅 Mês", ["Todos"] + (sorted(df_v["Mês"].unique(), reverse=True) if not df_v.empty else []))
        merc_s = f2.selectbox("🏪 Supermercado", ["Todos"] + sorted(df_e["Supermercado"].unique()))
        cat_s = f3.selectbox("🏷️ Categoria", ["Todas"] + sorted(df_e["Categoria"].unique()))
        busca = f4.text_input("🔎 Buscar produto", placeholder="Ex: arroz, sabão...").strip()

        if mes_s != "Todos":
            df_e = df_e[df_e["Data_dt"].dt.strftime("%Y-%m") == mes_s]
        if merc_s != "Todos":
            df_e = df_e[df_e["Supermercado"] == merc_s]
        if cat_s != "Todas":
            df_e = df_e[df_e["Categoria"] == cat_s]
        if busca:
            th = normalizar_texto(busca)
            df_e = df_e[[th in normalizar_texto(p) for p in df_e["Produto"]]]

    if df_e.empty:
        st.warning("Nenhuma compra encontrada com os filtros selecionados.")
    else:
        tot_f = float(df_e["Total"].sum())
        hm1, hm2, hm3 = st.columns(3)
        hm1.metric("💰 Total Filtrado", formatar_reais(tot_f))
        hm2.metric("🛍️ Produtos Comprados", f"{len(df_e)} itens")
        hm3.metric("🧭 Divisão", f"{df_e['Categoria'].nunique()} categorias • {df_e['Supermercado'].nunique()} mercados")

        aba_cat, aba_merc, aba_lst = st.tabs(["🏷️ Por Categoria", "🏪 Por Supermercado", "📋 Lista Geral"])
        with aba_cat:
            renderizar_grupos_historico(df_e, "Categoria", tot_f, modo="categoria")
        with aba_merc:
            renderizar_grupos_historico(df_e, "Supermercado", tot_f, modo="supermercado")
        with aba_lst:
            co, ce = st.columns([3, 1.4], vertical_alignment="bottom")
            ordem = co.radio("Ordenar lista por:", ["Mais recentes", "Maior valor", "Produto (A–Z)"], horizontal=True, key="hist_ordem_lista")
            df_t = df_e.sort_values(by="Data_dt", ascending=False, na_position="last") if ordem == "Mais recentes" else (df_e.sort_values(by="Total", ascending=False) if ordem == "Maior valor" else df_e.sort_values(by="Produto", key=lambda s: s.astype(str).str.lower()))
            ce.download_button("⬇️ Exportar CSV", data=df_t[COLUNAS].to_csv(index=False).encode("utf-8-sig"), file_name=f"listai_compras_{date.today().isoformat()}.csv", mime="text/csv", use_container_width=True)
            renderizar_lista_geral_historico(df_t, agrupar_por_data=(ordem == "Mais recentes"))

    with st.expander("🗑️ Excluir ou Limpar Compras"):
        cam = obter_arquivo_usuario(usuario_atual, "compras.csv")
        ops = {i: f"{r['Data'] or 'Sem data'} | {r['Supermercado'] or '-'} | {r['Produto']} | R$ {r['Total']:.2f}" for i, r in df_c.iterrows()}
        sels = st.multiselect("Excluir itens específicos:", list(ops.keys()), format_func=lambda i: ops[i])
        if st.button("Excluir selecionados", disabled=not sels):
            df_c.drop(index=sels)[COLUNAS].to_csv(cam, index=False)
            limpar_cache_compras()
            st.rerun()
        st.divider()
        if st.checkbox("Confirmo apagar TODAS as minhas compras") and st.button("🗑️ Limpar tudo", type="primary"):
            if os.path.exists(cam):
                os.remove(cam)
            limpar_cache_compras()
            st.rerun()


def pagina_precos():
    st.subheader("🏆 Comparar Preços")
    df_ord = carregar_comunidade_ordenada()
    if df_ord.empty:
        with st.container(border=True):
            st.info("Ainda não há preços compartilhados. Cadastre uma compra em **🛒 Compra**!")
        return

    with st.container(border=True):
        c1, c2 = st.columns([2, 1.3])
        busca = c1.text_input("🔎 Qual produto você procura?", placeholder="Ex: arroz, café, sabão omo...").strip()
        regs = ["Todas"] + sorted(r for r in df_ord["Região"].dropna().unique() if str(r).strip())
        reg_f = c2.selectbox("📍 Região", regs, index=regs.index(gps_regiao) if gps_regiao in regs else 0, key=f"f_com_{gps_regiao}")

    df_f = df_ord if reg_f == "Todas" else df_ord[df_ord["Região"] == reg_f]
    if busca:
        t = normalizar_texto(busca)
        df_f = df_f[[t in normalizar_texto(x) for x in df_f["Produto"]]]

    if df_f.empty:
        st.warning("Nenhum preço encontrado. Tente outro nome de produto ou selecione **Todas** as regiões.")
    else:
        m = df_f.iloc[0]
        menor_p, maior_p = float(m["Preço Unitário"]), float(df_f["Preço Unitário"].max())
        economia = max(0.0, maior_p - menor_p)
        eco_html = f'<span class="listai-eco-pill">Economia de até {formatar_reais(economia)}</span>' if economia > 0.01 else ""
        m_prod = html.escape(str(m["Produto"]))
        m_merc = html.escape(str(m["Supermercado"] or "Mercado"))
        m_reg = html.escape(str(m["Região"] or ""))

        st.markdown(
            f'<div class="listai-winner-card">'
            f'<div><h3>🏆 Melhor oferta: {m_prod}</h3><div>🏪 <strong>{m_merc}</strong> • {m_reg}</div>{eco_html}</div>'
            f'<div class="listai-winner-price">{formatar_reais(menor_p)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Ranking visual simples e leve (top 40)
        linhas = []
        medalhas = {0: "🥇", 1: "🥈", 2: "🥉"}
        for i, r in enumerate(df_f.head(40).to_dict("records")):
            p_unit = float(r.get("Preço Unitário", 0.0))
            diff = p_unit - menor_p
            badge_rank = medalhas.get(i, f"{i + 1}º")
            diff_html = '<div class="listai-diff-best">✓ Menor preço</div>' if diff <= 0.01 else f'<div class="listai-diff-up">+{formatar_reais(diff)}</div>'
            prod_r = html.escape(str(r.get("Produto", "")))
            merc_r = html.escape(str(r.get("Supermercado") or "Mercado"))
            reg_r = html.escape(str(r.get("Região") or "-"))
            dt_r = _fmt_dt(r.get("Data_dt"))
            linhas.append(
                f'<div class="listai-feed-row"><div class="listai-feed-left"><div class="listai-feed-ico">{badge_rank}</div>'
                f'<div class="listai-feed-info"><div class="listai-feed-name">{prod_r}</div>'
                f'<div class="listai-feed-tags"><span class="listai-feed-tag">🏪 {merc_r}</span>'
                f'<span class="listai-feed-tag listai-feed-tag-cat">{reg_r}</span>'
                f'<span class="listai-feed-tag">📅 {dt_r}</span></div></div></div>'
                f'<div class="listai-hist-right"><div class="listai-hist-val">{formatar_reais(p_unit)}</div>{diff_html}</div></div>'
            )
        st.markdown(f'<div class="listai-feed-box">{"".join(linhas)}</div>', unsafe_allow_html=True)

        zap = "\n".join(["🛒 *Melhores preços no Listaí:*", ""] + [f"• *{r['Produto']}*: R$ {r['Preço Unitário']:.2f} ({r['Supermercado']} - {r['Região']})" for r in df_f.head(5).to_dict("records")])
        st.link_button("📲 Enviar melhores preços no WhatsApp", f"https://wa.me/?text={urllib.parse.quote(zap)}", type="primary", use_container_width=True)
        with st.expander("👀 Ver mensagem antes de enviar"):
            st.code(zap, language=None)

    if usuario_atual in USUARIOS_ADMIN:
        with st.expander("👑 Admin — Limpar comunidade"):
            if st.button("Apagar preços compartilhados"):
                if os.path.exists(ARQUIVO_COMUNIDADE):
                    os.remove(ARQUIVO_COMUNIDADE)
                carregar_comunidade.clear()
                carregar_comunidade_ordenada.clear()
                st.rerun()


def pagina_mercados():
    st.subheader("🗺️ Supermercados na Região")
    raio = st.radio("Raio de busca:", [3, 5, 10], index=0, horizontal=True, format_func=lambda x: f"{x} km")
    with st.expander("📍 Ativar ou atualizar minha localização GPS", expanded=not bool(gps_coords)):
        st.caption("Toque no ícone abaixo e clique em **Permitir** no navegador:")
        processar_leitura_gps(streamlit_geolocation(), usuario_atual) if streamlit_geolocation else st.warning("Pacote `streamlit-geolocation` não instalado.")

    if gps_coords:
        if st.button("🔄 Buscar e cadastrar neste raio", type="primary", use_container_width=True):
            with st.spinner(f"Buscando em {raio} km..."):
                try:
                    nova = consultar_overpass_mercados(gps_coords[0], gps_coords[1], raio * 1000)
                    if nova:
                        registrar_varios_mercados(gps_regiao, [m["Supermercado"] for m in nova])
                    salvar_preferencias_gps(gps_coords[0], gps_coords[1], gps_regiao, usuario_atual)
                    st.session_state.update({"gps_detalhes": nova, "gps_mercados": _resumir_mercados(nova), "gps_raio_atual": raio})
                    st.rerun()
                except Exception as e:
                    st.warning(f"⚠️ {e}")
        if lg := st.session_state.get("gps_detalhes", []):
            exibir_tabela_e_mapa_regiao(lg, f"✅ **{len(lg)}** estabelecimentos em **{gps_regiao}** ({st.session_state.get('gps_raio_atual', 3)} km) cadastrados automaticamente!")
        else:
            st.info(f"Região atual: **{gps_regiao}**. Clique em **🔄 Buscar e cadastrar neste raio** para ver o mapa completo.")

    st.divider()
    with st.expander("🔎 Pesquisar Cidade / Bairro / CEP manualmente"):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        reg_b = c1.text_input("Cidade, Bairro ou CEP", placeholder="Ex: Campinas - Taquaral, 01310-100").strip()
        if c2.button("Buscar e cadastrar", type="primary", use_container_width=True) and reg_b:
            with st.spinner("Procurando supermercados..."):
                try:
                    loc, lm = buscar_supermercados_por_regiao(reg_b, raio * 1000)
                    st.session_state["res_manual"] = {"regiao": reg_b, "nome_local": loc, "lista": lm, "novos": registrar_varios_mercados(reg_b, [m["Supermercado"] for m in lm]) if (loc and lm) else 0}
                    st.rerun()
                except Exception as e:
                    st.warning(f"⚠️ {e}")
        if res := st.session_state.get("res_manual"):
            if not res["nome_local"]:
                st.error("Localização não encontrada. Tente Cidade e Estado.")
            elif not res["lista"]:
                st.warning("Nenhum supermercado encontrado nesse raio.")
            else:
                exibir_tabela_e_mapa_regiao(res["lista"], f"✅ **{len(res['lista'])}** em **{res['nome_local']}** (+{res['novos']} salvos em **'{res['regiao']}'**).")


def pagina_perfil():
    st.subheader("👤 Meu Perfil")
    u_dict = carregar_usuarios().copy()
    raw_u = u_dict.get(usuario_atual, {})
    reg_u = dict(raw_u) if isinstance(raw_u, dict) else {"tipo": "senha", "hash": raw_u, "nome": nome_usuario}
    df_p, _ = obter_compras_com_datas(usuario_atual)
    criado_em = reg_u.get("criado_em")
    sub_p = f"@{usuario_atual}" + (f" • Conta desde {criado_em}" if criado_em else "")

    with st.container(border=True):
        with st.container(key="perfil_hero_top"):
            c_av, c_inf = st.columns([1, 5], vertical_alignment="center")
            with c_av:
                with st.container(key="avatar_clicavel"):
                    st.markdown(f'<div class="listai-avatar-wrap">{avatar_html(nome_usuario, usuario_atual, 84, True)}<span class="listai-cam-badge">📷</span></div>', unsafe_allow_html=True)
                    if (f_up := st.file_uploader("Foto de perfil", type=list(EXTENSOES_FOTO) + ["jpeg"], label_visibility="collapsed", key=f"up_foto_{st.session_state.get('foto_versao', 0)}")) is not None:
                        raw = f_up.getvalue()
                        if (hf := hashlib.sha256(raw).hexdigest()) != st.session_state.get("ultima_foto_hash"):
                            salvar_foto_perfil(usuario_atual, raw, f_up.name)
                            st.session_state.update({"ultima_foto_hash": hf, "foto_versao": st.session_state.get("foto_versao", 0) + 1, "msg_sucesso": "Foto de perfil atualizada!"})
                            st.rerun()
            with c_inf:
                st.markdown(f'<div class="listai-profile-info"><h3>{html.escape(nome_usuario)}</h3><span>{html.escape(sub_p)}</span><span class="listai-foto-dica">👆 Clique na foto para colocar ou trocar</span></div>', unsafe_allow_html=True)
                if carregar_foto_perfil_base64(usuario_atual) is not None and st.button("🗑️ Remover foto", key="btn_remover_foto"):
                    remover_foto_perfil(usuario_atual)
                    st.session_state.pop("ultima_foto_hash", None)
                    st.session_state.update({"foto_versao": st.session_state.get("foto_versao", 0) + 1, "msg_sucesso": "Foto de perfil removida."})
                    st.rerun()

        st.write("")
        pm1, pm2, pm3 = st.columns(3)
        pm1.metric("🛍️ Compras Salvas", len(df_p))
        pm2.metric("💰 Total Acumulado", formatar_reais(float(df_p["Total"].sum()) if not df_p.empty else 0.0))
        pm3.metric("📍 Região Atual", gps_regiao or "Não definida")

    c_esq, c_dir = st.columns(2)
    with c_esq:
        with st.container(border=True):
            st.markdown("#### 📋 Informações Pessoais")
            with st.form("form_perfil_usuario", border=False):
                p_nome = st.text_input("Nome completo *", value=reg_u.get("nome", nome_usuario))
                p_email = st.text_input("E-mail", value=reg_u.get("email", ""))
                p_tel = st.text_input("Telefone / WhatsApp", value=reg_u.get("telefone", ""))
                p_cid = st.text_input("Cidade / Bairro", value=reg_u.get("cidade", ""))
                if st.form_submit_button("💾 Salvar Informações", type="primary", use_container_width=True):
                    if len(nome_ok := p_nome.strip()) < 2:
                        st.warning("Informe seu nome completo.")
                    else:
                        reg_u.update({"nome": nome_ok, "email": p_email.strip(), "telefone": p_tel.strip(), "cidade": p_cid.strip()})
                        u_dict[usuario_atual] = reg_u
                        salvar_usuarios(u_dict)
                        st.session_state.update({"nome_usuario": nome_ok, "msg_sucesso": "Informações pessoais salvas com sucesso!"})
                        st.rerun()

        with st.expander("🔒 Alterar Senha"):
            with st.form("form_trocar_senha", clear_on_submit=True, border=False):
                s_at = st.text_input("Senha atual", type="password")
                s_nv = st.text_input("Nova senha", type="password", placeholder="Mínimo 4 caracteres")
                s_cf = st.text_input("Confirmar nova senha", type="password")
                if st.form_submit_button("Atualizar senha", use_container_width=True):
                    if not verificar_senha(s_at, reg_u.get("hash", "")):
                        st.error("Senha atual incorreta.")
                    elif len(s_nv) < 4:
                        st.warning("A nova senha deve ter pelo menos 4 caracteres.")
                    elif s_nv != s_cf:
                        st.error("As novas senhas não coincidem.")
                    else:
                        reg_u["hash"] = gerar_hash_senha(s_nv)
                        u_dict[usuario_atual] = reg_u
                        salvar_usuarios(u_dict)
                        st.session_state["msg_sucesso"] = "Senha atualizada com sucesso!"
                        st.rerun()

    with c_dir:
        st.markdown("#### 🎯 Limite Mensal")
        renderizar_painel_limite_mensal(usuario_atual, "perfil", expandir_config=True)
        with st.container(border=True):
            st.markdown("#### 📍 Localização GPS")
            st.caption("Toque no ícone abaixo para detectar sua região e mercados próximos:")
            processar_leitura_gps(streamlit_geolocation(), usuario_atual) if streamlit_geolocation else st.warning("Pacote `streamlit-geolocation` não instalado.")
            if gps_coords:
                st.success(f"📌 **{gps_regiao}** · Mais próximo: **{gps_mercados[0][0]} ({gps_mercados[0][1]} m)**") if (gps_mercados and gps_mercados[0][1] is not None) else st.info(f"📌 Região salva: **{gps_regiao}**")

        with st.expander("⚙️ Inteligência Artificial (API Gemini)", expanded=not bool(api_key)):
            if api_key and origem_api in ("ambiente", "secrets"):
                st.success("API Gemini conectada automaticamente pelo servidor.")
            else:
                if api_key:
                    st.success("API Gemini conectada para sua sessão.")
                with st.form("form_gemini_perfil", border=False):
                    nk = st.text_input("Chave da API Gemini", value=st.session_state.get("gemini_api_key_usuario", ""), type="password", placeholder="Cole sua GEMINI_API_KEY", help="Crie grátis em aistudio.google.com/apikey")
                    if st.form_submit_button("Salvar chave IA", use_container_width=True):
                        st.session_state.update({"gemini_api_key_usuario": nk.strip(), "msg_sucesso": "Chave da API Gemini salva!" if nk.strip() else "Chave removida."})
                        st.rerun()

    if usuario_atual in USUARIOS_ADMIN:
        with st.expander("👑 Admin — Usuários Cadastrados"):
            st.metric("Total de usuários", len(u_dict))
            st.dataframe(pd.DataFrame([{"Usuário": k, "Nome": v.get("nome", k) if isinstance(v, dict) else k, "E-mail": v.get("email", "-") if isinstance(v, dict) else "-", "Cidade": v.get("cidade", "-") if isinstance(v, dict) else "-"} for k, v in sorted(u_dict.items())]), hide_index=True, use_container_width=True)

    st.divider()
    if st.button("🚪 Sair da conta", type="secondary", use_container_width=True, key="perfil_logout"):
        limpar_estado_usuario(incluir_auth=True)
        st.rerun()


# --- Inicialização e Execução ---
if st.session_state.get("gps_usuario_owner") != usuario_atual:
    limpar_estado_usuario(incluir_auth=False)
    prefs = carregar_preferencias_gps(usuario_atual)
    if prefs.get("lat") is not None and prefs.get("lon") is not None:
        rs = prefs.get("regiao", "")
        st.session_state.update({"gps_coords": (float(prefs["lat"]), float(prefs["lon"])), "gps_regiao": rs, "gps_mercados": [(m, None) for m in carregar_mercados().get(rs, [])], "gps_raio_atual": 3, "regiao_para_selecionar": rs})
    st.session_state["gps_usuario_owner"] = usuario_atual

if st.session_state.get("pagina_atual") not in (PAGINAS + [PAGINA_PERFIL]):
    st.session_state["pagina_atual"] = PAGINAS[0]
for k, v in [("form_versao", 0), ("valor_produto", ""), ("valor_quantidade", 1), ("valor_preco", 1.00), ("valor_supermercado", "")]:
    st.session_state.setdefault(k, v)

api_key, origem_api = obter_api_key_gemini()
if st.session_state.pop("rolar_topo", False):
    rolar_para_topo()

gps_coords, gps_regiao, gps_mercados = st.session_state.get("gps_coords"), st.session_state.get("gps_regiao", ""), st.session_state.get("gps_mercados", [])
renderizar_topo_nubank()

if msg := st.session_state.pop("msg_sucesso", None):
    st.success(msg)
if msg_lim := st.session_state.pop("msg_limite_alerta", None):
    st.warning(msg_lim)

{
    PAGINAS[0]: pagina_compra,
    PAGINAS[1]: pagina_pre_lista,
    PAGINAS[2]: pagina_graficos,
    PAGINAS[3]: pagina_historico,
    PAGINAS[4]: pagina_precos,
    PAGINAS[5]: pagina_mercados,
    PAGINA_PERFIL: pagina_perfil,
}[st.session_state["pagina_atual"]]()

exibir_rodape_anuncio()
renderizar_barra_inferior()