import hashlib
import io
import json
import os
import re
import unicodedata

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --- CSS Global + Representação da Bandeira do Estado do Pará ---
ESTILO_CSS = """<style>
html { scroll-behavior: smooth; }
html, body, .stApp { background-color: #FDF7F7 !important; color: #1E1B24 !important; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif !important; overflow-x: clip !important; -webkit-tap-highlight-color: transparent; }
.block-container { padding: 3.7rem 1rem 3.2rem 1rem !important; max-width: 1080px; animation: listaiFadeIn 0.22s ease-out; }
@keyframes listaiFadeIn { from { opacity: 0.92; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }
[data-testid="stHeader"] { background: rgba(253, 247, 247, 0.88) !important; backdrop-filter: blur(8px); }
[data-stale="true"] { opacity: 0.9 !important; transition: opacity 0.14s ease !important; }
.stElementContainer:has(iframe[height="0"]) { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
button, a, input, select, textarea, [role="button"] { touch-action: manipulation; }

h1, h2, h3, h4 { color: #881322 !important; font-weight: 800 !important; letter-spacing: -0.3px; }
label, .stMarkdown p, .stCheckbox p, .stRadio p { color: #1E1B24 !important; }
[data-testid="stCaptionContainer"] p, small { color: #475569 !important; font-size: 0.82rem !important; }
section[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* Topo Representando a Bandeira do Pará (Vermelho + Faixa Branca Diagonal + Estrela Azul) */
.st-key-topo_nubank {
    background-color: #C8102E !important;
    background-image:
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Cpolygon points='20,4 24.4,14.8 36,15.6 27,23.2 29.8,34.6 20,28.4 10.2,34.6 13,23.2 4,15.6 15.6,14.8' fill='%230B4EA2' stroke='%23FFFFFF' stroke-width='2.2' stroke-linejoin='round'/%3E%3C/svg%3E"),
        linear-gradient(148deg, transparent 0%, transparent 56%, rgba(255, 255, 255, 0.22) 56.4%, rgba(255, 255, 255, 0.30) 70%, transparent 70.4%, transparent 100%),
        linear-gradient(135deg, #991B1B 0%, #D91E2A 55%, #B91C1C 100%) !important;
    background-size: 32px 32px, 100% 100%, 100% 100% !important;
    background-position: 69% 50%, center, center !important;
    background-repeat: no-repeat !important;
    border-radius: 16px !important;
    padding: 0.9rem 1rem !important;
    margin-bottom: 0.55rem !important;
    box-shadow: 0 6px 20px rgba(185, 28, 28, 0.24) !important;
    border-bottom: 3px solid #0B4EA2 !important;
    transition: box-shadow 0.2s ease;
}
.st-key-topo_nubank [data-testid="stVerticalBlock"] { background: transparent !important; gap: 0 !important; }
.st-key-topo_nubank [data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: minmax(0, 1fr) auto !important; align-items: center !important; gap: 0.65rem !important; width: 100% !important; }
.st-key-topo_nubank [data-testid="stColumn"] { width: 100% !important; min-width: 0 !important; flex: none !important; }
.st-key-topo_nubank [data-testid="stColumn"]:last-child { width: auto !important; justify-self: end !important; }
.listai-nu-user { display: flex; align-items: center; gap: 0.7rem; width: 100%; min-width: 0; }
.listai-nu-texts { flex: 1 1 auto; min-width: 0; }
.listai-nu-brand { font-size: 0.68rem; font-weight: 800; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.7px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-shadow: 0 1px 3px rgba(0, 0, 0, 0.35); }
.listai-nu-hello { font-size: 1.2rem; font-weight: 800; color: #FFFFFF; line-height: 1.18; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-shadow: 0 1px 3px rgba(0, 0, 0, 0.35); }
.listai-nu-sub { font-size: 0.76rem; color: #FEE2E2; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.28); }
.st-key-topo_nubank .stButton > button { background: #FFFFFF !important; border: 2px solid #DBEAFE !important; color: #0B4EA2 !important; border-radius: 999px !important; padding: 0.36rem 0.85rem !important; font-size: 0.80rem !important; font-weight: 800 !important; white-space: nowrap !important; width: auto !important; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.14) !important; }
.st-key-topo_nubank .stButton > button p { color: #0B4EA2 !important; font-weight: 800 !important; white-space: nowrap !important; }

/* Banner Superior Estilo Carrossel */
.listai-top-ad-wrap { background: #FFFFFF; border: 1px solid #FECACA; border-radius: 12px; padding: 0.4rem 0.45rem; margin-bottom: 0.55rem; box-shadow: 0 2px 8px rgba(185, 28, 28, 0.06); }
.listai-top-ad-strip { display: flex; align-items: stretch; gap: 0.42rem; overflow-x: auto; scrollbar-width: none; -webkit-overflow-scrolling: touch; scroll-snap-type: x proximity; }
.listai-top-ad-strip::-webkit-scrollbar { display: none; }
.listai-top-ad-card { position: relative; flex: 0 0 106px; height: 82px; border-radius: 10px; border: 1px solid #E2E8F0; background: linear-gradient(180deg, #FFFFFF 0%, #FFF5F5 100%); overflow: hidden; text-decoration: none !important; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #1E1B24 !important; scroll-snap-align: start; transition: transform 0.14s ease; }
.listai-top-ad-card:active { transform: scale(0.96); }
.listai-top-ad-card img { width: 100%; height: 100%; object-fit: cover; display: block; }
.listai-top-ad-fallback { padding: 1.45rem 0.42rem 0.35rem 0.42rem; text-align: center; font-size: 0.70rem; font-weight: 700; line-height: 1.18; color: #881322; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; word-break: break-word; }
.listai-top-ad-disc { position: absolute; top: 5px; left: 5px; background: #0B4EA2; color: #FFFFFF; font-size: 0.62rem; font-weight: 800; padding: 1px 6px; border-radius: 5px; line-height: 1.2; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2); }
.listai-top-ad-store { flex: 0 0 88px; height: 82px; border-radius: 10px; border: 1px solid #BFDBFE; background: #EFF6FF; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 0.3rem; text-decoration: none !important; position: relative; scroll-snap-align: start; transition: transform 0.14s ease; }
.listai-top-ad-store:active { transform: scale(0.96); }
.listai-top-ad-info { position: absolute; top: 4px; right: 6px; font-size: 0.65rem; color: #0B4EA2; font-weight: 800; }
.listai-top-ad-store-name { font-size: 0.72rem; font-weight: 800; color: #0B4EA2; line-height: 1.15; margin-top: 4px; word-break: break-word; }
.listai-top-ad-store-cta { font-size: 0.60rem; color: #1D4ED8; font-weight: 700; margin-top: 2px; }

/* Barra de Navegação Superior */
.st-key-barra_navegacao { background: #FFFFFF !important; border: 1.5px solid #FCA5A5 !important; border-radius: 14px !important; padding: 0.28rem 0.32rem !important; margin-bottom: 0.75rem !important; box-shadow: 0 3px 12px rgba(185, 28, 28, 0.08) !important; }
.st-key-barra_navegacao [data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-key-barra_navegacao [data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: repeat(6, minmax(0, 1fr)) !important; gap: 0.18rem !important; width: 100% !important; }
.st-key-barra_navegacao [data-testid="stColumn"] { width: 100% !important; min-width: 0 !important; flex: none !important; }
.st-key-barra_navegacao .stButton > button { border-radius: 10px !important; padding: 0.32rem 0.06rem !important; min-height: 2.6rem !important; line-height: 1.1 !important; box-shadow: none !important; width: 100% !important; transition: background-color 0.16s ease, transform 0.12s ease !important; }
.st-key-barra_navegacao .stButton > button p { font-size: 0.72rem !important; font-weight: 700 !important; line-height: 1.12 !important; margin: 0 !important; white-space: pre-line !important; }
.st-key-barra_navegacao .stButton > button[kind="secondary"] { background: transparent !important; border: none !important; color: #334155 !important; }
.st-key-barra_navegacao .stButton > button[kind="secondary"]:hover { background: #FEF2F2 !important; }
.st-key-barra_navegacao .stButton > button[kind="primary"] { background: linear-gradient(135deg, #0B4EA2, #1D4ED8) !important; color: #FFFFFF !important; }
.st-key-barra_navegacao .stButton > button[kind="primary"] p { color: #FFFFFF !important; }

/* Leitor Estilo Pix */
.listai-pix-banner { background: linear-gradient(135deg, #991B1B 0%, #D91E2A 55%, #0B4EA2 100%); color: #FFFFFF; border-radius: 13px; padding: 0.68rem 0.88rem; margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; }
.listai-pix-title { font-size: 0.92rem; font-weight: 800; color: #FFFFFF; }
.listai-pix-sub { font-size: 0.75rem; color: #FEE2E2; margin-top: 1px; }
.listai-pix-pill { background: rgba(255, 255, 255, 0.22); border: 1px solid rgba(255, 255, 255, 0.42); color: #FFFFFF; font-size: 0.68rem; font-weight: 800; padding: 0.16rem 0.52rem; border-radius: 999px; white-space: nowrap; }
.st-key-leitor_pix_cam { background: #1F0B0E !important; border: 2px dashed #FFFFFF !important; border-radius: 14px !important; padding: 0.5rem !important; box-shadow: inset 0 0 0 2px rgba(11, 78, 162, 0.45) !important; }
.st-key-leitor_pix_cam [data-testid="stCameraInput"] video,
.st-key-leitor_pix_cam [data-testid="stCameraInput"] img { border-radius: 10px !important; border: 2px solid #0B4EA2 !important; }
.st-key-leitor_pix_cam [data-testid="stCameraInput"] button { background: #0B4EA2 !important; color: #FFFFFF !important; border: none !important; font-weight: 800 !important; border-radius: 999px !important; }
.st-key-leitor_pix_gal [data-testid="stFileUploaderDropzone"] { background: #EFF6FF !important; border: 2px dashed #0B4EA2 !important; border-radius: 13px !important; padding: 0.9rem !important; }

/* Grids Fixos */
[class*="st-key-kpi_2cols"] [data-testid="stHorizontalBlock"], .st-key-row_qtd_preco [data-testid="stHorizontalBlock"],
.st-key-acao_add_voz [data-testid="stHorizontalBlock"], .st-key-add_lista_row [data-testid="stHorizontalBlock"],
.st-key-lista_chk_box [data-testid="stHorizontalBlock"], [class*="st-key-compra_grp_"] [data-testid="stHorizontalBlock"],
[class*="st-key-edit_qp_"] [data-testid="stHorizontalBlock"], [class*="st-key-edit_btns_"] [data-testid="stHorizontalBlock"],
.st-key-foto_btns_row [data-testid="stHorizontalBlock"], .st-key-foto_pos_row [data-testid="stHorizontalBlock"],
[class*="st-key-mkt_card_"] [data-testid="stHorizontalBlock"], .st-key-fam_bar [data-testid="stHorizontalBlock"],
[class*="st-key-adm_ad_row_"] [data-testid="stHorizontalBlock"] {
    display: grid !important; gap: 0.45rem !important; align-items: center !important; width: 100% !important;
}
[class*="st-key-kpi_2cols"] [data-testid="stHorizontalBlock"], [class*="st-key-edit_qp_"] [data-testid="stHorizontalBlock"],
.st-key-foto_btns_row [data-testid="stHorizontalBlock"], .st-key-foto_pos_row [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
.st-key-row_qtd_preco [data-testid="stHorizontalBlock"] { grid-template-columns: 0.85fr 1.15fr !important; align-items: end !important; }
.st-key-acao_add_voz [data-testid="stHorizontalBlock"] { grid-template-columns: 1fr 1.35fr !important; align-items: center !important; }
.st-key-add_lista_row [data-testid="stHorizontalBlock"] { grid-template-columns: minmax(0, 1fr) 64px !important; align-items: end !important; }
.st-key-lista_chk_box [data-testid="stHorizontalBlock"] { grid-template-columns: minmax(0, 1fr) 40px 40px !important; gap: 0.25rem !important; }
.st-key-fam_bar [data-testid="stHorizontalBlock"] { grid-template-columns: minmax(0, 1fr) auto !important; gap: 0.45rem !important; }
[class*="st-key-compra_grp_"] [data-testid="stHorizontalBlock"], [class*="st-key-adm_ad_row_"] [data-testid="stHorizontalBlock"] { grid-template-columns: minmax(0, 1fr) 42px !important; gap: 0.35rem !important; }
[class*="st-key-edit_btns_"] [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; }
[class*="st-key-kpi_4cols"] [data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)) !important; gap: 0.5rem !important; width: 100% !important; }
[class*="st-key-kpi_3cols"] [data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: repeat(3, minmax(0, 1fr)) !important; gap: 0.5rem !important; width: 100% !important; }
[class*="st-key-mkt_card_"] [data-testid="stHorizontalBlock"] { grid-template-columns: minmax(0, 1fr) auto !important; align-items: center !important; }
[class*="st-key-kpi_2cols"] [data-testid="stColumn"], [class*="st-key-kpi_3cols"] [data-testid="stColumn"],
[class*="st-key-kpi_4cols"] [data-testid="stColumn"], .st-key-row_qtd_preco [data-testid="stColumn"],
.st-key-acao_add_voz [data-testid="stColumn"], .st-key-add_lista_row [data-testid="stColumn"], .st-key-lista_chk_box [data-testid="stColumn"],
[class*="st-key-compra_grp_"] [data-testid="stColumn"], [class*="st-key-edit_qp_"] [data-testid="stColumn"],
[class*="st-key-edit_btns_"] [data-testid="stColumn"], .st-key-foto_btns_row [data-testid="stColumn"],
.st-key-foto_pos_row [data-testid="stColumn"], [class*="st-key-mkt_card_"] [data-testid="stColumn"],
.st-key-fam_bar [data-testid="stColumn"], [class*="st-key-adm_ad_row_"] [data-testid="stColumn"] { width: 100% !important; min-width: 0 !important; flex: none !important; }

/* Gravador de Áudio Nativo */
.st-key-acao_add_voz .stButton > button { height: 44px !important; min-height: 44px !important; margin: 0 !important; }
.st-key-acao_add_voz [data-testid="stAudioInput"] { width: 100% !important; margin: 0 !important; }
.st-key-acao_add_voz [data-testid="stAudioInput"] > div { background: #EFF6FF !important; border: 1.5px solid #0B4EA2 !important; border-radius: 10px !important; min-height: 44px !important; }
.st-key-acao_add_voz [data-testid="stAudioInput"] button[aria-label*="Stop" i],
.st-key-acao_add_voz [data-testid="stAudioInput"] button[aria-label*="Parar" i] { background: #D91E2A !important; color: #FFFFFF !important; border-radius: 8px !important; }

/* Compra Ativa, Lista & Família */
.st-key-lista_chk_box .stButton > button, [class*="st-key-compra_grp_"] .stButton > button { padding: 0.25rem 0.2rem !important; min-height: 2.1rem !important; font-size: 0.85rem !important; }
.st-key-lista_chk_box .stCheckbox { margin: 0 !important; }
.st-key-lista_chk_box .stCheckbox label p { font-size: 0.88rem !important; line-height: 1.25 !important; word-break: break-word !important; }
.listai-fam-badge { background: linear-gradient(135deg, #FEF2F2, #EFF6FF); border: 1px solid #FCA5A5; border-radius: 11px; padding: 0.45rem 0.72rem; font-size: 0.82rem; font-weight: 700; color: #881322; }
.listai-fam-code { background: #FFFFFF; border: 1px dashed #0B4EA2; color: #0B4EA2; padding: 0.08rem 0.45rem; border-radius: 6px; font-family: monospace; font-size: 0.86rem; font-weight: 800; }
.listai-start-hero { background: linear-gradient(135deg, #FFF5F5 0%, #FFFFFF 100%); border: 1px solid #FECACA; border-left: 5px solid #D91E2A; border-radius: 14px; padding: 1rem 1.05rem; margin-bottom: 0.7rem; }
.listai-start-hero h3 { margin: 0 0 0.25rem 0 !important; font-size: 1.08rem !important; color: #881322 !important; }
.listai-start-hero p { margin: 0 !important; font-size: 0.85rem !important; color: #475569 !important; }
.listai-compra-banner { background: linear-gradient(145deg, #FFF5F5 0%, #FFFFFF 60%, #EFF6FF 100%); border: 1px solid #FECACA; border-left: 5px solid #D91E2A; border-radius: 13px; padding: 0.8rem 0.95rem; margin-bottom: 0.65rem; display: flex; justify-content: space-between; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.listai-compra-eyebrow { font-size: 0.72rem; font-weight: 800; color: #C8102E; text-transform: uppercase; letter-spacing: 0.5px; }
.listai-compra-merc { font-size: 1.08rem; font-weight: 800; color: #881322; margin-top: 2px; }
.listai-compra-data { font-size: 0.80rem; color: #475569; margin-top: 2px; }
.listai-compra-total-box { text-align: right; }
.listai-compra-total-lbl { font-size: 0.72rem; color: #475569; font-weight: 600; }
.listai-compra-total-val { font-size: 1.28rem; font-weight: 800; color: #0B4EA2; line-height: 1.1; }
.listai-rec-row { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.45rem 0.65rem; min-width: 0; transition: background-color 0.15s ease; }
.listai-rec-nome { font-weight: 700; font-size: 0.88rem; color: #881322; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.listai-rec-meta { font-size: 0.76rem; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Banco de Dados de Preços & Tabelas Estilizadas */
.listai-db-head { background: linear-gradient(135deg, #FFFFFF 0%, #FFF5F5 100%); border: 1px solid #FECACA; border-left: 5px solid #D91E2A; border-radius: 13px; padding: 0.75rem 0.9rem; margin: 0.45rem 0 0.35rem 0; display: flex; justify-content: space-between; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.listai-db-title { font-size: 0.98rem; font-weight: 800; color: #881322; }
.listai-db-sub { font-size: 0.77rem; color: #475569; margin-top: 2px; }
.listai-db-badges { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; }
.listai-db-wrap { background: #FFFFFF; border: 1px solid #FECACA; border-radius: 12px; overflow: hidden; margin: 0.2rem 0 0.55rem 0; box-shadow: 0 2px 8px rgba(185, 28, 28, 0.05); }
.listai-db-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; table-layout: auto; }
.listai-db-table thead th { background: #FEF2F2; color: #881322; font-weight: 800; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.45px; padding: 0.58rem 0.75rem; border-bottom: 1.5px solid #FECACA; text-align: left; white-space: nowrap; }
.listai-db-table thead th.num { text-align: right; }
.listai-db-table tbody tr { border-bottom: 1px solid #F1F5F9; transition: background 0.15s ease; }
.listai-db-table tbody tr:nth-child(even) { background: #FFFAFA; }
.listai-db-table tbody tr:hover { background: #EFF6FF; }
.listai-db-table tbody tr:last-child { border-bottom: none; }
.listai-db-table tbody td { padding: 0.56rem 0.75rem; vertical-align: middle; color: #1E1B24; }
.listai-db-prod { font-weight: 700; color: #881322; font-size: 0.89rem; word-break: break-word; line-height: 1.25; }
.listai-db-meta { font-size: 0.74rem; color: #64748B; margin-top: 2px; line-height: 1.25; }
.listai-db-price { text-align: right; font-weight: 800; color: #0B4EA2; font-size: 0.92rem; white-space: nowrap; font-variant-numeric: tabular-nums; }
.listai-db-price-best { color: #15803D; }
.listai-db-status { text-align: right; white-space: nowrap; }
.listai-st-best { display: inline-block; background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; font-size: 0.71rem; font-weight: 800; padding: 0.12rem 0.48rem; border-radius: 999px; }
.listai-st-up { display: inline-block; background: #FFF7ED; color: #B45309; border: 1px solid #FED7AA; font-size: 0.71rem; font-weight: 700; padding: 0.12rem 0.48rem; border-radius: 999px; }
.listai-st-only { display: inline-block; background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; font-size: 0.71rem; font-weight: 600; padding: 0.12rem 0.48rem; border-radius: 999px; }

.listai-pill-best { background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; font-size: 0.72rem; font-weight: 800; padding: 0.14rem 0.52rem; border-radius: 999px; }
.listai-pill-mid { background: #EFF6FF; color: #0B4EA2; border: 1px solid #BFDBFE; font-size: 0.72rem; font-weight: 800; padding: 0.14rem 0.52rem; border-radius: 999px; }
.listai-pill-high { background: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; font-size: 0.72rem; font-weight: 800; padding: 0.14rem 0.52rem; border-radius: 999px; }
.listai-pill-muted { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; font-size: 0.72rem; font-weight: 700; padding: 0.14rem 0.52rem; border-radius: 999px; }

.listai-mkt-item { display: flex; align-items: flex-start; gap: 0.65rem; min-width: 0; }
.listai-mkt-rank { width: 36px; height: 36px; border-radius: 10px; background: #FEF2F2; border: 1px solid #FCA5A5; color: #881322; font-weight: 800; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.listai-mkt-rank-top { background: linear-gradient(135deg, #0B4EA2, #1D4ED8); color: #FFFFFF; border-color: #0B4EA2; }
.listai-mkt-info { min-width: 0; flex: 1; }
.listai-mkt-name { font-size: 0.96rem; font-weight: 800; color: #881322; word-break: break-word; }
.listai-mkt-meta { font-size: 0.77rem; color: #475569; margin-top: 2px; word-break: break-word; }
.listai-mkt-tags { display: flex; flex-wrap: wrap; gap: 0.28rem; margin-top: 0.32rem; }

/* Avatares, Foto Clicável e Prévia */
.listai-avatar, .listai-avatar-solid { border-radius: 50%; color: #FFFFFF; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.listai-avatar { background: rgba(255, 255, 255, 0.22); border: 2px solid rgba(255, 255, 255, 0.92); }
.listai-avatar-solid { background: linear-gradient(135deg, #991B1B, #0B4EA2); border: 2px solid #FCA5A5; }
.listai-avatar-img { border-radius: 50%; object-fit: cover; border: 2px solid rgba(255, 255, 255, 0.92); flex-shrink: 0; display: block; }
.listai-foto-preview { display: flex; flex-direction: column; align-items: center; margin: 0.35rem 0 0.6rem 0; }
.listai-foto-preview img { width: 132px; height: 132px; border-radius: 50%; object-fit: cover; border: 3px solid #0B4EA2; box-shadow: 0 4px 16px rgba(11, 78, 162, 0.24); }
.st-key-perfil_hero_top [data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: 78px minmax(0, 1fr) !important; align-items: center !important; gap: 0.85rem !important; width: 100% !important; }
.st-key-perfil_hero_top [data-testid="stColumn"] { width: 100% !important; min-width: 0 !important; flex: none !important; }
.st-key-avatar_clicavel, .st-key-avatar_clicavel [data-testid="stVerticalBlock"], .listai-avatar-wrap { position: relative !important; width: 78px !important; height: 78px !important; border-radius: 50% !important; gap: 0 !important; }
.st-key-avatar_clicavel { cursor: pointer !important; }
.listai-cam-badge { position: absolute; right: 0; bottom: 0; width: 26px; height: 26px; border-radius: 50%; background: #0B4EA2; border: 2px solid #FFFFFF; color: #FFFFFF; font-size: 12px; display: flex; align-items: center; justify-content: center; pointer-events: none; }
.st-key-avatar_clicavel [data-testid="stFileUploader"] { position: absolute !important; inset: 0 !important; width: 78px !important; height: 78px !important; opacity: 0.001 !important; z-index: 20 !important; margin: 0 !important; padding: 0 !important; overflow: hidden !important; border-radius: 50% !important; }
.st-key-avatar_clicavel [data-testid="stFileUploaderDropzone"], .st-key-avatar_clicavel [data-testid="stFileUploaderDropzone"] button { position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; min-height: 78px !important; padding: 0 !important; border: none !important; border-radius: 50% !important; }
.st-key-avatar_clicavel [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
.st-key-foto_btns_row .stButton > button { padding: 0.28rem 0.5rem !important; min-height: 2.1rem !important; font-size: 0.80rem !important; margin-top: 0.35rem !important; }

/* Cards Diversos & Login Representando a Bandeira do Pará */
[data-testid="stVerticalBlockBorderWrapper"] { transition: box-shadow 0.18s ease, border-color 0.18s ease; }
.listai-header {
    background-color: #C8102E;
    background-image:
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Cpolygon points='20,4 24.4,14.8 36,15.6 27,23.2 29.8,34.6 20,28.4 10.2,34.6 13,23.2 4,15.6 15.6,14.8' fill='%230B4EA2' stroke='%23FFFFFF' stroke-width='2.2' stroke-linejoin='round'/%3E%3C/svg%3E"),
        linear-gradient(148deg, transparent 0%, transparent 56%, rgba(255, 255, 255, 0.22) 56.4%, rgba(255, 255, 255, 0.30) 70%, transparent 70.4%, transparent 100%),
        linear-gradient(135deg, #991B1B 0%, #D91E2A 55%, #B91C1C 100%);
    background-size: 32px 32px, 100% 100%, 100% 100%;
    background-position: 69% 50%, center, center;
    background-repeat: no-repeat;
    padding: 1.05rem 1.2rem;
    border-radius: 16px;
    border-bottom: 3px solid #0B4EA2;
    color: #FFFFFF !important;
    margin-bottom: 0.8rem;
    box-shadow: 0 6px 20px rgba(185, 28, 28, 0.20);
}
.listai-header-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
.listai-brand { display: flex; align-items: center; gap: 0.7rem; }
.listai-logo-badge { background: #FFFFFF; width: 42px; height: 42px; border-radius: 11px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18); }
.listai-header h1 { margin: 0 !important; font-size: 1.55rem !important; color: #FFFFFF !important; text-shadow: 0 1px 3px rgba(0, 0, 0, 0.35); }
.listai-header p { margin: 0.25rem 0 0 0 !important; font-size: 0.88rem !important; color: #FEE2E2 !important; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.25); }
.listai-pill { background: #0B4EA2; border: 1px solid rgba(255, 255, 255, 0.55); color: #FFFFFF !important; padding: 0.2rem 0.65rem; border-radius: 999px; font-size: 0.72rem; font-weight: 800; }
.listai-winner-card { background: linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 55%, #ECFDF5 100%); border: 1px solid #93C5FD; border-left: 6px solid #0B4EA2; border-radius: 14px; padding: 0.9rem 1.05rem; color: #1E1B24; margin-bottom: 0.8rem; display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.listai-winner-card h3 { margin: 0 0 0.2rem 0 !important; font-size: 1.05rem !important; color: #0B4EA2 !important; }
.listai-winner-price { font-size: 1.35rem; font-weight: 800; color: #15803D; }
.listai-eco-pill { display: inline-block; background: #16A34A; color: #FFFFFF; font-size: 0.72rem; font-weight: 700; padding: 0.16rem 0.55rem; border-radius: 999px; margin-top: 4px; }
.listai-profile-info h3 { margin: 0 !important; font-size: 1.15rem !important; }
.listai-profile-info span { color: #475569; font-size: 0.84rem; display: block; margin-top: 2px; }
.listai-foto-dica { color: #0B4EA2 !important; font-weight: 600; font-size: 0.78rem !important; }
.listai-ad-badge { display: inline-block; background: #FEE2E2; color: #991B1B; font-size: 0.68rem; font-weight: 800; padding: 0.12rem 0.48rem; border-radius: 6px; margin-right: 0.3rem; }
.listai-ad-cupom { display: inline-block; background: #EFF6FF; color: #0B4EA2; border: 1px dashed #0B4EA2; font-size: 0.70rem; font-weight: 800; padding: 0.08rem 0.45rem; border-radius: 6px; margin-left: 0.35rem; font-family: monospace; }

/* Histórico e Feed */
.listai-hist-card { background: #FFFFFF; border: 1px solid #FECACA; border-left: 5px solid #D91E2A; border-radius: 13px; padding: 0.75rem 0.9rem 0.55rem 0.9rem; margin-bottom: 0.35rem; }
.listai-hist-head { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.listai-hist-title { font-size: 0.96rem; font-weight: 800; color: #881322; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.listai-hist-badge { background: #EFF6FF; color: #0B4EA2; border: 1px solid #BFDBFE; font-size: 0.71rem; font-weight: 700; padding: 0.1rem 0.48rem; border-radius: 999px; }
.listai-hist-total { font-size: 1rem; font-weight: 800; color: #0B4EA2; }
.listai-hist-track { width: 100%; height: 5px; background: #FEE2E2; border-radius: 999px; overflow: hidden; margin-top: 0.45rem; }
.listai-hist-fill { height: 100%; background: linear-gradient(90deg, #D91E2A, #0B4EA2); border-radius: 999px; transition: width 0.35s ease; }
.listai-hist-item { display: flex; justify-content: space-between; align-items: center; gap: 0.6rem; padding: 0.45rem 0.15rem; border-bottom: 1px solid #F1F5F9; }
.listai-hist-item:last-child, .listai-feed-row:last-child { border-bottom: none; }
.listai-hist-prod, .listai-feed-name { font-weight: 700; color: #1E1B24; font-size: 0.90rem; word-break: break-word; }
.listai-hist-meta { font-size: 0.77rem; color: #64748B; margin-top: 2px; }
.listai-hist-right { text-align: right; flex-shrink: 0; }
.listai-hist-val { font-weight: 800; color: #881322; font-size: 0.90rem; }
.listai-hist-unit { font-size: 0.74rem; color: #64748B; }
.listai-feed-day { display: flex; justify-content: space-between; align-items: center; margin: 0.7rem 0 0.3rem 0; padding: 0 0.2rem; font-size: 0.81rem; font-weight: 800; color: #881322; }
.listai-feed-day span:last-child { color: #0B4EA2; }
.listai-feed-box { background: #FFFFFF; border: 1px solid #FECACA; border-radius: 14px; padding: 0.2rem 0.8rem; margin-bottom: 0.55rem; }
.listai-feed-row { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; padding: 0.58rem 0; border-bottom: 1px solid #F1F5F9; }
.listai-feed-left { display: flex; align-items: center; gap: 0.6rem; min-width: 0; flex: 1; }
.listai-feed-info { min-width: 0; }
.listai-feed-ico { width: 34px; height: 34px; border-radius: 10px; background: #FEF2F2; border: 1px solid #FECACA; display: flex; align-items: center; justify-content: center; font-size: 0.95rem; font-weight: 800; color: #881322; flex-shrink: 0; }
.listai-feed-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 3px; }
.listai-feed-tag { background: #F1F5F9; color: #334155; font-size: 0.70rem; font-weight: 600; padding: 0.08rem 0.42rem; border-radius: 6px; }
.listai-feed-tag-cat { background: #EFF6FF; color: #0B4EA2; }

/* Botões, DataFrames e Métricas */
[data-testid="stDataFrame"] { border: 1px solid #FECACA !important; border-radius: 12px !important; overflow: hidden !important; background: #FFFFFF !important; }
div[data-testid="stMetric"] { background-color: #FFFFFF !important; border: 1px solid #FECACA !important; border-left: 5px solid #D91E2A !important; padding: 10px 14px; border-radius: 12px; }
div[data-testid="stMetricLabel"] p { color: #334155 !important; font-weight: 600 !important; font-size: 0.82rem !important; }
div[data-testid="stMetricValue"] { color: #881322 !important; font-weight: 800 !important; font-size: 1.35rem !important; }
.stButton > button, .stLinkButton > a, .stFormSubmitButton > button { border-radius: 10px !important; font-weight: 600 !important; font-size: 0.90rem !important; transition: transform 0.12s ease, background-color 0.15s ease, box-shadow 0.15s ease !important; }
.stButton > button:active, .stLinkButton > a:active, .stFormSubmitButton > button:active { transform: scale(0.98) !important; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background-color: #0B4EA2 !important; border: none !important; color: #FFFFFF !important; }
.stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] p { color: #FFFFFF !important; }
.stButton > button[kind="secondary"] { background-color: #FFFFFF !important; border: 1px solid #FCA5A5 !important; color: #881322 !important; }
div[data-testid="stProgress"] > div > div > div > div { background: linear-gradient(90deg, #D91E2A, #0B4EA2) !important; transition: width 0.3s ease !important; }

@media (max-width: 680px) {
    .block-container { padding: 3.9rem 0.65rem 4.5rem 0.65rem !important; }
    .st-key-topo_nubank { padding: 0.82rem 0.85rem !important; margin-bottom: 0.45rem !important; }
    .listai-nu-hello { font-size: 1.05rem !important; }
    .st-key-topo_nubank .stButton > button { padding: 0.3rem 0.7rem !important; font-size: 0.76rem !important; }
    div[data-testid="stMetric"] { padding: 8px 11px !important; }
    div[data-testid="stMetricValue"] { font-size: 1.15rem !important; }
    [class*="st-key-kpi_4cols"] [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
    [class*="st-key-mkt_card_"] [data-testid="stHorizontalBlock"] { grid-template-columns: 1fr !important; }
    .st-key-barra_navegacao { padding: 0.22rem 0.22rem !important; margin-bottom: 0.55rem !important; }
    .st-key-barra_navegacao [data-testid="stHorizontalBlock"] { gap: 0.1rem !important; }
    .st-key-barra_navegacao .stButton > button { min-height: 2.38rem !important; padding: 0.2rem 0.02rem !important; }
    .st-key-barra_navegacao .stButton > button p { font-size: 0.59rem !important; }
    .listai-db-table thead th, .listai-db-table tbody td { padding: 0.48rem 0.52rem; }
    .listai-db-prod { font-size: 0.84rem; }
    .listai-db-price { font-size: 0.86rem; }
}
</style>"""

