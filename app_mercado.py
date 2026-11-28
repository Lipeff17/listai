import base64
from datetime import date
import hashlib
import html
import os
import re
import urllib.parse

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

st.set_page_config(page_title="Listaí — Preços e Compras", page_icon="🛒", layout="wide", initial_sidebar_state="collapsed")

from config import (
    ANUNCIOS_PADRAO,
    COLUNAS,
    COLUNAS_COMUNIDADE,
    ESTILO_CSS,
    EXTENSOES_FOTO,
    ICONES_CATEGORIA,
    LISTA_CATEGORIAS,
    LOGO_SVG,
    NAV_ITENS,
    PAGINAS,
    PAGINA_PERFIL,
    PERGUNTAS_SEGURANCA,
    RAIO_LABELS,
    RAIO_OPCOES,
    fmt_dt,
    fmt_qtd,
    formatar_delta_reais,
    formatar_distancia,
    formatar_reais,
    gerar_foto_ajustada,
    ler_segredo,
    limpar_estado_editor_foto,
    limpar_estado_usuario,
    mascarar_email,
    mascarar_telefone,
    normalizar_texto,
    obter_api_key_gemini,
    obter_arquivo_usuario,
    obter_iniciais,
    obter_usuarios_admin,
    preparar_imagem_base,
    rerun_fragmento,
    rolar_para_topo,
    supabase_ativo,
)
from dados import (
    adicionar_itens_pre_lista,
    atualizar_campos_perfil,
    atualizar_compra_usuario,
    atualizar_item_pre_lista,
    buscar_supermercados_por_regiao,
    buscar_usuario_unico,
    calcular_ranking_precos_mercados,
    carregar_anuncios_cadastrados,
    carregar_comunidade_ordenada,
    carregar_foto_original_bytes,
    carregar_foto_perfil_base64,
    carregar_mercados,
    carregar_orcamento_mensal,
    carregar_pre_lista,
    carregar_preferencias_gps,
    classificar_selo_preco,
    comparar_lista_nos_mercados,
    consultar_overpass_mercados,
    copiar_itens_para_familia,
    definir_grupo_lista,
    excluir_compras_usuario,
    gerar_codigo_familia,
    gerar_hash_senha,
    limpar_comunidade,
    listar_usuarios_admin,
    montar_lista_mercados_classificada,
    obter_compras_com_datas,
    obter_dono_lista,
    obter_gasto_mes_atual,
    obter_grupo_lista_atual,
    obter_perfil_atual,
    processar_leitura_gps,
    registrar_varios_mercados,
    remover_anuncio_admin,
    remover_foto_perfil,
    remover_pre_lista,
    resumir_mercados,
    salvar_anuncio_admin,
    salvar_compra_usuario,
    salvar_foto_perfil_final,
    salvar_orcamento_mensal,
    salvar_preco_comunidade,
    salvar_preferencias_gps,
    salvar_usuario_unico,
    selecionar_anuncio_inteligente,
    validar_codigo_familia,
    verificar_senha,
)
from ia_leitor import (
    identificar_categoria,
    reconhecer_produto_por_voz,
    renderizar_leitor_pix,
)

st.markdown(ESTILO_CSS, unsafe_allow_html=True)
_st_fragment = getattr(st, "fragment", lambda f: f)


# --- Tutorial & Tela de Login / Cadastro / Recuperação ---
def renderizar_tutorial_app(expandido=False):
    with st.expander("❓ Como usar o Listaí (Tutorial rápido)", expanded=expandido):
        st.markdown(
            """
* **🛒 Compra:** escolha o mercado, toque em **Iniciar Compra** e lance itens **digitando**, falando no **microfone 🎤** ou usando o **📷 Leitor estilo Pix** *(código de barras, etiqueta, cupom fiscal ou link NFC-e)*.
* **📝 Lista & 👨‍👩‍👧‍👦 Família:** anote o que falta, divida a lista usando o código `CASA-XXXXXX` e descubra **onde sua lista sai mais barata hoje**.
* **🏆 Preços & 🗺️ Mercados:** ative o **GPS** ou busque sua cidade para ver os mercados do **mais barato ao mais caro** e comparar ofertas.
* **📊 Gráficos, 🧾 Histórico & 🎯 Limite:** controle seu orçamento mensal, veja onde gasta mais e exporte suas compras em CSV.
* **👤 Perfil:** troque sua foto, salve lembrete/pergunta secreta para recuperar a senha, ajuste o GPS e a chave de IA.
            """.strip()
        )


def exibir_tela_login():
    st.session_state.setdefault("modo_login", "entrar")
    _, col_c, _ = st.columns([1, 1.8, 1])
    with col_c:
        st.markdown(
            f'<div class="listai-header"><div class="listai-header-top"><div class="listai-brand">{LOGO_SVG}<h1>Listaí</h1></div>'
            '<span class="listai-pill">PREÇOS E COMPRAS</span></div><p>Sua lista inteligente e os melhores preços da região.</p></div>',
            unsafe_allow_html=True,
        )
        st.info("ℹ️ **Versão Beta gratuita:** o app é gratuito nos primeiros meses e poderá ter cobrança futura (você será avisado antes).")
        with st.container(border=True):
            modo = st.session_state["modo_login"]
            if modo == "entrar":
                st.subheader("🔐 Entrar")
                if msg_ok := st.session_state.pop("msg_login_ok", None):
                    st.success(msg_ok)
                with st.form("form_login", border=False):
                    u_in = st.text_input("Usuário", placeholder="Seu usuário")
                    s_in = st.text_input("Senha", type="password", placeholder="Sua senha")
                    if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                        u = u_in.strip().lower()
                        try:
                            reg = buscar_usuario_unico(u, colunas="usuario,senha_hash,nome")
                        except Exception as erro_sb:
                            st.error(f"⚠️ {erro_sb}")
                            reg = False
                        if reg is False:
                            pass
                        elif reg is not None and verificar_senha(s_in, reg.get("hash", "")):
                            st.session_state.update({"autenticado": True, "usuario_logado": u, "nome_usuario": reg.get("nome", u)})
                            st.session_state.pop("modo_login", None)
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")

                with st.container(key="kpi_2cols_login"):
                    c_esq, c_cad = st.columns(2)
                    if c_esq.button("🔑 Esqueci a senha", use_container_width=True):
                        st.session_state.pop("rec_usuario", None)
                        st.session_state["modo_login"] = "recuperar"
                        st.rerun()
                    if c_cad.button("📝 Criar conta", use_container_width=True):
                        st.session_state["modo_login"] = "cadastro"
                        st.rerun()

            elif modo == "recuperar":
                st.subheader("🔑 Lembrar / Recuperar Senha")
                with st.form("form_buscar_rec", border=False):
                    rec_in = st.text_input("Digite seu usuário", value=st.session_state.get("rec_usuario", ""), placeholder="Ex: maria")
                    if st.form_submit_button("🔍 Buscar conta", use_container_width=True):
                        if not (u_limpo := rec_in.strip().lower()):
                            st.warning("Informe seu usuário.")
                        else:
                            st.session_state["rec_usuario"] = u_limpo
                            st.rerun()

                if rec_u := st.session_state.get("rec_usuario"):
                    try:
                        reg = buscar_usuario_unico(rec_u, colunas="usuario,senha_hash,nome,email,telefone,lembrete,pergunta_seg,resposta_seg_hash")
                    except Exception as erro_sb:
                        st.error(f"⚠️ {erro_sb}")
                        reg = False
                    if reg is False:
                        pass
                    elif reg is None:
                        st.error(f"Usuário **@{html.escape(rec_u)}** não encontrado.")
                    else:
                        if lembrete := str(reg.get("lembrete", "")).strip():
                            st.info(f"💡 **Lembrete da sua senha:** {lembrete}")
                        else:
                            st.caption("Esta conta não tem um lembrete de senha salvo.")

                        tel_limpo = re.sub(r"\D", "", str(reg.get("telefone", "")))
                        metodos = [m for cond, m in [
                            (bool(reg.get("pergunta_seg") and reg.get("resposta_seg_hash")), "Pergunta secreta"),
                            (bool(str(reg.get("email", "")).strip()), "E-mail cadastrado"),
                            (len(tel_limpo) >= 8, "WhatsApp cadastrado"),
                        ] if cond]

                        if not metodos:
                            st.warning("Esta conta não possui pergunta secreta, e-mail ou WhatsApp cadastrados.")
                        else:
                            st.divider()
                            st.markdown("**🔄 Não lembrou? Redefina sua senha:**")
                            metodo = st.radio("Confirmar usando:", metodos, horizontal=True, key="rec_metodo_verif") if len(metodos) > 1 else metodos[0]
                            with st.form("form_redefinir_senha", border=False):
                                if metodo == "Pergunta secreta":
                                    st.markdown(f"❓ **{html.escape(reg['pergunta_seg'])}**")
                                    verif_in = st.text_input("Sua resposta secreta")
                                elif metodo == "E-mail cadastrado":
                                    verif_in = st.text_input(f"Confirme o e-mail ({mascarar_email(reg['email'])})")
                                else:
                                    verif_in = st.text_input(f"Confirme o WhatsApp ({mascarar_telefone(reg['telefone'])})")

                                ns1, ns2 = st.columns(2)
                                nova_s = ns1.text_input("Nova senha *", type="password", placeholder="Mín. 4 caracteres")
                                conf_s = ns2.text_input("Confirmar senha *", type="password")
                                if st.form_submit_button("✅ Salvar nova senha", type="primary", use_container_width=True):
                                    ok_v = (
                                        verificar_senha(normalizar_texto(verif_in), reg["resposta_seg_hash"]) if metodo == "Pergunta secreta"
                                        else (verif_in.strip().lower() == str(reg.get("email", "")).strip().lower() if metodo == "E-mail cadastrado"
                                              else re.sub(r"\D", "", verif_in) == tel_limpo)
                                    )
                                    if not ok_v:
                                        st.error("Os dados de confirmação não conferem.")
                                    elif len(nova_s) < 4:
                                        st.warning("Mínimo 4 caracteres.")
                                    elif nova_s != conf_s:
                                        st.error("As senhas não coincidem.")
                                    else:
                                        try:
                                            atualizar_campos_perfil(rec_u, senha_hash=gerar_hash_senha(nova_s))
                                            st.session_state.pop("rec_usuario", None)
                                            st.session_state.update({"modo_login": "entrar", "msg_login_ok": f"Senha de **{rec_u}** redefinida! Já pode entrar."})
                                            st.rerun()
                                        except Exception as erro_sb:
                                            st.error(f"⚠️ {erro_sb}")

                st.divider()
                if st.button("← Voltar para Entrar", use_container_width=True):
                    st.session_state.pop("rec_usuario", None)
                    st.session_state["modo_login"] = "entrar"
                    st.rerun()

            else:
                st.subheader("📝 Criar Conta")
                with st.form("form_cadastro", border=False):
                    nome_p = st.text_input("Nome completo *", placeholder="Ex: Maria Silva")
                    c1, c2 = st.columns(2)
                    email_p = c1.text_input("E-mail (opcional)", placeholder="maria@email.com")
                    tel_p = c2.text_input("WhatsApp (opcional)", placeholder="(11) 99999-9999")
                    cid_p = st.text_input("Cidade / Bairro (opcional)", placeholder="Ex: Belém - Nazaré")
                    a1, a2 = st.columns(2)
                    novo_u = a1.text_input("Usuário *", placeholder="Ex: maria")
                    nova_s = a2.text_input("Senha *", type="password", placeholder="Mín. 4 caracteres")
                    st.caption("💡 **Para lembrar ou recuperar sua senha caso esqueça:**")
                    lemb_p = st.text_input("Lembrete / dica da senha (opcional)", placeholder="Ex: Nome do pet + ano")
                    s1, s2 = st.columns(2)
                    perg_p = s1.selectbox("Pergunta secreta (opcional)", PERGUNTAS_SEGURANCA)
                    resp_p = s2.text_input("Resposta secreta (opcional)", placeholder="Ex: Rex")

                    if st.form_submit_button("✅ Criar conta e entrar", type="primary", use_container_width=True):
                        nome_ok = nome_p.strip()
                        nl = re.sub(r"[^a-z0-9._-]", "", novo_u.strip().lower())
                        if len(nome_ok) < 2:
                            st.warning("Digite seu nome completo.")
                        elif len(nl) < 2 or nl != novo_u.strip().lower():
                            st.warning("Usuário deve ter pelo menos 2 caracteres (letras, números, . _ -).")
                        elif len(nova_s) < 4:
                            st.warning("Senha deve ter pelo menos 4 caracteres.")
                        else:
                            try:
                                if buscar_usuario_unico(nl, colunas="usuario") is not None:
                                    st.error("Esse usuário já existe. Escolha outro.")
                                else:
                                    novo_reg = {"tipo": "senha", "hash": gerar_hash_senha(nova_s), "nome": nome_ok, "email": email_p.strip(), "telefone": tel_p.strip(), "cidade": cid_p.strip(), "lembrete": lemb_p.strip(), "criado_em": date.today().isoformat()}
                                    if resp_p.strip():
                                        novo_reg.update({"pergunta_seg": perg_p, "resposta_seg_hash": gerar_hash_senha(normalizar_texto(resp_p))})
                                    salvar_usuario_unico(nl, novo_reg)
                                    st.session_state.update({"autenticado": True, "usuario_logado": nl, "nome_usuario": nome_ok, "msg_sucesso": f"Conta criada! Bem-vindo(a), **{nome_ok}**."})
                                    st.session_state.pop("modo_login", None)
                                    st.rerun()
                            except Exception as erro_sb:
                                st.error(f"⚠️ {erro_sb}")
                st.divider()
                if st.button("← Já tenho conta (Voltar)", use_container_width=True):
                    st.session_state["modo_login"] = "entrar"
                    st.rerun()

        renderizar_tutorial_app()