LOGO_SVG = '<div class="listai-logo-badge"><svg width="24" height="24" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="lg" x1="0" y1="12" x2="24" y2="4" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#D91E2A"/><stop offset="55%" stop-color="#0B4EA2"/><stop offset="100%" stop-color="#1D4ED8"/></linearGradient></defs><path d="M2 4H5L7.4 14.5C7.6 15.4 8.4 16 9.3 16H17.5C18.4 16 19.2 15.4 19.4 14.5L21 7H6" stroke="url(#lg)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.5 10.2L12 12.6L19.5 4.8" stroke="url(#lg)" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="9.5" cy="19.5" r="1.6" fill="#D91E2A"/><circle cx="17" cy="19.5" r="1.6" fill="#0B4EA2"/></svg></div>'
# --- Constantes ---
PASTA_DADOS_USUARIOS = "dados_usuarios"
ARQUIVO_COMUNIDADE = "precos_comunidade.csv"
ARQUIVO_MERCADOS = "supermercados.json"
ARQUIVO_USUARIOS = "usuarios.json"
ARQUIVO_ANUNCIOS = "anuncios.json"

NAV_ITENS = [("🛒", "Compra"), ("📝", "Lista"), ("📊", "Gráficos"), ("🧾", "Histórico"), ("🏆", "Preços"), ("🗺️", "Mercados")]
PAGINAS = [f"{ico} {txt}" for ico, txt in NAV_ITENS]
PAGINA_PERFIL = "👤 Perfil"
PERGUNTAS_SEGURANCA = [
    "Qual o nome do seu primeiro pet?",
    "Qual sua cidade natal?",
    "Qual o nome da sua mãe?",
    "Qual sua comida favorita?",
    "Qual o nome da sua escola de infância?",
]