if not st.session_state.get("autenticado", False):
    exibir_tela_login()
    st.stop()


# --- Componentes Compartilhados ---
def avatar_html(nome, usuario, tamanho=48, solido=False):
    if foto := carregar_foto_perfil_base64(usuario):
        borda = "border: 2px solid #FCA5A5;" if solido else ""
        return f'<img src="data:{foto[1]};base64,{foto[0]}" class="listai-avatar-img" style="width:{tamanho}px;height:{tamanho}px;{borda}" alt="Foto">'
    classe = "listai-avatar-solid" if solido else "listai-avatar"
    return f'<div class="{classe}" style="width:{tamanho}px;height:{tamanho}px;font-size:{max(14, int(tamanho * 0.36))}px;">{html.escape(obter_iniciais(nome))}</div>'


def exibir_banner_anuncio_topo():
    script_secret = ler_segredo("AD_BANNER_HTML")
    cadastrados, _ = carregar_anuncios_cadastrados()
    script_ad = next((a["script_html"] for a in cadastrados if a.get("script_html")), "")
    tag_cpm = script_secret or script_ad

    if tag_cpm:
        components.html(f"<div style='margin:0;padding:0;display:flex;justify-content:center;align-items:center;overflow:hidden;'>{tag_cpm}</div>", height=90, scrolling=False)
        return

    pool = [a for a in cadastrados if str(a.get("url", "")).startswith("https://")] or ANUNCIOS_PADRAO
    cards_html = []
    for ad in pool[:8]:
        url = html.escape(ad["url"])
        disc = ad.get("desconto") or ("OFERTA" if not ad.get("cupom") else ad["cupom"][:8])
        img_u, tit_c = ad.get("imagem_url", ""), html.escape(ad["titulo"])
        corpo = f'<img src="{html.escape(img_u)}" alt="{tit_c}" loading="lazy">' if img_u.startswith("https://") else f'<div class="listai-top-ad-fallback">{tit_c}</div>'
        cards_html.append(f'<a class="listai-top-ad-card" href="{url}" target="_blank" rel="noopener noreferrer" title="{tit_c}"><span class="listai-top-ad-disc">{html.escape(disc)}</span>{corpo}</a>')

    destaque = pool[0]
    cards_html.append(
        f'<a class="listai-top-ad-store" href="{html.escape(destaque["url"])}" target="_blank" rel="noopener noreferrer">'
        f'<span class="listai-top-ad-info">ⓘ</span><div class="listai-top-ad-store-name">{html.escape((destaque.get("texto_botao") or "Ofertas")[:16])}</div>'
        '<div class="listai-top-ad-store-cta">Abrir ↗</div></a>'
    )
    st.markdown(f'<div class="listai-top-ad-wrap"><div class="listai-top-ad-strip">{"".join(cards_html)}</div></div>', unsafe_allow_html=True)


def exibir_rodape_anuncio(gps_regiao):
    ad, motivo = selecionar_anuncio_inteligente(gps_regiao, st.session_state.get("pagina_atual", ""))
    url = ad["url"] if str(ad["url"]).startswith("https://") else "https://"
    cupom_html = f'<span class="listai-ad-cupom">🏷️ Cupom: {html.escape(ad["cupom"])}</span>' if ad.get("cupom") else ""
    with st.container(border=True):
        c1, c2 = st.columns([4, 1], vertical_alignment="center")
        c1.markdown(
            f'<span class="listai-ad-badge">{html.escape(motivo)}</span>'
            f'<strong>{html.escape(ad["titulo"])}</strong> — {html.escape(ad["descricao"])}{cupom_html}',
            unsafe_allow_html=True,
        )
        c2.link_button(ad["texto_botao"], url, use_container_width=True)