COLUNAS = ["Data", "Região", "Supermercado", "Produto", "Categoria", "Quantidade", "Preço Unitário", "Total"]
COLUNAS_PRE_LISTA = ["ID", "Produto", "Quantidade", "Categoria", "Comprado"]
COLUNAS_COMUNIDADE = ["Data", "Região", "Supermercado", "Produto", "Categoria", "Preço Unitário", "Usuário"]

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
]
TRADUCAO_LOJA = {
    "supermarket": "Supermercado",
    "wholesale": "Atacarejo",
    "convenience": "Mercearia / Minimercado",
    "greengrocer": "Hortifruti / Sacolão",
}
RAIO_OPCOES = [1, 3, 5, 10, 15]
RAIO_LABELS = {1: "1 km · A pé", 3: "3 km · Bairro", 5: "5 km · Região", 10: "10 km · Cidade", 15: "15 km · Amplo"}
EXTENSOES_FOTO = ("jpg", "png", "webp")
MAX_FOTO_BYTES = 8 * 1024 * 1024
CHAVES_EDITOR_FOTO = ("foto_rascunho", "editando_foto", "foto_ed_modo", "foto_ed_zoom", "foto_ed_px", "foto_ed_py", "foto_ed_rot")
ALFABETO_CASA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

ANUNCIOS_PADRAO = [
    {"id": None, "titulo": "🔥 Ofertas Amazon", "descricao": "Descontos em café, bebidas, limpeza e despensa.", "texto_botao": "Amazon", "url": "https://www.amazon.com.br/", "categoria": "Geral", "regiao": "", "cupom": "", "desconto": "-15%", "imagem_url": "", "script_html": ""},
    {"id": None, "titulo": "🧽 Limpeza e Casa", "descricao": "Sabão, amaciante e multiuso em promoção no Mercado Livre.", "texto_botao": "Mercado Livre", "url": "https://www.mercadolivre.com.br/", "categoria": "Limpeza", "regiao": "", "cupom": "", "desconto": "-10%", "imagem_url": "", "script_html": ""},
    {"id": None, "titulo": "🐾 Mundo Pet", "descricao": "Ração, petiscos e tapetes higiênicos na Shopee.", "texto_botao": "Shopee", "url": "https://shopee.com.br/", "categoria": "Pet Shop", "regiao": "", "cupom": "", "desconto": "-20%", "imagem_url": "", "script_html": ""},
    {"id": None, "titulo": "☕ Café e Despensa", "descricao": "Compare kits econômicos com entrega rápida na Amazon.", "texto_botao": "Amazon", "url": "https://www.amazon.com.br/", "categoria": "Bebidas", "regiao": "", "cupom": "", "desconto": "-12%", "imagem_url": "", "script_html": ""},
]