def renderizar_topo_nubank(nome_usuario, usuario_atual, gps_regiao):
    p_nome = nome_usuario.strip().split()[0] if nome_usuario.strip() else usuario_atual
    sub_reg = f"📍 {gps_regiao}" if gps_regiao else "Lista inteligente e menor preço"
    no_perfil = st.session_state["pagina_atual"] == PAGINA_PERFIL

    with st.container(key="topo_nubank"):
        c_user, c_btn = st.columns([5, 1])
        c_user.markdown(
            f'<div class="listai-nu-user">{avatar_html(nome_usuario, usuario_atual, 44)}'
            f'<div class="listai-nu-texts"><div class="listai-nu-brand">Listaí • Pará</div>'
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


def renderizar_barra_navegacao():
    with st.container(key="barra_navegacao"):
        for idx, (col, (ico, txt), pag) in enumerate(zip(st.columns(len(NAV_ITENS), gap="small"), NAV_ITENS, PAGINAS)):
            ativo = st.session_state["pagina_atual"] == pag
            if col.button(f"{ico}\n{txt}", key=f"top_nav_{idx}", type="primary" if ativo else "secondary", use_container_width=True) and not ativo:
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
        with st.expander("🎯 Definir limite mensal (opcional)", expanded=expandir_config):
            renderizar_config_orcamento(usuario, pref)
        return
    gasto = obter_gasto_mes_atual(usuario, date.today().strftime("%Y-%m")) if gasto_mes is None else gasto_mes
    pct, rest = gasto / limite, limite - gasto
    with st.container(border=True):
        if rest < 0:
            st.error(f"🚨 **Limite ultrapassado!** {formatar_reais(gasto)} de {formatar_reais(limite)} (+{formatar_reais(abs(rest))}).")
        elif pct >= 0.80:
            st.warning(f"⚠️ **Limite ({int(pct * 100)}%):** {formatar_reais(gasto)} / {formatar_reais(limite)} · Resta {formatar_reais(rest)}.")
        else:
            st.success(f"🎯 **Limite ({int(pct * 100)}%):** {formatar_reais(gasto)} / {formatar_reais(limite)} · Resta {formatar_reais(rest)}.")
        st.progress(min(pct, 1.0))
        with st.expander("⚙️ Alterar limite mensal", expanded=expandir_config):
            renderizar_config_orcamento(usuario, pref)


def renderizar_editor_compra(df_c, idx_edit, state_key, usuario):
    if idx_edit not in df_c.index:
        st.session_state.pop(state_key, None)
        return
    r = df_c.loc[idx_edit]
    dt_p = pd.to_datetime(r.get("Data"), errors="coerce")
    cat_at = str(r.get("Categoria") or "Outros")
    with st.form(f"form_edit_{state_key}_{idx_edit}", border=True):
        st.markdown(f"**✏️ Editando:** {html.escape(str(r.get('Produto', '')))}")
        e_prod = st.text_input("Produto", value=str(r.get("Produto", "")))
        with st.container(key=f"edit_qp_{state_key}"):
            cq, cp = st.columns(2)
            e_qtd = cq.number_input("Qtd", min_value=1, value=max(1, int(float(r.get("Quantidade", 1) or 1))), step=1)
            e_preco = cp.number_input("Preço (R$)", min_value=0.01, value=max(0.01, float(r.get("Preço Unitário", 1.0) or 1.0)), step=0.01, format="%.2f")
        e_cat = st.selectbox("Categoria", LISTA_CATEGORIAS, index=LISTA_CATEGORIAS.index(cat_at) if cat_at in LISTA_CATEGORIAS else LISTA_CATEGORIAS.index("Outros"))
        e_merc = st.text_input("Supermercado", value=str(r.get("Supermercado", "")))
        e_dt = st.date_input("Data", value=dt_p.date() if pd.notna(dt_p) else date.today(), format="DD/MM/YYYY")

        with st.container(key=f"edit_btns_{state_key}"):
            b1, b2, b3 = st.columns(3)
            salvar = b1.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
            excluir = b2.form_submit_button("🗑️ Excluir", use_container_width=True)
            cancelar = b3.form_submit_button("✖️ Fechar", use_container_width=True)

        if salvar:
            if not (p_ok := e_prod.strip()):
                st.warning("Informe o nome do produto.")
            else:
                atualizar_compra_usuario(usuario, idx_edit, e_dt.isoformat(), e_merc.strip() or "Não informado", p_ok, e_cat, e_qtd, e_preco)
                st.session_state.pop(state_key, None)
                st.session_state["msg_sucesso"] = f"'{p_ok}' atualizado ({e_cat})!"
                st.rerun()
        elif excluir:
            excluir_compras_usuario(usuario, ids=[idx_edit])
            st.session_state.pop(state_key, None)
            st.session_state["msg_sucesso"] = "Item excluído da compra."
            st.rerun()
        elif cancelar:
            st.session_state.pop(state_key, None)
            st.rerun()


def renderizar_itens_compra_ativa(df_c, usuario, merc_atual, data_atual):
    sess_ids = [i for i in st.session_state.get("compra_sessao_ids", []) if i in df_c.index]
    st.session_state["compra_sessao_ids"] = sess_ids
    sub_df = df_c.loc[sess_ids].iloc[::-1] if sess_ids else pd.DataFrame(columns=COLUNAS)
    tot_atual = float(sub_df["Total"].sum()) if not sub_df.empty else 0.0
    qtd_atual = len(sub_df)
    merc_exib = merc_atual.strip() or "Supermercado"

    with st.container(border=True):
        st.markdown(
            f'<div class="listai-compra-banner"><div><div class="listai-compra-eyebrow">🛒 Compra em Andamento</div>'
            f'<div class="listai-compra-merc">🏪 {html.escape(merc_exib)}</div>'
            f'<div class="listai-compra-data">📅 {data_atual.strftime("%d/%m/%Y")} • {qtd_atual} {"item" if qtd_atual == 1 else "itens"} no carrinho</div></div>'
            f'<div class="listai-compra-total-box"><div class="listai-compra-total-lbl">Total desta compra</div>'
            f'<div class="listai-compra-total-val">{formatar_reais(tot_atual)}</div></div></div>',
            unsafe_allow_html=True,
        )

        if (edit_idx := st.session_state.get("edit_compra_idx")) is not None:
            renderizar_editor_compra(df_c, edit_idx, "edit_compra_idx", usuario)

        if sub_df.empty:
            st.caption("Nenhum produto adicionado ainda nesta compra. Use o formulário acima!")
        else:
            with st.container(key="compra_grp_ativa"):
                for idx_r, rr in sub_df.iterrows():
                    cat_r = str(rr.get("Categoria") or "Outros")
                    ico_r = ICONES_CATEGORIA.get(cat_r, "📦")
                    c_info, c_ed = st.columns([6, 1])
                    c_info.markdown(
                        f'<div class="listai-rec-row"><div class="listai-rec-nome">{ico_r} {html.escape(str(rr["Produto"]))} (x{fmt_qtd(rr.get("Quantidade", 1))}) — {formatar_reais(float(rr.get("Total", 0.0)))}</div>'
                        f'<div class="listai-rec-meta">{html.escape(cat_r)} · {formatar_reais(float(rr.get("Preço Unitário", 0.0)))}/un</div></div>',
                        unsafe_allow_html=True,
                    )
                    if c_ed.button("✏️", key=f"btn_ed_ini_{idx_r}", help="Editar ou excluir", use_container_width=True):
                        st.session_state["edit_compra_idx"] = idx_r
                        st.rerun()

        st.divider()
        lbl_fin = "✅ Finalizar Compra" if qtd_atual > 0 else "✖️ Sair da Compra"
        if st.button(lbl_fin, type="primary" if qtd_atual > 0 else "secondary", use_container_width=True, key="btn_finalizar_compra"):
            st.session_state.update({
                "compra_ativa": False, "compra_sessao_ids": [], "valor_produto": "",
                "valor_quantidade": 1, "valor_preco": 1.00, "valor_categoria": "✨ Automática", "valor_supermercado": "",
            })
            st.session_state.pop("edit_compra_idx", None)
            st.session_state.pop("aviso_voz", None)
            st.session_state.pop("aviso_barcode", None)
            st.session_state.pop("itens_foto_lidos", None)
            st.session_state.pop("ultimo_cupom_hash", None)
            if qtd_atual > 0:
                st.session_state["msg_sucesso"] = f"Compra finalizada em **{merc_exib}**! {qtd_atual} {'item' if qtd_atual == 1 else 'itens'} • Total: **{formatar_reais(tot_atual)}** (salva no Histórico)."
            else:
                st.session_state["msg_sucesso"] = "Compra encerrada."
            st.rerun()


def renderizar_tabela_banco_precos(df_rows, min_por_prod, contar_merc_prod, mostrar_mercado=False):
    linhas_html = []
    for row in df_rows.to_dict("records"):
        prod = html.escape(str(row.get("Produto", "")))
        cat_r = str(row.get("Categoria") or "Outros")
        ico_r, dt_r = ICONES_CATEGORIA.get(cat_r, "📦"), fmt_dt(row.get("Data_dt"))
        p_u, p_norm = float(row.get("Preço Unitário", 0.0)), row.get("Prod_norm", "")
        p_min, qtd_m = float(min_por_prod.get(p_norm, p_u)), int(contar_merc_prod.get(p_norm, 1))
        diff = p_u - p_min

        if qtd_m <= 1:
            st_html, prc_cls = '<span class="listai-st-only">Único</span>', "listai-db-price"
        elif diff <= 0.01:
            st_html, prc_cls = '<span class="listai-st-best">🏆 Menor</span>', "listai-db-price listai-db-price-best"
        else:
            st_html, prc_cls = f'<span class="listai-st-up">+{formatar_reais(diff)}</span>', "listai-db-price"

        meta_itens = [f"{ico_r} {html.escape(cat_r)}", f"📅 {dt_r}"]
        if mostrar_mercado:
            meta_itens.insert(0, f"🏪 <strong>{html.escape(str(row.get('Supermercado') or 'Mercado'))}</strong> ({html.escape(str(row.get('Região') or '-'))})")

        linhas_html.append(
            f'<tr><td><div class="listai-db-prod">{prod}</div><div class="listai-db-meta">{" · ".join(meta_itens)}</div></td>'
            f'<td class="{prc_cls}">{formatar_reais(p_u)}</td><td class="listai-db-status">{st_html}</td></tr>'
        )

    st.markdown(
        '<div class="listai-db-wrap"><table class="listai-db-table">'
        '<thead><tr><th>Produto</th><th class="num">Preço</th><th class="num">Status</th></tr></thead>'
        f'<tbody>{"".join(linhas_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


@_st_fragment
def renderizar_editor_foto_perfil(usuario, rascunho):
    with st.container(border=True):
        st.markdown("#### ✂️ Ajustar Foto do Perfil")
        modo_f = st.radio("Como encaixar:", ["🔍 Preencher círculo", "🖼️ Caber inteira"], horizontal=True, key="foto_ed_modo")
        if modo_f == "🔍 Preencher círculo":
            zoom_f = st.slider("🔎 Zoom", 1.0, 2.5, 1.0, 0.1, key="foto_ed_zoom")
            with st.container(key="foto_pos_row"):
                c_px, c_py = st.columns(2)
                pos_x = c_px.slider("⬅️ ➡️ Lado", -100, 100, 0, 5, key="foto_ed_px")
                pos_y = c_py.slider("⬆️ ⬇️ Altura", -100, 100, 0, 5, key="foto_ed_py")
        else:
            zoom_f, pos_x, pos_y = 1.0, 0, 0
        rot_f = st.radio("🔄 Girar:", [0, 90, 180, 270], horizontal=True, format_func=lambda g: f"{g}°", key="foto_ed_rot")

        prev_bytes = gerar_foto_ajustada(rascunho, modo=("Encaixar inteira" if modo_f == "🖼️ Caber inteira" else "Preencher"), zoom=zoom_f, pos_x=pos_x, pos_y=pos_y, rotacao=rot_f)
        prev_b64 = base64.b64encode(prev_bytes).decode("ascii")
        st.markdown(f'<div class="listai-foto-preview"><img src="data:image/jpeg;base64,{prev_b64}" alt="Prévia"></div>', unsafe_allow_html=True)

        with st.container(key="kpi_2cols_foto_ed"):
            s_col, c_col = st.columns(2)
            if s_col.button("✅ Salvar foto", type="primary", use_container_width=True, key="btn_salvar_foto_ed"):
                salvar_foto_perfil_final(usuario, rascunho, prev_bytes)
                limpar_estado_editor_foto()
                st.session_state["msg_sucesso"] = "Foto de perfil salva!"
                st.rerun()
            if c_col.button("✖️ Cancelar", use_container_width=True, key="btn_cancelar_foto_ed"):
                limpar_estado_editor_foto()
                st.rerun()


def _ao_alternar_item_lista(dono_lista, item_id, chk_key):
    atualizar_item_pre_lista(dono_lista, item_id, Comprado=bool(st.session_state.get(chk_key, False)))


@_st_fragment
def renderizar_bloco_lista_interativa(usuario_atual, api_key, gps_regiao):
    df_c, _ = obter_compras_com_datas(usuario_atual)
    cod_fam = obter_grupo_lista_atual(usuario_atual)
    dono_lista = obter_dono_lista(usuario_atual)
    versao = st.session_state["form_versao"]

    if cod_fam:
        with st.container(key="fam_bar"):
            c_fb, c_fs = st.columns([4, 1], vertical_alignment="center")
            c_fb.markdown(f'<div class="listai-fam-badge">👨‍👩‍👧‍👦 Lista da Família • Código: <span class="listai-fam-code">{html.escape(cod_fam)}</span></div>', unsafe_allow_html=True)
            if c_fs.button("🔄 Atualizar", key="btn_sync_fam", use_container_width=True, help="Buscar novidades da família"):
                st.session_state.pop("_ss_pre_lista_df", None)
                st.session_state.pop("_ss_pre_lista_owner", None)
                rerun_fragmento()

    with st.container(border=True):
        with st.container(key="add_lista_row"):
            c_in, c_bt = st.columns([5, 1], vertical_alignment="bottom")
            novo_item = c_in.text_input("Anotar na lista", placeholder="Ex: Arroz, Café, Leite...", key=f"in_lista_{st.session_state.get('lista_versao', 0)}", label_visibility="collapsed")
            if c_bt.button("➕", key="btn_add_lista", type="primary", use_container_width=True, help="Adicionar na lista"):
                if not novo_item.strip():
                    st.warning("Digite um item.")
                else:
                    adicionar_itens_pre_lista(novo_item, 1, api_key, dono_lista)
                    st.session_state["lista_versao"] = st.session_state.get("lista_versao", 0) + 1
                    rerun_fragmento()

        if not df_c.empty:
            with st.expander("⚡ Adicionar rápido dos itens mais comprados"):
                esc = st.multiselect("Escolha os itens:", df_c["Produto"].value_counts().head(8).index.tolist(), key="ms_mais_comprados")
                if st.button("Adicionar selecionados na lista", disabled=not esc, use_container_width=True):
                    adicionar_itens_pre_lista(", ".join(esc), 1, api_key, dono_lista)
                    rerun_fragmento()

        df_pre = carregar_pre_lista(dono_lista)
        if not df_pre.empty:
            tot_l, pegos = len(df_pre), int(df_pre["Comprado"].sum())
            st.progress(pegos / tot_l, text=f"✅ {pegos} de {tot_l} no carrinho ({int((pegos / tot_l) * 100)}%)")

            with st.container(key="lista_chk_box"):
                for _, row in df_pre.sort_values(by="Comprado", ascending=True).iterrows():
                    iid, nome_i, qtd_i, cat_i, pego = row["ID"], row["Produto"], int(row["Quantidade"]), row["Categoria"] or "Outros", bool(row["Comprado"])
                    ico_i = ICONES_CATEGORIA.get(cat_i, "📦")
                    c_chk, c_lnc, c_del = st.columns([6, 1, 1])
                    lbl = f"~~{ico_i} {nome_i} (x{qtd_i})~~" if pego else f"**{ico_i} {nome_i}** (x{qtd_i}) · *{cat_i}*"
                    c_chk.checkbox(lbl, value=pego, key=f"chk_pre_{iid}", on_change=_ao_alternar_item_lista, args=(dono_lista, iid, f"chk_pre_{iid}"))

                    if c_lnc.button("💰", key=f"btn_lancar_{iid}", help="Lançar preço em Compra", use_container_width=True):
                        atualizar_item_pre_lista(dono_lista, iid, Comprado=True)
                        st.session_state.pop("aviso_voz", None)
                        st.session_state.pop("aviso_barcode", None)
                        st.session_state.update({
                            "compra_ativa": True, "valor_produto": nome_i, "valor_quantidade": qtd_i,
                            "valor_categoria": cat_i if cat_i in LISTA_CATEGORIAS else "✨ Automática",
                            "form_versao": versao + 1, "pagina_atual": PAGINAS[0], "rolar_topo": True,
                        })
                        st.rerun()
                    if c_del.button("🗑️", key=f"btn_del_pre_{iid}", help="Remover", use_container_width=True):
                        remover_pre_lista(dono_lista, item_id=iid)
                        rerun_fragmento()

            df_pre = carregar_pre_lista(dono_lista)
            if not df_pre.empty:
                with st.expander("✏️ Ajustar item ou categoria da lista"):
                    ops_l = {idx: f"{r['Produto']} (x{int(r['Quantidade'])}) — {r['Categoria'] or 'Outros'}" for idx, r in df_pre.iterrows()}
                    idx_l = st.selectbox("Item da lista", list(ops_l.keys()), format_func=lambda i: ops_l[i], key="sel_aj_lista")
                    row_l = df_pre.loc[idx_l]
                    cat_l = row_l["Categoria"] if row_l["Categoria"] in LISTA_CATEGORIAS else "Outros"
                    with st.form("form_aj_lista", border=False):
                        aj_nome = st.text_input("Produto", value=str(row_l["Produto"]))
                        with st.container(key="edit_qp_lista"):
                            cq_l, cc_l = st.columns(2)
                            aj_qtd = cq_l.number_input("Qtd", min_value=1, value=max(1, int(row_l["Quantidade"])), step=1)
                            aj_cat = cc_l.selectbox("Categoria", LISTA_CATEGORIAS, index=LISTA_CATEGORIAS.index(cat_l))
                        if st.form_submit_button("💾 Atualizar item da lista", use_container_width=True) and aj_nome.strip():
                            atualizar_item_pre_lista(dono_lista, row_l["ID"], Produto=aj_nome.strip(), Quantidade=int(aj_qtd), Categoria=aj_cat)
                            rerun_fragmento()

                pegos_atual = int(df_pre["Comprado"].sum())
                with st.container(key="kpi_2cols_lista"):
                    a1, a2 = st.columns(2)
                    if a1.button("🧹 Limpar marcados", disabled=(pegos_atual == 0), use_container_width=True):
                        remover_pre_lista(dono_lista, apenas_marcados=True)
                        rerun_fragmento()
                    if a2.button("🗑️ Limpar lista", use_container_width=True):
                        remover_pre_lista(dono_lista, tudo=True)
                        rerun_fragmento()

                df_pend = df_pre[~df_pre["Comprado"]]
                if not df_pend.empty:
                    df_com = carregar_comunidade_ordenada()
                    res_comp, escopo = comparar_lista_nos_mercados(df_pend, df_com, gps_regiao)
                    if res_comp:
                        st.divider()
                        vencedor = res_comp[0]
                        comparaveis = [r for r in res_comp if r["qtd_enc"] == vencedor["qtd_enc"]]
                        econ = max(0.0, max((r["total"] for r in comparaveis), default=vencedor["total"]) - vencedor["total"])
                        eco_badge = f'<span class="listai-eco-pill">Economia de até {formatar_reais(econ)}</span>' if econ > 0.01 else ""

                        st.markdown(f"**🧠 Onde sua lista sai mais barata hoje** *({html.escape(escopo)})*")
                        st.markdown(
                            f'<div class="listai-winner-card"><div><h3>🏆 {html.escape(vencedor["mercado"])}</h3>'
                            f'<div>📦 <strong>{vencedor["qtd_enc"]} de {vencedor["qtd_total"]}</strong> itens encontrados · {html.escape(vencedor["regiao"])}</div>'
                            f'{eco_badge}</div><div class="listai-winner-price">{formatar_reais(vencedor["total"])}</div></div>',
                            unsafe_allow_html=True,
                        )

                        if st.button(f"🛒 Comprar em {vencedor['mercado']}", type="primary", use_container_width=True, key="btn_comprar_vencedor_lista"):
                            if vencedor["regiao"] and vencedor["regiao"] != "-":
                                registrar_varios_mercados(vencedor["regiao"], [vencedor["mercado"]])
                                st.session_state["regiao_para_selecionar"] = vencedor["regiao"]
                            st.session_state.update({"merc_para_selecionar": vencedor["mercado"], "compra_ativa": True, "compra_sessao_ids": [], "pagina_atual": PAGINAS[0], "rolar_topo": True})
                            st.rerun()

                        with st.expander(f"🔎 Comparar todos os mercados ({len(res_comp)})"):
                            for idx_c, r in enumerate(res_comp[:6]):
                                sel_ico = "🥇" if idx_c == 0 else ("🥈" if idx_c == 1 else ("🥉" if idx_c == 2 else "🏪"))
                                st.markdown(f"**{sel_ico} {html.escape(r['mercado'])}** — **{formatar_reais(r['total'])}** ({r['qtd_enc']}/{r['qtd_total']} itens)")
                                st.caption("✓ " + " · ".join(f"{it['item']} ({formatar_reais(it['preco'])})" for it in r["itens"]))
                                if r["faltando"]:
                                    st.caption(f"⚠️ Sem preço: {', '.join(r['faltando'])}")
        else:
            st.caption("Sua lista está vazia. Anote acima o que precisa comprar!")

        with st.expander("👨‍👩‍👧‍👦 Lista da Família (Compartilhada)", expanded=False):
            if cod_fam:
                st.success(f"Você está conectado à Lista da Família **`{cod_fam}`**.")
                zap_convite = f"🏠 Entre na nossa Lista de Compras no Listaí!\n\nCódigo: *{cod_fam}*\nAbra a aba 📝 Lista → 👨‍👩‍👧‍👦 Lista da Família e digite esse código."
                st.link_button("📲 Enviar código no WhatsApp", f"https://wa.me/?text={urllib.parse.quote(zap_convite)}", type="primary", use_container_width=True)
                if st.button("🚪 Voltar para minha lista pessoal", use_container_width=True, key="btn_sair_fam"):
                    try:
                        definir_grupo_lista(usuario_atual, "")
                        st.session_state["msg_sucesso"] = "Você voltou para sua lista pessoal."
                        st.rerun()
                    except Exception as e_fam:
                        st.warning(str(e_fam))
            else:
                st.caption("Divida a mesma lista em tempo real com outra pessoa da sua casa.")
                copiar_at = st.checkbox("Copiar meus itens pendentes para a nova lista da família", value=True, key="chk_copiar_fam")
                if st.button("🏠 Criar lista da família", type="primary", use_container_width=True, key="btn_criar_fam"):
                    novo_cod = gerar_codigo_familia()
                    try:
                        if copiar_at:
                            copiar_itens_para_familia(usuario_atual, f"fam:{novo_cod}")
                        definir_grupo_lista(usuario_atual, novo_cod)
                        st.session_state["msg_sucesso"] = f"Lista da Família criada! Código: **`{novo_cod}`**."
                        st.rerun()
                    except Exception as e_fam:
                        st.warning(str(e_fam))

                st.divider()
                with st.form("form_entrar_fam", border=False):
                    cod_in = st.text_input("Já tem um código?", placeholder="Ex: CASA-7K9P2M")
                    if st.form_submit_button("🔗 Entrar na lista da família", use_container_width=True):
                        if not (cod_ok := validar_codigo_familia(cod_in)):
                            st.warning("Código inválido. Use o formato `CASA-XXXXXX`.")
                        else:
                            try:
                                definir_grupo_lista(usuario_atual, cod_ok)
                                st.session_state["msg_sucesso"] = f"Conectado à lista da família **`{cod_ok}`**!"
                                st.rerun()
                            except Exception as e_fam:
                                st.warning(str(e_fam))


def renderizar_graficos_compras(df, df_validos, limite_mensal=0.0):
    if df_validos.empty:
        st.info("Adicione compras com data para visualizar os gráficos.")
        return
    import altair as alt

    visao = st.radio("Agrupar evolução mensal por:", ["Total do Mês", "Por Categoria", "Por Supermercado"], horizontal=True)
    paleta = ["#881322", "#D91E2A", "#0B4EA2", "#1D4ED8", "#EF4444", "#60A5FA", "#F87171", "#93C5FD"]
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
                x=alt.X("Mês_Label:N", sort=ord_lbls, title=None, axis=alt.Axis(labelAngle=0, labelColor="#1E1B24")),
                y=alt.Y("Total:Q", title="Gasto (R$)", axis=alt.Axis(labelColor="#1E1B24", titleColor="#881322")),
                color=alt.Color(f"{col_cor}:N", scale=alt.Scale(range=paleta), legend=alt.Legend(orient="bottom", columns=2, title=None, labelColor="#1E1B24")),
                tooltip=[alt.Tooltip("Mês_Label:N", title="Mês"), alt.Tooltip(f"{col_cor}:N", title=col_cor), alt.Tooltip("Valor_fmt:N", title="Total")],
            ).properties(height=270, title=f"Gastos Mensais ({visao})")
        else:
            g = df_v.groupby(["Mês", "Mês_Label"], as_index=False)["Total"].sum()
            g["Valor_fmt"] = g["Total"].apply(formatar_reais)
            teto_y = max(g["Total"].max() * 1.18, limite_mensal * 1.12 if limite_mensal > 0 else 0.0, 10.0)
            barras = alt.Chart(g).mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7, color="#0B4EA2", size=34).encode(
                x=alt.X("Mês_Label:N", sort=ord_lbls, title=None, axis=alt.Axis(labelAngle=0, labelColor="#1E1B24")),
                y=alt.Y("Total:Q", title="Gasto (R$)", scale=alt.Scale(domain=[0, teto_y]), axis=alt.Axis(labelColor="#1E1B24", titleColor="#881322")),
                tooltip=[alt.Tooltip("Mês_Label:N", title="Mês"), alt.Tooltip("Valor_fmt:N", title="Total Gasto")],
            )
            camadas, tit = [barras, barras.mark_text(align="center", baseline="bottom", dy=-5, fontWeight="bold", color="#881322").encode(text="Valor_fmt:N")], []
            if len(g) >= 2:
                media = g["Total"].mean()
                camadas.append(alt.Chart(pd.DataFrame({"Media": [media]})).mark_rule(strokeDash=[5, 4], color="#881322", size=2).encode(y="Media:Q"))
                tit.append(f"média: {formatar_reais(media)}")
            if limite_mensal > 0:
                camadas.append(alt.Chart(pd.DataFrame({"Limite": [limite_mensal]})).mark_rule(strokeDash=[3, 3], color="#D91E2A", size=2).encode(y="Limite:Q"))
                tit.append(f"limite: {formatar_reais(limite_mensal)}")
            chart_m = alt.layer(*camadas).properties(height=270, title=f"Evolução Mensal ({' • '.join(tit)})" if tit else "Evolução Mensal")
        st.altair_chart(chart_m.configure(background="#FFFFFF"), use_container_width=True)

    with col_c:
        rc = df.groupby("Categoria", as_index=False)["Total"].sum().sort_values("Total", ascending=False)
        rc["Label"] = rc.apply(lambda r: f"{formatar_reais(r['Total'])} ({(r['Total'] / max(rc['Total'].sum(), 0.01)) * 100:.0f}%)", axis=1)
        bc = alt.Chart(rc).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
            y=alt.Y("Categoria:N", sort="-x", title=None, axis=alt.Axis(labelColor="#1E1B24")),
            x=alt.X("Total:Q", title=None, axis=None, scale=alt.Scale(domain=[0, max(rc["Total"].max() * 1.55, 10)])),
            color=alt.Color("Total:Q", scale=alt.Scale(range=["#60A5FA", "#0B4EA2", "#D91E2A"]), legend=None),
            tooltip=[alt.Tooltip("Categoria:N", title="Categoria"), alt.Tooltip("Label:N", title="Gasto")],
        )
        st.altair_chart((bc + bc.mark_text(align="left", baseline="middle", dx=6, fontSize=11, fontWeight="bold", color="#881322").encode(text="Label:N")).properties(height=270, title="Onde você gastou mais").configure(background="#FFFFFF"), use_container_width=True)


def renderizar_grupos_historico(df_exib, col_grupo, total_geral, modo="categoria"):
    resumo = df_exib.groupby(col_grupo, as_index=False)["Total"].sum().sort_values("Total", ascending=False)
    total_base, abrir_todos = max(total_geral, 0.01), len(resumo) <= 4
    for idx, row_g in enumerate(resumo.itertuples(index=False)):
        nome_grp, total_grp = getattr(row_g, col_grupo), float(row_g.Total)
        pct = min(100.0, (total_grp / total_base) * 100)
        sub = df_exib[df_exib[col_grupo] == nome_grp].sort_values(by=("Data_dt" if modo == "categoria" else ["Categoria", "Data_dt"]), ascending=(False if modo == "categoria" else [True, False]), na_position="last")
        ico = ICONES_CATEGORIA.get(nome_grp, "📦") if modo == "categoria" else "🏪"
        qtd = len(sub)
        plural = "item" if qtd == 1 else "itens"
        st.markdown(
            f'<div class="listai-hist-card"><div class="listai-hist-head">'
            f'<div class="listai-hist-title">{ico} {html.escape(str(nome_grp))} <span class="listai-hist-badge">{qtd} {plural} • {pct:.0f}%</span></div>'
            f'<div class="listai-hist-total">{formatar_reais(total_grp)}</div></div>'
            f'<div class="listai-hist-track"><div class="listai-hist-fill" style="width:{pct:.1f}%"></div></div></div>',
            unsafe_allow_html=True,
        )
        with st.expander(f"Ver produtos de {nome_grp} ({qtd})", expanded=(abrir_todos or idx == 0)):
            itens = []
            for r in sub.to_dict("records"):
                dt_txt, merc_str, cat_str = fmt_dt(r.get("Data_dt")), html.escape(str(r.get("Supermercado") or "Não informado")), str(r.get("Categoria") or "Outros")
                meta = f"🏪 {merc_str} · 📅 {dt_txt}" if modo == "categoria" else f"{ICONES_CATEGORIA.get(cat_str, '📦')} {html.escape(cat_str)} · 📅 {dt_txt}"
                itens.append(f'<div class="listai-hist-item"><div><div class="listai-hist-prod">{html.escape(str(r.get("Produto", "")))} <small>(x{fmt_qtd(r.get("Quantidade", 1))})</small></div><div class="listai-hist-meta">{meta}</div></div><div class="listai-hist-right"><div class="listai-hist-val">{formatar_reais(float(r.get("Total", 0.0)))}</div><div class="listai-hist-unit">{formatar_reais(float(r.get("Preço Unitário", 0.0)))}/un</div></div></div>')
            st.markdown("".join(itens), unsafe_allow_html=True)


def _montar_row_feed(r, mostrar_data=False):
    cat = str(r.get("Categoria") or "Outros")
    tags = f'<span class="listai-feed-tag">🏪 {html.escape(str(r.get("Supermercado") or "Não informado"))}</span><span class="listai-feed-tag listai-feed-tag-cat">{html.escape(cat)}</span>'
    if mostrar_data:
        tags += f'<span class="listai-feed-tag">📅 {fmt_dt(r.get("Data_dt"))}</span>'
    return f'<div class="listai-feed-row"><div class="listai-feed-left"><div class="listai-feed-ico">{ICONES_CATEGORIA.get(cat, "📦")}</div><div class="listai-feed-info"><div class="listai-feed-name">{html.escape(str(r.get("Produto", "")))} <small>(x{fmt_qtd(r.get("Quantidade", 1))})</small></div><div class="listai-feed-tags">{tags}</div></div></div><div class="listai-hist-right"><div class="listai-hist-val">{formatar_reais(float(r.get("Total", 0.0)))}</div><div class="listai-hist-unit">{formatar_reais(float(r.get("Preço Unitário", 0.0)))}/un</div></div></div>'


def renderizar_lista_geral_historico(df_tab, agrupar_por_data=True):
    regs = df_tab.head(100).to_dict("records")
    if not agrupar_por_data:
        st.markdown(f'<div class="listai-feed-box">{"".join(_montar_row_feed(r, True) for r in regs)}</div>', unsafe_allow_html=True)
        return
    blocos, mapa, hoje = [], {}, date.today().strftime("%d/%m/%Y")
    for r in regs:
        dia = fmt_dt(r.get("Data_dt"))
        if dia not in mapa:
            mapa[dia] = {"dia": dia, "total": 0.0, "itens": []}
            blocos.append(mapa[dia])
        mapa[dia]["total"] += float(r.get("Total", 0.0))
        mapa[dia]["itens"].append(r)
    partes = []
    for g in blocos:
        dia_lbl = f"Hoje ({g['dia']})" if g["dia"] == hoje else g["dia"]
        rows_html = "".join(_montar_row_feed(r) for r in g["itens"])
        partes.append(f'<div class="listai-feed-day"><span>📅 {html.escape(dia_lbl)}</span><span>Total: {formatar_reais(g["total"])}</span></div><div class="listai-feed-box">{rows_html}</div>')
    st.markdown("".join(partes), unsafe_allow_html=True)