ICONES_CATEGORIA = {
    "Alimentos": "🍚", "Bebidas": "🥤", "Hortifruti": "🥬", "Açougue e Peixaria": "🥩",
    "Frios e Laticínios": "🧀", "Padaria": "🥖", "Limpeza": "🧽", "Higiene Pessoal": "🧴",
    "Pet Shop": "🐾", "Utilidades Domésticas": "🏠", "Outros": "📦",
}
LISTA_CATEGORIAS = list(ICONES_CATEGORIA.keys())

CATEGORIAS_FALLBACK = {
    "Açougue e Peixaria": ["carne", "carne moida", "picanha", "alcatra", "patinho", "acem", "coxao", "maminha", "fraldinha", "contrafile", "bisteca", "costela", "lombo", "pernil", "linguica", "salsicha", "frango", "peito de frango", "sobrecoxa", "peixe", "tilapia", "salmao", "camarao", "bacalhau"],
    "Frios e Laticínios": ["queijo", "mussarela", "requeijao", "cream cheese", "presunto", "peito de peru", "mortadela", "salame", "manteiga", "margarina", "iogurte", "danone", "creme de leite", "leite condensado", "nata", "ricota"],
    "Padaria": ["pao", "pao de forma", "pao frances", "bisnaguinha", "bolo", "torta", "croissant", "broa", "rosquinha", "torrada", "panetone"],
    "Higiene Pessoal": ["papel higienico", "sabonete", "shampoo", "xampu", "condicionador", "creme dental", "pasta de dente", "escova de dente", "fio dental", "desodorante", "absorvente", "fralda", "barbeador", "lenco umedecido", "cotonete", "hidratante"],
    "Limpeza": ["agua sanitaria", "detergente", "sabao", "sabao em po", "sabao liquido", "desinfetante", "amaciante", "esponja", "palha de aco", "bombril", "alvejante", "limpador", "multiuso", "saco de lixo", "vassoura", "rodo", "pano de chao", "alcool"],
    "Pet Shop": ["racao", "petisco", "sache", "areia higienica", "tapete higienico", "coleira"],
    "Utilidades Domésticas": ["papel aluminio", "papel toalha", "filme pvc", "guardanapo", "vela", "fosforo", "lampada", "pilha", "copo descartavel"],
    "Bebidas": ["agua", "agua mineral", "refrigerante", "coca", "guarana", "suco", "cerveja", "vinho", "leite", "cafe", "cha", "energetico", "achocolatado", "nescau", "toddy", "agua de coco"],
    "Hortifruti": ["banana", "maca", "pera", "laranja", "tangerina", "uva", "mamao", "melancia", "melao", "abacaxi", "limao", "morango", "manga", "tomate", "cebola", "batata", "mandioca", "cenoura", "beterraba", "alface", "couve", "rucula", "pepino", "abobora", "chuchu", "pimentao", "alho", "brocolis"],
    "Alimentos": ["arroz", "feijao", "macarrao", "espaguete", "ovo", "ovos", "farinha", "trigo", "fuba", "acucar", "sal", "biscoito", "bolacha", "oleo", "azeite", "vinagre", "molho", "molho de tomate", "extrato de tomate", "ketchup", "maionese", "mostarda", "milho", "ervilha", "atum", "sardinha", "aveia", "granola", "chocolate", "pipoca"],
}