# --- Páginas ---
def pagina_compra(ctx):
    usuario_atual, nome_usuario, api_key = ctx["usuario"], ctx["nome"], ctx["api_key"]
    gps_regiao, gps_mercados = ctx["gps_regiao"], ctx["gps_mercados"]

    mes_hoje = date.today().strftime("%Y-%m")
    df_c, df_v = obter_compras_com_datas(usuario_atual)
    gasto_mes = 0.0 if df_v.empty else float(df_v.loc[df_v["Mês"] == mes_hoje, "Total"].sum())
    df_pre = carregar_pre_lista(obter_dono_lista(usuario_atual))
    pend = int((~df_pre["Comprado"]).sum()) if not df_pre.empty else 0

    with st.container(key="kpi_2cols_compra"):
        k1, k2 = st.columns(2)
        k1.metric("📅 Gasto no mês", formatar_reais(gasto_mes))
        k2.metric("📝 Na lista", f"{pend} pendente(s)" if pend else "Tudo ok ✅")

    renderizar_painel_limite_mensal(usuario_atual, "compra", gasto_mes=gasto_mes)

    mercados_reg = carregar_mercados()
    regioes = ([gps_regiao] if gps_regiao and gps_regiao not in mercados_reg else []) + sorted(mercados_reg.keys())
    op_reg = regioes + ["➕ Nova região..."]

    if (rp := st.session_state.pop("regiao_para_selecionar", None)) in op_reg:
        st.session_state["sel_reg_compra"] = rp
    if st.session_state.get("sel_reg_compra") not in op_reg:
        st.session_state["sel_reg_compra"] = gps_regiao if gps_regiao in op_reg else op_reg[0]

    reg_sel = st.session_state["sel_reg_compra"]
    reg_ativa = st.session_state.get("input_nova_regiao", "").strip() if reg_sel == "➕ Nova região..." else reg_sel
    versao, dist_gps = st.session_state["form_versao"], dict(gps_mercados)

    lista_m = [st.session_state["valor_supermercado"].strip()] if st.session_state.get("valor_supermercado", "").strip() else []
    for m in ([n for n, _ in gps_mercados] if reg_ativa == gps_regiao else []) + list(mercados_reg.get(reg_ativa, [])):
        if m not in lista_m:
            lista_m.append(m)
    op_merc = lista_m + ["➕ Novo supermercado..."]

    if (mp := st.session_state.pop("merc_para_selecionar", None)) in op_merc:
        st.session_state["sel_merc_compra"] = mp
    if st.session_state.get("sel_merc_compra") not in op_merc:
        st.session_state["sel_merc_compra"] = op_merc[0]

    if not st.session_state.get("compra_ativa", False):
        with st.container(border=True):
            st.markdown(
                '<div class="listai-start-hero"><h3>🛒 Pronto para ir às compras?</h3>'
                '<p>Escolha o supermercado e toque em <strong>Iniciar Compra</strong> para registrar seus produtos e preços.</p></div>',
                unsafe_allow_html=True,
            )
            merc_ini = st.selectbox(
                "🏪 Onde você vai comprar?", op_merc, key="sel_merc_compra",
                format_func=(lambda m: f"{m} ({formatar_distancia(dist_gps[m])})" if reg_ativa == gps_regiao and dist_gps.get(m) is not None else m),
            )
            merc_ini_final = st.text_input("Nome do Supermercado", placeholder="Ex: Atacadão, Líder, Mateus", key="in_merc_inicio").strip() if merc_ini == "➕ Novo supermercado..." else merc_ini

            with st.expander(f"📍 Região: {reg_ativa or 'Selecionar'}", expanded=(reg_sel == "➕ Nova região...")):
                reg_esc = st.selectbox("📍 Região", op_reg, key="sel_reg_compra")
                if reg_esc == "➕ Nova região...":
                    st.text_input("Nome da nova região", placeholder="Ex: Belém - Batista Campos", key="input_nova_regiao")

            if pend > 0:
                st.caption(f"📝 Você tem **{pend}** {'item pendente' if pend == 1 else 'itens pendentes'} na sua **Lista**.")

            if st.button("🛒 Iniciar Compra", type="primary", use_container_width=True, key="btn_iniciar_compra"):
                if merc_ini == "➕ Novo supermercado..." and not merc_ini_final:
                    st.warning("Informe o nome do supermercado.")
                else:
                    if merc_ini_final and reg_ativa:
                        registrar_varios_mercados(reg_ativa, [merc_ini_final])
                        st.session_state["merc_para_selecionar"] = merc_ini_final
                    st.session_state.update({"compra_ativa": True, "compra_sessao_ids": []})
                    st.rerun()
        renderizar_tutorial_app()
        return

    with st.container(border=True):
        st.markdown("#### 🛒 Adicionar Produto")
        merc_esc = st.selectbox("🏪 Supermercado", op_merc, key="sel_merc_compra", format_func=(lambda m: f"{m} ({formatar_distancia(dist_gps[m])})" if reg_ativa == gps_regiao and dist_gps.get(m) is not None else m))
        merc_final = st.text_input("Nome do Supermercado", placeholder="Ex: Atacadão, Líder, Mateus").strip() if merc_esc == "➕ Novo supermercado..." else merc_esc

        if aviso := st.session_state.get("aviso_voz"):
            txt_v = f'🎤 **Ouvi:** *"{aviso["transcricao"]}"* • **{aviso["categoria"]}**' + (f" • **{aviso['supermercado']}**" if aviso.get("supermercado") else "")
            st.info(txt_v)
        if err_v := st.session_state.pop("aviso_voz_erro", None):
            st.warning(err_v)
        if aviso_bc := st.session_state.pop("aviso_barcode", None):
            st.success(f"🏷️ **Código `{aviso_bc['codigo']}` identificado:** {aviso_bc['produto']} — digite o preço abaixo e toque em **✅ Adicionar**!")

        prod = st.text_input("Produto", value=st.session_state["valor_produto"], placeholder="Ex: Arroz 5kg, Farinha, Açaí, Café...", key=f"input_produto_{versao}")
        with st.container(key="row_qtd_preco"):
            c_qtd, c_prc = st.columns(2)
            qtd = c_qtd.number_input("Qtd", min_value=1, value=int(st.session_state["valor_quantidade"]), step=1, key=f"input_qtd_{versao}")
            preco = c_prc.number_input("Preço (R$)", min_value=0.01, value=float(st.session_state["valor_preco"]), step=0.01, format="%.2f", key=f"input_preco_{versao}")

        cat_opcoes = ["✨ Automática"] + LISTA_CATEGORIAS
        cat_def = st.session_state.get("valor_categoria", "✨ Automática")
        cat_esc = st.selectbox("🏷️ Categoria", cat_opcoes, index=cat_opcoes.index(cat_def) if cat_def in cat_opcoes else 0, key=f"input_cat_{versao}", format_func=lambda c: c if c == "✨ Automática" else f"{ICONES_CATEGORIA.get(c, '📦')} {c}")

        with st.container(key="acao_add_voz"):
            c_add, c_mic = st.columns([1, 1.35], vertical_alignment="center")
            clicou_add = c_add.button("✅ Adicionar", type="primary", use_container_width=True, key=f"btn_add_prod_{versao}")
            audio = c_mic.audio_input("Por Voz", label_visibility="collapsed", key=f"audio_zap_{versao}")

        st.caption("🎤 Toque no microfone ao lado para falar (ex: *'2 arroz por 24,90'*)." if api_key else "🎤 Para usar a voz ou o leitor Pix, informe sua Chave Gemini em **👤 Perfil → Inteligência Artificial**.")

        if audio is not None:
            ab = audio.getvalue()
            ah = hashlib.sha256(ab).hexdigest()
            if ah != st.session_state.get("ultimo_audio_hash"):
                st.session_state["ultimo_audio_hash"] = ah
                if not api_key:
                    st.session_state.update({"aviso_voz_erro": "Configure a Chave Gemini em **👤 Perfil → Inteligência Artificial** para usar a voz.", "form_versao": versao + 1})
                    st.rerun()
                else:
                    with st.spinner("Ouvindo e preenchendo..."):
                        try:
                            dv = reconhecer_produto_por_voz(ab, api_key, mime_type=getattr(audio, "type", None) or "audio/wav")
                            if not dv["produto"]:
                                st.session_state.update({"aviso_voz_erro": "Não entendi o produto. Tente falar mais perto do microfone.", "form_versao": versao + 1})
                            else:
                                st.session_state.update({
                                    "valor_produto": dv["produto"], "valor_quantidade": dv["quantidade"],
                                    "valor_preco": dv["preco_unitario"] or 1.00,
                                    "valor_categoria": dv["categoria"] if dv["categoria"] in LISTA_CATEGORIAS else "✨ Automática",
                                    "aviso_voz": dv, "form_versao": versao + 1,
                                })
                                if dv["supermercado"]:
                                    st.session_state.update({"valor_supermercado": dv["supermercado"], "merc_para_selecionar": dv["supermercado"]})
                            st.rerun()
                        except Exception:
                            st.session_state.update({"aviso_voz_erro": "Não foi possível processar o áudio agora. Tente novamente.", "form_versao": versao + 1})
                            st.rerun()

        with st.expander(f"📅 Data ({date.today().strftime('%d/%m/%Y')}) e região ({reg_ativa or '-'})", expanded=(reg_sel == "➕ Nova região...")):
            cd1, cd2 = st.columns(2, vertical_alignment="center")
            data_c = cd1.date_input("Data da compra", value=date.today(), format="DD/MM/YYYY", key=f"input_dt_{versao}")
            comp = cd2.checkbox("📢 Compartilhar preço", value=True, key=f"input_comp_{versao}")
            reg_esc = st.selectbox("📍 Região", op_reg, key="sel_reg_compra")
            reg_final = st.text_input("Nome da nova região", placeholder="Ex: Belém - Nazaré", key="input_nova_regiao").strip() if reg_esc == "➕ Nova região..." else reg_esc

        if res_pix := renderizar_leitor_pix(api_key, merc_final, versao):
            selecionados, merc_usar = res_pix
            if not reg_final:
                st.warning("Informe a Região antes de salvar.")
            else:
                v_tot_lote = sum(it["quantidade"] * it["preco_unitario"] for it in selecionados)
                orc = carregar_orcamento_mensal(usuario_atual)
                lim, mes_c = float(orc["limite"]), data_c.strftime("%Y-%m")
                novo_tot = gasto_mes + (v_tot_lote if mes_c == mes_hoje else 0.0)
                if lim > 0 and orc["bloquear"] and mes_c == mes_hoje and novo_tot > lim:
                    st.error(f"🚫 Bloqueado pelo limite mensal de **{formatar_reais(lim)}**!")
                else:
                    registrar_varios_mercados(reg_final, [merc_usar])
                    linhas_u = [[data_c.isoformat(), reg_final, merc_usar, it["produto"], it["categoria"], it["quantidade"], it["preco_unitario"], it["quantidade"] * it["preco_unitario"]] for it in selecionados]
                    novos_ids = salvar_compra_usuario(usuario_atual, pd.DataFrame(linhas_u, columns=COLUNAS))
                    st.session_state.setdefault("compra_sessao_ids", []).extend(novos_ids)
                    if comp:
                        linhas_c = [[data_c.isoformat(), reg_final, merc_usar, it["produto"], it["categoria"], it["preco_unitario"], nome_usuario] for it in selecionados]
                        salvar_preco_comunidade(pd.DataFrame(linhas_c, columns=COLUNAS_COMUNIDADE))
                    if lim > 0 and mes_c == mes_hoje and novo_tot > lim:
                        st.session_state["msg_limite_alerta"] = f"⚠️ Gastos do mês chegaram a **{formatar_reais(novo_tot)}** (acima do limite de **{formatar_reais(lim)}**)."
                    st.session_state.pop("itens_foto_lidos", None)
                    st.session_state.pop("ultimo_cupom_hash", None)
                    st.session_state.update({"msg_sucesso": f"📸 **{len(selecionados)} item(ns)** salvos em **{merc_usar}**!", "merc_para_selecionar": merc_usar, "form_versao": versao + 1})
                    st.rerun()

        if clicou_add:
            if not (prod_ok := prod.strip()):
                st.warning("Digite ou fale o nome do produto.")
            elif not reg_final or not merc_final:
                st.warning("Informe a Região e o Supermercado.")
            else:
                v_tot, orc = float(qtd) * float(preco), carregar_orcamento_mensal(usuario_atual)
                lim, mes_c = float(orc["limite"]), data_c.strftime("%Y-%m")
                novo_tot = gasto_mes + (v_tot if mes_c == mes_hoje else 0.0)
                if lim > 0 and orc["bloquear"] and mes_c == mes_hoje and novo_tot > lim:
                    st.error(f"🚫 Bloqueado pelo limite mensal de **{formatar_reais(lim)}**!")
                else:
                    av = st.session_state.get("aviso_voz")
                    cat = cat_esc if cat_esc != "✨ Automática" else (av["categoria"] if (av and normalizar_texto(prod_ok) == normalizar_texto(av.get("produto", "")) and av.get("categoria") in LISTA_CATEGORIAS) else identificar_categoria(prod_ok, api_key))
                    registrar_varios_mercados(reg_final, [merc_final])
                    novos_ids = salvar_compra_usuario(usuario_atual, pd.DataFrame([[data_c.isoformat(), reg_final, merc_final, prod_ok, cat, qtd, preco, v_tot]], columns=COLUNAS))
                    st.session_state.setdefault("compra_sessao_ids", []).extend(novos_ids)
                    extra = ""
                    if comp:
                        salvar_preco_comunidade(pd.DataFrame([[data_c.isoformat(), reg_final, merc_final, prod_ok, cat, preco, nome_usuario]], columns=COLUNAS_COMUNIDADE))
                        extra = " Preço compartilhado!"
                    if lim > 0 and mes_c == mes_hoje and novo_tot > lim:
                        st.session_state["msg_limite_alerta"] = f"⚠️ Gastos do mês chegaram a **{formatar_reais(novo_tot)}** (acima do limite de **{formatar_reais(lim)}**)."
                    st.session_state.update({
                        "msg_sucesso": f"'{prod_ok}' adicionado em **{merc_final}** ({cat}).{extra}",
                        "valor_produto": "", "valor_quantidade": 1, "valor_preco": 1.00,
                        "valor_categoria": "✨ Automática", "valor_supermercado": "",
                        "regiao_para_selecionar": reg_final, "merc_para_selecionar": merc_final, "form_versao": versao + 1,
                    })
                    st.session_state.pop("aviso_voz", None)
                    st.session_state.pop("aviso_barcode", None)
                    st.rerun()

    renderizar_itens_compra_ativa(df_c, usuario_atual, merc_final, data_c)


def pagina_lista(ctx):
    st.subheader("📝 Lista de Compras")
    renderizar_bloco_lista_interativa(ctx["usuario"], ctx["api_key"], ctx["gps_regiao"])


def pagina_graficos(ctx):
    usuario_atual = ctx["usuario"]
    st.subheader("📊 Gráficos e Gastos")
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
            st.info("Você ainda não tem compras registradas. Adicione em **🛒 Compra**!")
        return

    with st.container(key="kpi_4cols_graf"):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Total Geral", formatar_reais(df_c["Total"].sum()))
        m2.metric("📅 Mês Atual", formatar_reais(gasto), delta=delta, delta_color="inverse")
        m3.metric("📈 Média Mensal", formatar_reais(media))
        m4.metric("🛍️ Itens", len(df_c))

    with st.container(border=True):
        renderizar_graficos_compras(df_c, df_v, limite_mensal=float(carregar_orcamento_mensal(usuario_atual)["limite"]))


def pagina_historico(ctx):
    usuario_atual = ctx["usuario"]
    st.subheader("🧾 Histórico de Compras")
    df_c, df_v = obter_compras_com_datas(usuario_atual)
    if df_c.empty:
        with st.container(border=True):
            st.info("Nenhuma compra no histórico ainda. Cadastre itens em **🛒 Compra**!")
        return

    with st.container(border=True):
        df_e = df_c.copy()
        df_e["Supermercado"] = df_e["Supermercado"].replace("", "Não informado").fillna("Não informado")
        df_e["Categoria"] = df_e["Categoria"].replace("", "Outros").fillna("Outros")
        with st.container(key="kpi_4cols_hist"):
            f1, f2, f3, f4 = st.columns(4)
            mes_s = f1.selectbox("📅 Mês", ["Todos"] + (sorted(df_v["Mês"].unique(), reverse=True) if not df_v.empty else []))
            merc_s = f2.selectbox("🏪 Mercado", ["Todos"] + sorted(df_e["Supermercado"].unique()))
            cat_s = f3.selectbox("🏷️ Categoria", ["Todas"] + sorted(df_e["Categoria"].unique()))
            busca = f4.text_input("🔎 Buscar", placeholder="Ex: arroz...").strip()

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
        with st.container(key="kpi_2cols_hist"):
            hm1, hm2 = st.columns(2)
            hm1.metric("💰 Total Filtrado", formatar_reais(tot_f))
            hm2.metric("🛍️ Compras", f"{len(df_e)} itens · {df_e['Categoria'].nunique()} cat.")

        with st.expander("✏️ Editar uma compra", expanded=(st.session_state.get("edit_hist_idx") is not None)):
            ops_ed = {i: f"{r['Data'] or 'Sem data'} | {r['Produto']} (x{fmt_qtd(r['Quantidade'])}) — {formatar_reais(float(r['Total']))}" for i, r in df_e.iloc[::-1].iterrows()}
            idx_ed = st.selectbox("Selecione o produto:", list(ops_ed.keys()), format_func=lambda i: ops_ed[i], key="sel_hist_edit")
            renderizar_editor_compra(df_c, idx_ed, "edit_hist_idx", usuario_atual)

        aba_cat, aba_merc, aba_lst = st.tabs(["🏷️ Categoria", "🏪 Mercado", "📋 Geral"])
        with aba_cat:
            renderizar_grupos_historico(df_e, "Categoria", tot_f, modo="categoria")
        with aba_merc:
            renderizar_grupos_historico(df_e, "Supermercado", tot_f, modo="supermercado")
        with aba_lst:
            co, ce = st.columns([3, 1.4], vertical_alignment="bottom")
            ordem = co.radio("Ordenar:", ["Mais recentes", "Maior valor", "Produto (A–Z)"], horizontal=True, key="hist_ordem_lista")
            df_t = df_e.sort_values(by="Data_dt", ascending=False, na_position="last") if ordem == "Mais recentes" else (df_e.sort_values(by="Total", ascending=False) if ordem == "Maior valor" else df_e.sort_values(by="Produto", key=lambda s: s.astype(str).str.lower()))
            ce.download_button("⬇️ Exportar CSV", data=df_t[COLUNAS].to_csv(index=False).encode("utf-8-sig"), file_name=f"listai_compras_{date.today().isoformat()}.csv", mime="text/csv", use_container_width=True)
            renderizar_lista_geral_historico(df_t, agrupar_por_data=(ordem == "Mais recentes"))

    with st.expander("🗑️ Excluir vários ou limpar tudo"):
        ops = {i: f"{r['Data'] or 'Sem data'} | {r['Supermercado'] or '-'} | {r['Produto']} | R$ {r['Total']:.2f}" for i, r in df_c.iloc[::-1].iterrows()}
        sels = st.multiselect("Excluir itens específicos:", list(ops.keys()), format_func=lambda i: ops[i])
        if st.button("Excluir selecionados", disabled=not sels):
            excluir_compras_usuario(usuario_atual, ids=sels)
            st.rerun()
        st.divider()
        if st.checkbox("Confirmo apagar TODAS as minhas compras") and st.button("🗑️ Limpar tudo", type="primary"):
            excluir_compras_usuario(usuario_atual, tudo=True)
            st.rerun()


def pagina_precos(ctx):
    usuario_atual, gps_regiao = ctx["usuario"], ctx["gps_regiao"]
    st.subheader("🏆 Banco de Preços por Supermercado")
    df_ord = carregar_comunidade_ordenada()
    if df_ord.empty:
        with st.container(border=True):
            st.info("Ainda não há preços compartilhados. Cadastre uma compra em **🛒 Compra**!")
        return

    with st.container(border=True):
        with st.container(key="kpi_4cols_db"):
            c1, c2, c3, c4 = st.columns(4)
            busca = c1.text_input("🔎 Produto", placeholder="Ex: arroz, café...").strip()
            regs = ["Todas"] + sorted(r for r in df_ord["Região"].dropna().unique() if str(r).strip())
            reg_f = c2.selectbox("📍 Região", regs, index=regs.index(gps_regiao) if gps_regiao in regs else 0, key=f"f_com_{gps_regiao}")
            df_reg = df_ord if reg_f == "Todas" else df_ord[df_ord["Região"] == reg_f]
            mercs = ["Todos"] + sorted(m for m in df_reg["Supermercado"].dropna().unique() if str(m).strip())
            merc_f = c3.selectbox("🏪 Mercado", mercs)
            cats = ["Todas"] + sorted(c for c in df_reg["Categoria"].dropna().unique() if str(c).strip())
            cat_f = c4.selectbox("🏷️ Categoria", cats)

    df_f = df_reg.copy()
    if merc_f != "Todos":
        df_f = df_f[df_f["Supermercado"] == merc_f]
    if cat_f != "Todas":
        df_f = df_f[df_f["Categoria"] == cat_f]
    if busca:
        t = normalizar_texto(busca)
        df_f = df_f[[t in p for p in df_f["Prod_norm"]]]

    if df_f.empty:
        st.warning("Nenhum preço encontrado. Tente ajustar os filtros.")
        return

    df_base = df_f.sort_values(by=["Data_dt", "Preço Unitário"], ascending=[False, True], na_position="last")
    df_db = df_base.drop_duplicates(subset=["Merc_norm", "Região", "Prod_norm"], keep="first").copy()

    min_por_prod = df_db.groupby("Prod_norm")["Preço Unitário"].min().to_dict()
    contar_merc_prod = df_db.groupby("Prod_norm")["Merc_norm"].nunique().to_dict()
    ranking_reg = calcular_ranking_precos_mercados(df_reg)

    with st.container(key="kpi_3cols_db"):
        k1, k2, k3 = st.columns(3)
        k1.metric("🏪 Supermercados", df_db["Supermercado"].nunique())
        k2.metric("📦 Produtos", df_db["Prod_norm"].nunique())
        k3.metric("🏷️ Preços ativos", len(df_db))

    if busca:
        m = df_db.sort_values(by="Preço Unitário", ascending=True).iloc[0]
        menor_p = float(m["Preço Unitário"])
        economia = max(0.0, float(df_db["Preço Unitário"].max()) - menor_p)
        eco_html = f'<span class="listai-eco-pill">Economia de até {formatar_reais(economia)}</span>' if economia > 0.01 else ""
        st.markdown(f'<div class="listai-winner-card"><div><h3>🏆 Melhor oferta: {html.escape(str(m["Produto"]))}</h3><div>🏪 <strong>{html.escape(str(m["Supermercado"] or "Mercado"))}</strong> • {html.escape(str(m["Região"] or ""))}</div>{eco_html}</div><div class="listai-winner-price">{formatar_reais(menor_p)}</div></div>', unsafe_allow_html=True)

    aba_db, aba_geral = st.tabs(["🏪 Por Supermercado (Banco de Dados)", "📋 Tabela Completa"])

    with aba_db:
        grupos = []
        for (merc_nome, reg_nome), grp in df_db.groupby(["Supermercado", "Região"]):
            mn = normalizar_texto(merc_nome)
            info = ranking_reg.get(mn, {})
            wins = sum(
                1 for r in grp.to_dict("records")
                if contar_merc_prod.get(r["Prod_norm"], 1) > 1 and float(r["Preço Unitário"]) <= min_por_prod.get(r["Prod_norm"], 0) + 0.01
            )
            grupos.append({
                "mercado": merc_nome or "Não informado", "regiao": reg_nome or "-",
                "grp": grp.sort_values(by="Produto", key=lambda s: s.astype(str).str.lower()),
                "info": info, "wins": wins, "qtd": len(grp),
                "indice": info.get("indice_pct", 0.0) if info else 0.0, "ult_dt": grp["Data_dt"].max(),
            })

        grupos.sort(key=lambda g: (0 if g["info"] and g["info"].get("tem_comparacao") else 1, g["indice"], -g["wins"], -g["qtd"]))
        lim_db = st.session_state.setdefault("db_limite_mercs", 10)
        abrir_auto = len(grupos) <= 3 or bool(busca)

        for idx, g in enumerate(grupos[:lim_db]):
            selo_txt, selo_cls = classificar_selo_preco(g["info"])
            wins_badge = f'<span class="listai-pill-best">🏆 {g["wins"]} menor(es)</span>' if g["wins"] > 0 else ""
            st.markdown(
                f'<div class="listai-db-head"><div><div class="listai-db-title">🏪 {html.escape(g["mercado"])}</div>'
                f'<div class="listai-db-sub">📍 {html.escape(g["regiao"])} • 📅 Atualizado em {fmt_dt(g["ult_dt"])}</div></div>'
                f'<div class="listai-db-badges"><span class="listai-pill-muted">📦 {g["qtd"]} {"item" if g["qtd"] == 1 else "itens"}</span>{wins_badge}<span class="{selo_cls}">{html.escape(selo_txt)}</span></div></div>',
                unsafe_allow_html=True,
            )
            with st.expander(f"Abrir banco de preços — {g['mercado']} ({g['qtd']})", expanded=(abrir_auto or idx == 0)):
                renderizar_tabela_banco_precos(g["grp"].head(60), min_por_prod, contar_merc_prod, mostrar_mercado=False)

        if len(grupos) > lim_db:
            if st.button(f"🏪 Mostrar mais supermercados ({len(grupos) - lim_db} restantes)", use_container_width=True, key="btn_mais_db_mercs"):
                st.session_state["db_limite_mercs"] = lim_db + 10
                st.rerun()

    with aba_geral:
        co, ce = st.columns([3, 1.3], vertical_alignment="bottom")
        ordem_db = co.radio("Ordenar por:", ["Menor preço", "Mais recentes", "Produto (A–Z)", "Supermercado"], horizontal=True, key="db_ordem_geral")
        if ordem_db == "Menor preço":
            df_g = df_db.sort_values(by=["Preço Unitário", "Data_dt"], ascending=[True, False])
        elif ordem_db == "Mais recentes":
            df_g = df_db.sort_values(by=["Data_dt", "Preço Unitário"], ascending=[False, True], na_position="last")
        elif ordem_db == "Produto (A–Z)":
            df_g = df_db.sort_values(by="Produto", key=lambda s: s.astype(str).str.lower())
        else:
            df_g = df_db.sort_values(by=["Supermercado", "Preço Unitário"], ascending=[True, True])

        df_exp = df_g[["Data", "Região", "Supermercado", "Produto", "Categoria", "Preço Unitário"]].copy()
        ce.download_button("⬇️ Exportar CSV", data=df_exp.to_csv(index=False).encode("utf-8-sig"), file_name=f"listai_precos_{date.today().isoformat()}.csv", mime="text/csv", use_container_width=True)
        renderizar_tabela_banco_precos(df_g.head(80), min_por_prod, contar_merc_prod, mostrar_mercado=True)
        if len(df_g) > 80:
            st.caption(f"Exibindo os primeiros 80 de {len(df_g)} registros. Use os filtros acima para refinar.")

    zap_df = df_db.sort_values(by="Preço Unitário", ascending=True).head(5)
    zap = "\n".join(["🛒 *Melhores preços no Listaí:*", ""] + [f"• *{r['Produto']}*: R$ {r['Preço Unitário']:.2f} ({r['Supermercado']} - {r['Região']})" for r in zap_df.to_dict("records")])
    st.link_button("📲 Enviar melhores preços no WhatsApp", f"https://wa.me/?text={urllib.parse.quote(zap)}", type="primary", use_container_width=True)

    if usuario_atual in ctx["admins"]:
        with st.expander("👑 Admin — Limpar comunidade"):
            if st.button("Apagar preços compartilhados"):
                limpar_comunidade()
                st.rerun()