def normalizar_texto(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower().strip()) if unicodedata.category(c) != "Mn")


REGRAS_CATEGORIA = sorted(
    [(re.compile(rf"\b{re.escape(normalizar_texto(p))}\b"), cat, len(normalizar_texto(p))) for cat, ps in CATEGORIAS_FALLBACK.items() for p in ps],
    key=lambda x: x[2],
    reverse=True,
)


# --- Segredos, HTTP e Supabase ---
def ler_segredo(nome):
    if v := os.getenv(nome):
        return v.strip()
    try:
        if v := st.secrets.get(nome):
            return str(v).strip()
    except Exception:
        pass
    return ""


@st.cache_resource
def obter_config_supabase():
    url = re.sub(r"/rest/v1/?$", "", ler_segredo("SUPABASE_URL").rstrip("/"))
    key = ler_segredo("SUPABASE_KEY") or ler_segredo("SUPABASE_ANON_KEY")
    return (url, key) if (url.startswith("https://") and key) else (None, None)


def supabase_ativo():
    return obter_config_supabase()[0] is not None


@st.cache_resource
def obter_http_session():
    import requests
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "ListaiApp/1.0 (https://listai.streamlit.app)",
        "Accept": "application/json",
    })
    return sess


def sb_req(method, tabela, params=None, json_data=None, extra_headers=None):
    url, key = obter_config_supabase()
    headers = {"apikey": key, "Content-Type": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    if extra_headers:
        headers.update(extra_headers)
    resp = obter_http_session().request(method, f"{url}/rest/v1/{tabela}", headers=headers, params=params, json=json_data, timeout=8)
    if not resp.ok:
        detalhe = ""
        try:
            err = resp.json()
            cod = err.get("code") or ""
            msg = err.get("message") or err.get("error") or ""
            detalhe = f"[{cod}] {msg}".strip() if cod else msg
        except Exception:
            detalhe = f"HTTP {resp.status_code}"
        if resp.status_code in (401, 403):
            raise RuntimeError(f"Chave do Supabase recusada (HTTP {resp.status_code}). Use a Secret key (sb_secret_...) ou service_role nos Secrets. {detalhe}")
        if resp.status_code == 404 or "PGRST205" in detalhe:
            raise RuntimeError(f"Tabela '{tabela}' não encontrada no Supabase. Execute o Script SQL no SQL Editor do Supabase. ({detalhe})")
        if "PGRST204" in detalhe or resp.status_code == 400:
            raise RuntimeError(f"Coluna ou regra faltando na tabela '{tabela}'. Execute o SQL de atualização no Supabase. ({detalhe})")
        raise RuntimeError(f"Erro no Supabase (HTTP {resp.status_code}): {detalhe}")
    return resp.json() if resp.text.strip() else None


def obter_usuarios_admin():
    admins = {"admin"}
    if env := ler_segredo("LISTAI_ADMINS"):
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
    if chave := ler_segredo("GEMINI_API_KEY"):
        return chave, "secrets"
    chave = st.session_state.get("gemini_api_key_usuario", "").strip()
    return (chave or None), ("perfil" if chave else "")


@st.cache_resource
def obter_gemini_client(api_key):
    from google import genai
    return genai.Client(api_key=api_key)


# --- Utilitários Gerais e Imagens ---
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


def formatar_reais(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_delta_reais(valor):
    return f"{'+' if valor >= 0 else '-'}{formatar_reais(abs(valor))}"


def formatar_distancia(metros):
    if metros is None:
        return ""
    m = int(metros)
    return f"{m} m" if m < 1000 else f"{m / 1000:.1f} km".replace(".", ",")


def obter_iniciais(nome):
    p = [x for x in str(nome or "").strip().split() if x]
    return "US" if not p else (p[0][:2].upper() if len(p) == 1 else (p[0][0] + p[-1][0]).upper())


def mascarar_email(email):
    e = str(email or "").strip()
    if "@" not in e:
        return "***"
    local, dom = e.split("@", 1)
    return f"{local[:2] if len(local) > 2 else local[:1]}***@{dom}"


def mascarar_telefone(tel):
    dig = re.sub(r"\D", "", str(tel or ""))
    return f"***-{dig[-4:]}" if len(dig) >= 4 else "***"


def fmt_qtd(v):
    return int(v) if float(v).is_integer() else v


def fmt_dt(dt):
    return dt.strftime("%d/%m/%Y") if pd.notna(dt) else "Sem data"


def rolar_para_topo():
    components.html(
        "<script>setTimeout(()=>{const d=window.parent.document,m=d.querySelector('[data-testid=\"stMain\"]')||d.querySelector('section.main');if(m)m.scrollTo({top:0,behavior:'smooth'});window.parent.scrollTo({top:0,behavior:'smooth'});},30);</script>",
        height=0,
    )


def rerun_fragmento():
    try:
        st.rerun(scope="fragment")
    except TypeError:
        st.rerun()


def limpar_estado_editor_foto():
    for k_ed in CHAVES_EDITOR_FOTO:
        st.session_state.pop(k_ed, None)


def limpar_estado_usuario(incluir_auth=False):
    chaves = {
        "aviso_voz", "aviso_voz_erro", "ultimo_audio_hash", "ultimo_cupom_hash", "itens_foto_lidos",
        "msg_sucesso", "msg_foto_erro", "msg_limite_alerta", "gps_ultima_leitura", "gps_coords",
        "gps_regiao", "gps_mercados", "gps_detalhes", "gps_raio_atual", "gps_usuario_owner",
        "sel_reg_compra", "sel_merc_compra", "regiao_para_selecionar", "merc_para_selecionar",
        "input_nova_regiao", "res_manual", "ultima_foto_hash", "foto_versao", "edit_compra_idx",
        "edit_hist_idx", "valor_categoria", "compra_ativa", "compra_sessao_ids",
        "mkt_limite_exib", "db_limite_mercs", "leitor_pix_modo",
        "_ss_perfil", "_ss_perfil_owner", "_ss_compras_df", "_ss_compras_proc",
        "_ss_compras_owner", "_ss_compras_ver", "_ss_compras_proc_ver",
        "_ss_pre_lista_df", "_ss_pre_lista_owner", "_ss_foto_b64", "_ss_foto_owner",
        *CHAVES_EDITOR_FOTO,
    }
    if incluir_auth:
        st.session_state.update({"autenticado": False, "usuario_logado": ""})
        chaves.update({"modo_login", "rec_usuario", "msg_login_ok", "gemini_api_key_usuario", "pagina_atual", "pagina_anterior"})
    for k in list(st.session_state.keys()):
        if k.startswith(("num_lim_", "chk_bloq_", "up_foto_", "audio_zap_", "up_cupom_", "cam_cupom_", "chk_foto_item_", "nfce_in_")) or k in chaves:
            st.session_state.pop(k, None)


def preparar_imagem_base(raw_bytes, max_lado=640, quality=86, melhorar_contraste=False):
    if len(raw_bytes) > MAX_FOTO_BYTES:
        raise ValueError("Imagem muito grande (máximo 8 MB).")
    try:
        from PIL import Image, ImageFile, ImageOps
        Image.MAX_IMAGE_PIXELS = 25_000_000
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass

        with Image.open(io.BytesIO(raw_bytes)) as img_aberta:
            if getattr(img_aberta, "format", "") == "JPEG":
                try:
                    img_aberta.draft("RGB", (max_lado, max_lado))
                except Exception:
                    pass
            img_aberta.load()
            try:
                img = ImageOps.exif_transpose(img_aberta)
            except Exception:
                img = img_aberta.copy()

            if img.mode in ("RGBA", "LA", "PA", "RGBa") or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")
                fundo = Image.new("RGB", rgba.size, (255, 255, 255))
                fundo.paste(rgba, mask=rgba.split()[-1])
                img = fundo
            elif img.mode != "RGB":
                img = img.convert("RGB")

            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
            img.thumbnail((max_lado, max_lado), resample)
            if melhorar_contraste:
                try:
                    img = ImageOps.autocontrast(img, cutoff=1)
                except Exception:
                    pass
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()
    except ImportError:
        return None
    except Exception:
        raise ValueError("Não foi possível abrir essa foto. Tente outra imagem (JPG, PNG ou WEBP).")


@st.cache_data(show_spinner=False, max_entries=6)
def gerar_foto_ajustada(orig_bytes, modo="Preencher", zoom=1.0, pos_x=0, pos_y=0, rotacao=0):
    from PIL import Image, ImageFilter
    with Image.open(io.BytesIO(orig_bytes)) as im:
        img = im.convert("RGB")
    if rotacao:
        img = img.rotate(-int(rotacao), expand=True)
    resample = getattr(getattr(Image, "Resampling", Image), "BILINEAR", Image.BICUBIC)

    if modo == "Encaixar inteira":
        lado = min(img.size)
        l, t = (img.width - lado) // 2, (img.height - lado) // 2
        fundo = img.crop((l, t, l + lado, t + lado)).resize((64, 64), resample).filter(ImageFilter.GaussianBlur(4)).resize((200, 200), resample)
        frente = img.copy()
        frente.thumbnail((200, 200), resample)
        fundo.paste(frente, ((200 - frente.width) // 2, (200 - frente.height) // 2))
        final = fundo
    else:
        lado_base = min(img.size)
        lado = max(32, int(lado_base / max(1.0, float(zoom))))
        max_dx, max_dy = max(0, (img.width - lado) // 2), max(0, (img.height - lado) // 2)
        cx = img.width // 2 + int((pos_x / 100.0) * max_dx)
        cy = img.height // 2 + int((pos_y / 100.0) * max_dy)
        l = max(0, min(img.width - lado, cx - lado // 2))
        t = max(0, min(img.height - lado, cy - lado // 2))
        final = img.crop((l, t, l + lado, t + lado)).resize((200, 200), resample)

    buf = io.BytesIO()
    final.save(buf, format="JPEG", quality=84)
    return buf.getvalue()