def pagina_mercados(ctx):
    usuario_atual, gps_coords, gps_regiao = ctx["usuario"], ctx["gps_coords"], ctx["gps_regiao"]
    st.subheader("🗺️ Mercados da Região")
    raio_atual = int(st.session_state.get("gps_raio_atual", 3))
    if raio_atual not in RAIO_OPCOES:
        raio_atual = 3

    with st.container(border=True):
        raio = st.select_slider("📡 Raio de alcance", options=RAIO_OPCOES, value=raio_atual, format_func=lambda x: RAIO_LABELS.get(x, f"{x} km"))
        st.caption(f"Buscando estabelecimentos em até **{raio} km** de distância.")

        with st.expander("📍 Ativar ou atualizar GPS", expanded=not bool(gps_coords)):
            if streamlit_geolocation:
                c_geo, c_ref = st.columns([1.2, 2], vertical_alignment="center")
                with c_geo:
                    st.caption("Toque para localizar:")
                    processar_leitura_gps(streamlit_geolocation(), usuario_atual)
                with c_ref:
                    if gps_coords:
                        if st.button(f"🔄 Atualizar em {raio} km ({gps_regiao})", type="primary", use_container_width=True):
                            with st.spinner(f"Buscando mercados em até {raio} km..."):
                                try:
                                    nova = consultar_overpass_mercados(gps_coords[0], gps_coords[1], raio * 1000)
                                    if nova:
                                        registrar_varios_mercados(gps_regiao, [m["Supermercado"] for m in nova])
                                    salvar_preferencias_gps(gps_coords[0], gps_coords[1], gps_regiao, usuario_atual)
                                    st.session_state.update({"gps_detalhes": nova, "gps_mercados": resumir_mercados(nova), "gps_raio_atual": raio, "mkt_limite_exib": 15})
                                    st.rerun()
                                except Exception as e:
                                    st.warning(f"⚠️ {e}")
                    else:
                        st.info("Toque no ícone ao lado para descobrir os mercados perto de você.")
            else:
                st.warning("Pacote `streamlit-geolocation` não instalado.")

        with st.expander("🔎 Buscar Cidade / Bairro / CEP"):
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            reg_b = c1.text_input("Cidade, Bairro ou CEP", placeholder="Ex: Belém - Nazaré, 66035-145").strip()
            if c2.button("Buscar", type="primary", use_container_width=True) and reg_b:
                with st.spinner(f"Procurando em até {raio} km..."):
                    try:
                        loc, lm = buscar_supermercados_por_regiao(reg_b, raio * 1000)
                        st.session_state["res_manual"] = {
                            "regiao": reg_b, "nome_local": loc, "lista": lm,
                            "novos": registrar_varios_mercados(reg_b, [m["Supermercado"] for m in lm]) if (loc and lm) else 0,
                        }
                        st.session_state["mkt_limite_exib"] = 15
                        st.rerun()
                    except Exception as e:
                        st.warning(f"⚠️ {e}")

    mercados_reg = carregar_mercados()
    res_m = st.session_state.get("res_manual")
    if res_m and res_m.get("nome_local"):
        reg_exib, det_exib = res_m["regiao"], res_m["lista"]
        st.success(f"📍 Exibindo busca para **{res_m['nome_local']}** ({len(det_exib)} no raio de {raio} km).")
    elif gps_regiao:
        reg_exib, det_exib = gps_regiao, st.session_state.get("gps_detalhes", [])
    else:
        reg_exib = st.selectbox("📍 Região salva:", sorted(mercados_reg.keys())) if mercados_reg else ""
        det_exib = []

    df_com = carregar_comunidade_ordenada()
    lista_rank = montar_lista_mercados_classificada(reg_exib, det_exib, mercados_reg.get(reg_exib, []), df_com)
    if not lista_rank:
        st.info("Nenhum supermercado encontrado nesta região ainda. Ative seu GPS ou busque uma cidade acima.")
        return

    st.markdown(f"#### 🏆 Classificação por Preço — {html.escape(reg_exib or 'Região')}")
    st.caption("Ordenados do **mais barato** para o mais caro com base nos preços compartilhados pela comunidade.")

    com_mapa = [x for x in lista_rank if x.get("lat") is not None and x.get("lon") is not None]
    aba_lista, aba_mapa = st.tabs([f"📋 Ranking ({len(lista_rank)})", f"🗺️ Mapa ({len(com_mapa)})"])

    with aba_lista:
        medalhas = {0: "🥇", 1: "🥈", 2: "🥉"}
        lim_mkt = st.session_state.setdefault("mkt_limite_exib", 15)
        for idx, m in enumerate(lista_rank[:lim_mkt]):
            info = m.get("preco_info")
            selo_txt, selo_cls = classificar_selo_preco(info)
            pos_txt = medalhas.get(idx, f"{idx + 1}º") if info else "📍"
            rank_cls = "listai-mkt-rank listai-mkt-rank-top" if (info and idx == 0) else "listai-mkt-rank"

            dist_txt = formatar_distancia(m.get("Distância (m)"))
            meta_partes = [p for p in [m.get("Tipo"), f"📏 {dist_txt}" if dist_txt else "", m.get("Endereço") if m.get("Endereço") not in ("-", reg_exib, "") else ""] if p]
            tags_html = f'<span class="{selo_cls}">{html.escape(selo_txt)}</span>'
            if info:
                if info.get("wins", 0) > 0:
                    tags_html += f'<span class="listai-pill-best">🏆 {info["wins"]} menor(es)</span>'
                tags_html += f'<span class="listai-pill-muted">📦 {info["qtd_precos"]} {"preço" if info["qtd_precos"] == 1 else "preços"}</span>'

            with st.container(border=True):
                with st.container(key=f"mkt_card_{idx}"):
                    c_inf, c_act = st.columns([4, 1.3], vertical_alignment="center")
                    c_inf.markdown(
                        f'<div class="listai-mkt-item"><div class="{rank_cls}">{pos_txt}</div>'
                        f'<div class="listai-mkt-info"><div class="listai-mkt-name">{html.escape(m["Supermercado"])}</div>'
                        f'<div class="listai-mkt-meta">{html.escape(" · ".join(meta_partes))}</div>'
                        f'<div class="listai-mkt-tags">{tags_html}</div></div></div>',
                        unsafe_allow_html=True,
                    )
                    if c_act.button("🛒 Comprar aqui", key=f"btn_comprar_mkt_{idx}", use_container_width=True):
                        if reg_exib:
                            registrar_varios_mercados(reg_exib, [m["Supermercado"]])
                            st.session_state["regiao_para_selecionar"] = reg_exib
                        st.session_state.update({"merc_para_selecionar": m["Supermercado"], "compra_ativa": True, "compra_sessao_ids": [], "pagina_atual": PAGINAS[0], "rolar_topo": True})
                        st.rerun()

        if len(lista_rank) > lim_mkt:
            if st.button(f"📋 Mostrar mais mercados ({len(lista_rank) - lim_mkt} restantes)", use_container_width=True, key="btn_mais_mkts"):
                st.session_state["mkt_limite_exib"] = lim_mkt + 15
                st.rerun()

    with aba_mapa:
        if com_mapa:
            st.map(pd.DataFrame(com_mapa), latitude="lat", longitude="lon")
        else:
            st.info("Use **📍 Ativar ou atualizar GPS** ou **🔎 Buscar Cidade / Bairro / CEP** para visualizar os pinos no mapa.")


def pagina_perfil(ctx):
    usuario_atual, nome_usuario = ctx["usuario"], ctx["nome"]
    api_key, origem_api = ctx["api_key"], ctx["origem_api"]
    gps_coords, gps_regiao, gps_mercados = ctx["gps_coords"], ctx["gps_regiao"], ctx["gps_mercados"]

    st.subheader("👤 Meu Perfil")
    st.info("ℹ️ **Versão Beta gratuita:** uso liberado durante os testes iniciais; planos ou cobrança poderão ser aplicados após alguns meses.")
    reg_u = dict(obter_perfil_atual(usuario_atual))
    df_p, _ = obter_compras_com_datas(usuario_atual)
    sub_p = f"@{usuario_atual}" + (f" • Desde {reg_u['criado_em']}" if reg_u.get("criado_em") else "")

    st.caption("☁️ Banco na nuvem: **Supabase conectado**" if supabase_ativo() else "💾 Armazenamento local (configure `SUPABASE_URL` e `SUPABASE_KEY` nos Secrets para salvar na nuvem)")

    with st.container(border=True):
        if err_f := st.session_state.pop("msg_foto_erro", None):
            st.warning(err_f)
        with st.container(key="perfil_hero_top"):
            c_av, c_inf = st.columns([1, 5], vertical_alignment="center")
            with c_av:
                with st.container(key="avatar_clicavel"):
                    st.markdown(f'<div class="listai-avatar-wrap">{avatar_html(nome_usuario, usuario_atual, 78, True)}<span class="listai-cam-badge">📷</span></div>', unsafe_allow_html=True)
                    if (f_up := st.file_uploader("Foto", type=None, label_visibility="collapsed", key=f"up_foto_{st.session_state.get('foto_versao', 0)}")) is not None:
                        raw = f_up.getvalue()
                        hf = hashlib.sha256(raw).hexdigest()
                        if hf != st.session_state.get("ultima_foto_hash"):
                            st.session_state["ultima_foto_hash"] = hf
                            try:
                                base_bytes = preparar_imagem_base(raw)
                                if base_bytes is None:
                                    ext = os.path.splitext(f_up.name.lower())[1].lstrip(".")
                                    ext = "jpg" if ext in ("jpeg", "jfif") else ext
                                    if ext not in EXTENSOES_FOTO:
                                        raise ValueError("Formato não suportado. Envie uma imagem JPG, PNG ou WEBP.")
                                    remover_foto_perfil(usuario_atual)
                                    with open(obter_arquivo_usuario(usuario_atual, f"foto_perfil.{ext}"), "wb") as f:
                                        f.write(raw)
                                    st.session_state.update({"foto_versao": st.session_state.get("foto_versao", 0) + 1, "msg_sucesso": "Foto atualizada!"})
                                else:
                                    limpar_estado_editor_foto()
                                    st.session_state.update({"foto_rascunho": base_bytes, "editando_foto": True, "foto_versao": st.session_state.get("foto_versao", 0) + 1})
                            except ValueError as err_foto:
                                st.session_state.update({"foto_versao": st.session_state.get("foto_versao", 0) + 1, "msg_foto_erro": str(err_foto)})
                            st.rerun()
            with c_inf:
                st.markdown(f'<div class="listai-profile-info"><h3>{html.escape(nome_usuario)}</h3><span>{html.escape(sub_p)}</span><span class="listai-foto-dica">👆 Toque na foto para trocar</span></div>', unsafe_allow_html=True)
                if carregar_foto_perfil_base64(usuario_atual) is not None and not st.session_state.get("editando_foto"):
                    with st.container(key="foto_btns_row"):
                        b_aj, b_rm = st.columns(2)
                        if b_aj.button("✂️ Ajustar", key="btn_ajustar_foto", use_container_width=True):
                            if orig := carregar_foto_original_bytes(usuario_atual):
                                try:
                                    if base_ed := preparar_imagem_base(orig):
                                        limpar_estado_editor_foto()
                                        st.session_state.update({"foto_rascunho": base_ed, "editando_foto": True})
                                        st.rerun()
                                except ValueError:
                                    pass
                            st.warning("Para ajustar, envie a foto novamente tocando no círculo.")
                        if b_rm.button("🗑️ Remover", key="btn_remover_foto", use_container_width=True):
                            remover_foto_perfil(usuario_atual)
                            st.session_state.pop("ultima_foto_hash", None)
                            st.session_state.update({"foto_versao": st.session_state.get("foto_versao", 0) + 1, "msg_sucesso": "Foto removida."})
                            st.rerun()

        if st.session_state.get("editando_foto") and (rascunho := st.session_state.get("foto_rascunho")):
            renderizar_editor_foto_perfil(usuario_atual, rascunho)

        with st.container(key="kpi_2cols_perfil"):
            pm1, pm2 = st.columns(2)
            pm1.metric("🛍️ Compras", len(df_p))
            pm2.metric("💰 Acumulado", formatar_reais(float(df_p["Total"].sum()) if not df_p.empty else 0.0))

    c_esq, c_dir = st.columns(2)
    with c_esq:
        with st.container(border=True):
            st.markdown("#### 📋 Informações Pessoais")
            with st.form("form_perfil_usuario", border=False):
                p_nome = st.text_input("Nome completo *", value=reg_u.get("nome", nome_usuario))
                p_email = st.text_input("E-mail", value=reg_u.get("email", ""))
                p_tel = st.text_input("WhatsApp", value=reg_u.get("telefone", ""))
                p_cid = st.text_input("Cidade / Bairro", value=reg_u.get("cidade", ""))
                if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                    if len(nome_ok := p_nome.strip()) < 2:
                        st.warning("Informe seu nome completo.")
                    else:
                        reg_u.update({"nome": nome_ok, "email": p_email.strip(), "telefone": p_tel.strip(), "cidade": p_cid.strip()})
                        salvar_usuario_unico(usuario_atual, reg_u)
                        st.session_state.update({"nome_usuario": nome_ok, "msg_sucesso": "Informações salvas!"})
                        st.rerun()

        with st.expander("💡 Lembrete e Pergunta de Recuperação", expanded=not bool(reg_u.get("lembrete") or reg_u.get("resposta_seg_hash"))):
            with st.form("form_recuperacao_perfil", border=False):
                r_lemb = st.text_input("Lembrete / dica da senha", value=reg_u.get("lembrete", ""), placeholder="Ex: Nome do pet + ano")
                perg_at = reg_u.get("pergunta_seg", PERGUNTAS_SEGURANCA[0])
                r_perg = st.selectbox("Pergunta secreta", PERGUNTAS_SEGURANCA, index=PERGUNTAS_SEGURANCA.index(perg_at) if perg_at in PERGUNTAS_SEGURANCA else 0)
                r_resp = st.text_input("Resposta secreta", placeholder="Já configurada (digite apenas para trocar)" if reg_u.get("resposta_seg_hash") else "Digite sua resposta secreta")
                if st.form_submit_button("💾 Salvar recuperação", use_container_width=True):
                    reg_u.update({"lembrete": r_lemb.strip(), "pergunta_seg": r_perg})
                    if r_resp.strip():
                        reg_u["resposta_seg_hash"] = gerar_hash_senha(normalizar_texto(r_resp))
                    salvar_usuario_unico(usuario_atual, reg_u)
                    st.session_state["msg_sucesso"] = "Configurações de recuperação salvas!"
                    st.rerun()

        with st.expander("🔒 Alterar Senha"):
            with st.form("form_trocar_senha", clear_on_submit=True, border=False):
                s_at = st.text_input("Senha atual", type="password")
                s_nv = st.text_input("Nova senha", type="password")
                s_cf = st.text_input("Confirmar senha", type="password")
                if st.form_submit_button("Atualizar senha", use_container_width=True):
                    if not verificar_senha(s_at, reg_u.get("hash", "")):
                        st.error("Senha atual incorreta.")
                    elif len(s_nv) < 4:
                        st.warning("Mínimo 4 caracteres.")
                    elif s_nv != s_cf:
                        st.error("As senhas não coincidem.")
                    else:
                        atualizar_campos_perfil(usuario_atual, senha_hash=gerar_hash_senha(s_nv))
                        st.session_state["msg_sucesso"] = "Senha atualizada!"
                        st.rerun()

    with c_dir:
        renderizar_painel_limite_mensal(usuario_atual, "perfil", expandir_config=True)
        with st.container(border=True):
            st.markdown("#### 📍 Localização GPS")
            if gps_coords:
                st.success(f"📌 **{gps_regiao}** · Mais próximo: **{gps_mercados[0][0]} ({formatar_distancia(gps_mercados[0][1])})**") if (gps_mercados and gps_mercados[0][1] is not None) else st.info(f"📌 Região: **{gps_regiao}**")
            with st.expander("📡 Atualizar localização GPS", expanded=not bool(gps_coords)):
                processar_leitura_gps(streamlit_geolocation(), usuario_atual) if streamlit_geolocation else st.warning("Pacote `streamlit-geolocation` não instalado.")

        with st.expander("⚙️ Inteligência Artificial (API Gemini)", expanded=not bool(api_key)):
            if api_key and origem_api == "secrets":
                st.success("API Gemini conectada pelo servidor.")
            else:
                if api_key:
                    st.success("API Gemini conectada na sessão.")
                with st.form("form_gemini_perfil", border=False):
                    nk = st.text_input("Chave API Gemini", value=st.session_state.get("gemini_api_key_usuario", ""), type="password", placeholder="Cole sua GEMINI_API_KEY")
                    if st.form_submit_button("Salvar chave IA", use_container_width=True):
                        st.session_state.update({"gemini_api_key_usuario": nk.strip(), "msg_sucesso": "Chave salva!" if nk.strip() else "Chave removida."})
                        st.rerun()

    if usuario_atual in ctx["admins"]:
        with st.expander("👑 Admin — Anúncios, Carrossel Topo e Script CPM"):
            ads_salvos, tab_ok = carregar_anuncios_cadastrados()
            if supabase_ativo() and not tab_ok:
                st.warning("Tabela `anuncios` ainda não criada no Supabase. Rode o SQL da tabela `anuncios` no SQL Editor para salvar seus links na nuvem.")
            with st.form("form_admin_novo_anuncio", clear_on_submit=True, border=False):
                ad_tit = st.text_input("Título *", placeholder="Ex: 🔥 Sabão Omo 2,4kg em Oferta")
                ad_desc = st.text_input("Descrição *", placeholder="Ex: Desconto exclusivo na Amazon com frete grátis")
                ad_url = st.text_input("Link de Afiliado / Parceiro *", placeholder="https://amzn.to/...")
                a_c1, a_c2 = st.columns(2)
                ad_cat = a_c1.selectbox("Categoria alvo", ["Geral"] + LISTA_CATEGORIAS)
                ad_reg = a_c2.text_input("Região alvo (opcional)", placeholder="Ex: Belém (vazio = todas)")
                b_c1, b_c2 = st.columns(2)
                ad_btn = b_c1.text_input("Nome da Loja / Botão", value="Ver Oferta")
                ad_cup = b_c2.text_input("Cupom (opcional)", placeholder="Ex: LISTAI10")
                i_c1, i_c2 = st.columns(2)
                ad_img = i_c1.text_input("URL da Imagem (carrossel topo)", placeholder="https://.../foto.jpg")
                ad_desc_tag = i_c2.text_input("Selo de desconto (topo)", placeholder="Ex: -10%")
                ad_script = st.text_area("Script HTML CPM (opcional — Adsterra / Monetag / Adcash)", placeholder="<script>...</script>", height=70)
                if st.form_submit_button("➕ Publicar Anúncio", type="primary", use_container_width=True):
                    if not ad_tit.strip() or (not ad_url.strip() and not ad_script.strip()):
                        st.warning("Informe o título e o link (https://...) ou um Script HTML.")
                    else:
                        try:
                            salvar_anuncio_admin(ad_tit, ad_desc, ad_btn, ad_url, ad_cat, ad_reg, ad_cup, ad_img, ad_desc_tag, ad_script)
                            st.session_state["msg_sucesso"] = f"Anúncio **{ad_tit.strip()}** publicado!"
                            st.rerun()
                        except Exception as err_ad:
                            st.error(str(err_ad))

            if ads_salvos:
                st.divider()
                st.caption(f"**{len(ads_salvos)} anúncio(s) ativo(s):**")
                for ad_i in ads_salvos:
                    with st.container(key=f"adm_ad_row_{ad_i['id']}"):
                        ca_i, ca_d = st.columns([6, 1])
                        reg_lbl = f"📍 {ad_i['regiao']}" if ad_i.get("regiao") else "🌎 Todas"
                        tipo_lbl = "📡 CPM" if ad_i.get("script_html") else f"`{ad_i['categoria']}`"
                        ca_i.markdown(f"**{html.escape(ad_i['titulo'])}** · {tipo_lbl} · {html.escape(reg_lbl)}")
                        if ca_d.button("🗑️", key=f"btn_del_ad_{ad_i['id']}", help="Remover anúncio", use_container_width=True):
                            remover_anuncio_admin(ad_i["id"])
                            st.rerun()
            else:
                st.caption("Nenhum anúncio próprio cadastrado ainda — exibindo ofertas padrão.")

        with st.expander("👑 Admin — Usuários"):
            lista_adm = listar_usuarios_admin()
            st.metric("Total", len(lista_adm))
            st.dataframe(pd.DataFrame(lista_adm), hide_index=True, use_container_width=True)
            if lista_adm:
                with st.form("form_admin_reset_senha", border=False):
                    adm_u = st.selectbox("Redefinir senha do usuário", [u["Usuário"] for u in lista_adm])
                    adm_s = st.text_input("Nova senha provisória", type="password")
                    if st.form_submit_button("Redefinir senha", use_container_width=True):
                        if len(adm_s) < 4:
                            st.warning("Mínimo 4 caracteres.")
                        else:
                            atualizar_campos_perfil(adm_u, senha_hash=gerar_hash_senha(adm_s))
                            st.session_state["msg_sucesso"] = f"Senha de **@{adm_u}** redefinida!"
                            st.rerun()

    renderizar_tutorial_app()

    if st.button("🚪 Sair da conta", type="secondary", use_container_width=True, key="perfil_logout"):
        limpar_estado_usuario(incluir_auth=True)
        st.rerun()


# --- Inicialização e Execução ---
usuario_atual = st.session_state.get("usuario_logado", "usuario")
nome_usuario = st.session_state.get("nome_usuario", usuario_atual)

if st.session_state.get("gps_usuario_owner") != usuario_atual:
    limpar_estado_usuario(incluir_auth=False)
    prefs = carregar_preferencias_gps(usuario_atual)
    if prefs.get("lat") is not None and prefs.get("lon") is not None:
        rs = prefs.get("regiao", "")
        st.session_state.update({
            "gps_coords": (float(prefs["lat"]), float(prefs["lon"])),
            "gps_regiao": rs,
            "gps_mercados": [(m, None) for m in carregar_mercados().get(rs, [])],
            "gps_raio_atual": 3,
            "regiao_para_selecionar": rs,
        })
    st.session_state["gps_usuario_owner"] = usuario_atual

if st.session_state.get("pagina_atual") not in (PAGINAS + [PAGINA_PERFIL]):
    st.session_state["pagina_atual"] = PAGINAS[0]
for k, v in [
    ("form_versao", 0), ("valor_produto", ""), ("valor_quantidade", 1),
    ("valor_preco", 1.00), ("valor_categoria", "✨ Automática"), ("valor_supermercado", ""),
    ("compra_ativa", False), ("compra_sessao_ids", []),
]:
    st.session_state.setdefault(k, v)

api_key, origem_api = obter_api_key_gemini()
if st.session_state.pop("rolar_topo", False):
    rolar_para_topo()

ctx = {
    "usuario": usuario_atual,
    "nome": nome_usuario,
    "api_key": api_key,
    "origem_api": origem_api,
    "gps_coords": st.session_state.get("gps_coords"),
    "gps_regiao": st.session_state.get("gps_regiao", ""),
    "gps_mercados": st.session_state.get("gps_mercados", []),
    "admins": obter_usuarios_admin(),
}

renderizar_topo_nubank(ctx["nome"], ctx["usuario"], ctx["gps_regiao"])
exibir_banner_anuncio_topo()
renderizar_barra_navegacao()

if msg := st.session_state.pop("msg_sucesso", None):
    st.success(msg)
if msg_lim := st.session_state.pop("msg_limite_alerta", None):
    st.warning(msg_lim)

{
    PAGINAS[0]: pagina_compra,
    PAGINAS[1]: pagina_lista,
    PAGINAS[2]: pagina_graficos,
    PAGINAS[3]: pagina_historico,
    PAGINAS[4]: pagina_precos,
    PAGINAS[5]: pagina_mercados,
    PAGINA_PERFIL: pagina_perfil,
}[st.session_state["pagina_atual"]](ctx)

exibir_rodape_anuncio(ctx["gps_regiao"])