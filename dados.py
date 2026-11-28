import base64
from datetime import date
import hashlib
import json
import math
import os
import random
import re
import secrets
import uuid

import pandas as pd
import streamlit as st

from config import (
    ALFABETO_CASA,
    ANUNCIOS_PADRAO,
    ARQUIVO_ANUNCIOS,
    ARQUIVO_COMUNIDADE,
    ARQUIVO_MERCADOS,
    ARQUIVO_USUARIOS,
    COLUNAS,
    COLUNAS_COMUNIDADE,
    COLUNAS_PRE_LISTA,
    EXTENSOES_FOTO,
    OVERPASS_SERVERS,
    TRADUCAO_LOJA,
    ler_json,
    normalizar_texto,
    obter_arquivo_usuario,
    obter_http_session,
    salvar_json,
    sb_req,
    supabase_ativo,
)
from ia_leitor import identificar_categorias_em_lote


# --- Autenticação & Perfil ---
def gerar_hash_senha(senha):
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return f"pbkdf2${salt}${dk}"


def verificar_senha(digitada, salva):
    partes = str(salva or "").split("$")
    if len(partes) == 3 and partes[0] == "pbkdf2":
        dk = hashlib.pbkdf2_hmac("sha256", digitada.encode("utf-8"), partes[1].encode("utf-8"), 120_000).hex()
        return secrets.compare_digest(dk, partes[2])
    if len(partes) == 2:
        legado = hashlib.sha256((partes[0] + digitada).encode("utf-8")).hexdigest()
        return secrets.compare_digest(legado, partes[1])
    return False


def _normalizar_row_usuario_sb(r):
    return {
        "tipo": "senha",
        "hash": r.get("senha_hash", ""),
        "nome": r.get("nome", r.get("usuario", "")),
        "email": r.get("email") or "",
        "telefone": r.get("telefone") or "",
        "cidade": r.get("cidade") or "",
        "lembrete": r.get("lembrete") or "",
        "pergunta_seg": r.get("pergunta_seg") or "",
        "resposta_seg_hash": r.get("resposta_seg_hash") or "",
        "limite_mensal": float(r.get("limite_mensal") or 0.0),
        "bloquear_limite": bool(r.get("bloquear_limite") or False),
        "gps_lat": r.get("gps_lat"),
        "gps_lon": r.get("gps_lon"),
        "gps_regiao": r.get("gps_regiao") or "",
        "grupo_lista": str(r.get("grupo_lista") or "").strip().upper(),
        "favoritos": str(r.get("favoritos") or ""),
        "foto_url": r.get("foto_url") or "",
        "criado_em": str(r.get("criado_em") or "")[:10],
    }


def _carregar_usuarios_local():
    if dados := ler_json(ARQUIVO_USUARIOS, dict):
        return dados
    iniciais = {"teste": {"tipo": "senha", "hash": gerar_hash_senha("1234"), "nome": "Conta Teste", "lembrete": "Sequência numérica de 1 a 4", "criado_em": date.today().isoformat()}}
    salvar_json(ARQUIVO_USUARIOS, iniciais)
    return iniciais


def buscar_usuario_unico(usuario, colunas="*"):
    u = str(usuario or "").strip().lower()
    if not u:
        return None
    if supabase_ativo():
        rows = sb_req("GET", "usuarios", params={"usuario": f"eq.{u}", "select": colunas, "limit": "1"}) or []
        if not rows:
            if u == "teste":
                existente = sb_req("GET", "usuarios", params={"select": "usuario", "limit": "1"}) or []
                if not existente:
                    teste = {"usuario": "teste", "senha_hash": gerar_hash_senha("1234"), "nome": "Conta Teste", "lembrete": "Sequência numérica de 1 a 4"}
                    sb_req("POST", "usuarios", params={"on_conflict": "usuario"}, json_data=teste, extra_headers={"Prefer": "resolution=merge-duplicates"})
                    return _normalizar_row_usuario_sb(teste)
            return None
        return _normalizar_row_usuario_sb(rows[0])
    reg = _carregar_usuarios_local().get(u)
    return (dict(reg) if isinstance(reg, dict) else {"tipo": "senha", "hash": reg, "nome": u}) if reg is not None else None


def obter_perfil_atual(usuario):
    if st.session_state.get("_ss_perfil_owner") == usuario and isinstance(st.session_state.get("_ss_perfil"), dict):
        return st.session_state["_ss_perfil"]
    reg = buscar_usuario_unico(usuario) or {"tipo": "senha", "hash": "", "nome": usuario}
    st.session_state["_ss_perfil"] = reg
    st.session_state["_ss_perfil_owner"] = usuario
    return reg


def atualizar_campos_perfil(usuario, **campos_sb_e_local):
    if supabase_ativo():
        sb_req("PATCH", "usuarios", params={"usuario": f"eq.{usuario}"}, json_data=campos_sb_e_local)
        if st.session_state.get("_ss_perfil_owner") == usuario and isinstance(st.session_state.get("_ss_perfil"), dict):
            mapa = {"senha_hash": "hash", "limite_mensal": "limite_mensal", "bloquear_limite": "bloquear_limite"}
            for k, v in campos_sb_e_local.items():
                st.session_state["_ss_perfil"][mapa.get(k, k)] = v
    else:
        u_dict = _carregar_usuarios_local().copy()
        reg = dict(u_dict.get(usuario, {"tipo": "senha", "nome": usuario}))
        mapa_local = {"senha_hash": "hash", "limite_mensal": "limite_mensal", "bloquear_limite": "bloquear_limite"}
        for k, v in campos_sb_e_local.items():
            reg[mapa_local.get(k, k)] = v
        u_dict[usuario] = reg
        salvar_json(ARQUIVO_USUARIOS, u_dict)
        if st.session_state.get("_ss_perfil_owner") == usuario:
            st.session_state["_ss_perfil"] = reg


def salvar_usuario_unico(usuario, reg):
    if supabase_ativo():
        payload = {
            "usuario": usuario,
            "senha_hash": reg.get("hash", ""),
            "nome": reg.get("nome", usuario),
            "email": reg.get("email", ""),
            "telefone": reg.get("telefone", ""),
            "cidade": reg.get("cidade", ""),
            "lembrete": reg.get("lembrete", ""),
            "pergunta_seg": reg.get("pergunta_seg", ""),
            "resposta_seg_hash": reg.get("resposta_seg_hash", ""),
        }
        sb_req("POST", "usuarios", params={"on_conflict": "usuario"}, json_data=payload, extra_headers={"Prefer": "resolution=merge-duplicates"})
    else:
        u_dict = _carregar_usuarios_local().copy()
        u_dict[usuario] = reg
        salvar_json(ARQUIVO_USUARIOS, u_dict)
    if st.session_state.get("usuario_logado") == usuario:
        st.session_state["_ss_perfil"] = dict(reg)
        st.session_state["_ss_perfil_owner"] = usuario


def listar_usuarios_admin():
    if supabase_ativo():
        rows = sb_req("GET", "usuarios", params={"select": "usuario,nome,email,cidade", "order": "usuario.asc"}) or []
        return [{"Usuário": r["usuario"], "Nome": r.get("nome") or r["usuario"], "E-mail": r.get("email") or "-", "Cidade": r.get("cidade") or "-"} for r in rows]
    u_dict = _carregar_usuarios_local()
    return [{"Usuário": k, "Nome": v.get("nome", k) if isinstance(v, dict) else k, "E-mail": v.get("email", "-") if isinstance(v, dict) else "-", "Cidade": v.get("cidade", "-") if isinstance(v, dict) else "-"} for k, v in sorted(u_dict.items())]


# --- Favoritos (v2.0) ---
def carregar_favoritos(usuario):
    if isinstance(ss_fav := st.session_state.get("_ss_favoritos"), list) and st.session_state.get("_ss_perfil_owner") == usuario:
        return ss_fav
    raw = str(obter_perfil_atual(usuario).get("favoritos") or "").strip()
    favs = []
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                favs = [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            favs = [x.strip() for x in raw.split(",") if x.strip()]
    if not favs:
        loc = ler_json(obter_arquivo_usuario(usuario, "favoritos.json"), list)
        if isinstance(loc, list):
            favs = [str(x).strip() for x in loc if str(x).strip()]
    st.session_state["_ss_favoritos"] = favs
    return favs


def salvar_favoritos(usuario, lista_favs):
    limpos, vistos = [], set()
    for f in lista_favs:
        txt = str(f or "").strip()
        fn = normalizar_texto(txt)
        if txt and fn not in vistos:
            vistos.add(fn)
            limpos.append(txt)
    st.session_state["_ss_favoritos"] = limpos
    salvar_json(obter_arquivo_usuario(usuario, "favoritos.json"), limpos)
    if supabase_ativo():
        try:
            atualizar_campos_perfil(usuario, favoritos=json.dumps(limpos, ensure_ascii=False))
        except RuntimeError:
            pass
    return limpos


# --- Foto de Perfil ---
def carregar_foto_perfil_base64(usuario):
    if st.session_state.get("_ss_foto_owner") == usuario and "_ss_foto_b64" in st.session_state:
        return st.session_state["_ss_foto_b64"]
    res = None
    if supabase_ativo():
        foto_url = str(obter_perfil_atual(usuario).get("foto_url") or "")
        if foto_url.startswith("data:image/") and ";base64," in foto_url:
            cab, b64 = foto_url.split(";base64,", 1)
            res = (b64, cab.replace("data:", ""))
    else:
        for ext in EXTENSOES_FOTO:
            p = obter_arquivo_usuario(usuario, f"foto_perfil.{ext}")
            if os.path.exists(p) and os.path.getsize(p) > 0:
                with open(p, "rb") as f:
                    res = (base64.b64encode(f.read()).decode("ascii"), f"image/{'jpeg' if ext == 'jpg' else ext}")
                break
    st.session_state["_ss_foto_b64"] = res
    st.session_state["_ss_foto_owner"] = usuario
    return res


def carregar_foto_original_bytes(usuario):
    p_orig = obter_arquivo_usuario(usuario, "foto_original.jpg")
    if os.path.exists(p_orig) and os.path.getsize(p_orig) > 0:
        with open(p_orig, "rb") as f:
            return f.read()
    if foto := carregar_foto_perfil_base64(usuario):
        return base64.b64decode(foto[0])
    return None


def remover_foto_perfil(usuario, incluir_original=True):
    st.session_state.pop("_ss_foto_b64", None)
    st.session_state.pop("_ss_foto_owner", None)
    if supabase_ativo():
        atualizar_campos_perfil(usuario, foto_url="")
    alvos = [f"foto_perfil.{ext}" for ext in EXTENSOES_FOTO] + (["foto_original.jpg"] if incluir_original else [])
    for nome_arq in alvos:
        if os.path.exists(p := obter_arquivo_usuario(usuario, nome_arq)):
            os.remove(p)


def salvar_foto_perfil_final(usuario, orig_bytes, final_bytes):
    st.session_state.pop("_ss_foto_b64", None)
    st.session_state.pop("_ss_foto_owner", None)
    with open(obter_arquivo_usuario(usuario, "foto_original.jpg"), "wb") as f:
        f.write(orig_bytes)
    if supabase_ativo():
        b64 = base64.b64encode(final_bytes).decode("ascii")
        atualizar_campos_perfil(usuario, foto_url=f"data:image/jpeg;base64,{b64}")
    else:
        remover_foto_perfil(usuario, incluir_original=False)
        with open(obter_arquivo_usuario(usuario, "foto_perfil.jpg"), "wb") as f:
            f.write(final_bytes)


# --- Lista Compartilhada da Casa / Família ---
def validar_codigo_familia(codigo):
    cod = str(codigo or "").strip().upper()
    return cod if re.fullmatch(r"CASA-[A-Z0-9]{4,12}", cod) else None


def gerar_codigo_familia():
    return "CASA-" + "".join(secrets.choice(ALFABETO_CASA) for _ in range(6))


def obter_grupo_lista_atual(usuario):
    cod = str(obter_perfil_atual(usuario).get("grupo_lista") or "").strip().upper()
    return validar_codigo_familia(cod)


def obter_dono_lista(usuario):
    cod = obter_grupo_lista_atual(usuario)
    return f"fam:{cod}" if cod else usuario


def definir_grupo_lista(usuario, codigo):
    cod_ok = (validar_codigo_familia(codigo) or "") if codigo else ""
    try:
        atualizar_campos_perfil(usuario, grupo_lista=cod_ok)
    except RuntimeError as e:
        if "PGRST204" in str(e) or "grupo_lista" in str(e):
            if st.session_state.get("_ss_perfil_owner") == usuario and isinstance(st.session_state.get("_ss_perfil"), dict):
                st.session_state["_ss_perfil"]["grupo_lista"] = cod_ok
            raise RuntimeError("Falta a coluna 'grupo_lista' no Supabase. Rode no SQL Editor: ALTER TABLE public.usuarios ADD COLUMN IF NOT EXISTS grupo_lista text NOT NULL DEFAULT '';")
        raise
    st.session_state.pop("_ss_pre_lista_df", None)
    st.session_state.pop("_ss_pre_lista_owner", None)


# --- Anúncios ---
@st.cache_data(ttl=600, show_spinner=False)
def carregar_anuncios_cadastrados():
    if supabase_ativo():
        try:
            try:
                rows = sb_req(
                    "GET", "anuncios",
                    params={"ativo": "is.true", "select": "id,titulo,descricao,texto_botao,url,categoria,regiao,cupom,imagem_url,desconto,script_html", "order": "id.desc"},
                ) or []
            except RuntimeError as e:
                if "PGRST204" in str(e) or "400" in str(e):
                    rows = sb_req(
                        "GET", "anuncios",
                        params={"ativo": "is.true", "select": "id,titulo,descricao,texto_botao,url,categoria,regiao,cupom", "order": "id.desc"},
                    ) or []
                else:
                    raise
            return [
                {
                    "id": r.get("id"),
                    "titulo": str(r.get("titulo") or ""),
                    "descricao": str(r.get("descricao") or ""),
                    "texto_botao": str(r.get("texto_botao") or "Ver Oferta"),
                    "url": str(r.get("url") or ""),
                    "categoria": str(r.get("categoria") or "Geral"),
                    "regiao": str(r.get("regiao") or ""),
                    "cupom": str(r.get("cupom") or ""),
                    "imagem_url": str(r.get("imagem_url") or ""),
                    "desconto": str(r.get("desconto") or ""),
                    "script_html": str(r.get("script_html") or ""),
                }
                for r in rows
                if str(r.get("url") or "").startswith("https://") or str(r.get("script_html") or "").strip()
            ], True
        except RuntimeError:
            return [], False
    dados = ler_json(ARQUIVO_ANUNCIOS, list)
    return ([d for d in dados if isinstance(d, dict) and (str(d.get("url", "")).startswith("https://") or str(d.get("script_html", "")).strip())], True)


def salvar_anuncio_admin(titulo, descricao, texto_botao, url, categoria, regiao, cupom, imagem_url="", desconto="", script_html=""):
    url_ok, script_ok = url.strip(), script_html.strip()
    if not script_ok and not url_ok.startswith("https://"):
        raise ValueError("Informe um link começando com https:// (ou um Script HTML CPM).")
    payload = {
        "titulo": titulo.strip(), "descricao": descricao.strip(), "texto_botao": texto_botao.strip() or "Ver Oferta",
        "url": url_ok or "https://listai.streamlit.app", "categoria": categoria or "Geral", "regiao": regiao.strip(),
        "cupom": cupom.strip(), "imagem_url": imagem_url.strip(), "desconto": desconto.strip(), "script_html": script_ok,
    }
    if supabase_ativo():
        try:
            sb_req("POST", "anuncios", json_data={**payload, "ativo": True})
        except RuntimeError as e:
            if "PGRST204" in str(e) or "400" in str(e):
                basico = {k: payload[k] for k in ("titulo", "descricao", "texto_botao", "url", "categoria", "regiao", "cupom")}
                sb_req("POST", "anuncios", json_data={**basico, "ativo": True})
            else:
                raise
    else:
        lista = ler_json(ARQUIVO_ANUNCIOS, list)
        payload["id"] = str(uuid.uuid4())
        lista.insert(0, payload)
        salvar_json(ARQUIVO_ANUNCIOS, lista)
    carregar_anuncios_cadastrados.clear()


def remover_anuncio_admin(ad_id):
    if supabase_ativo():
        sb_req("DELETE", "anuncios", params={"id": f"eq.{int(ad_id)}"})
    else:
        lista = [d for d in ler_json(ARQUIVO_ANUNCIOS, list) if str(d.get("id")) != str(ad_id)]
        salvar_json(ARQUIVO_ANUNCIOS, lista)
    carregar_anuncios_cadastrados.clear()


def selecionar_anuncio_inteligente(regiao_usuario, pagina_atual):
    cadastrados, _ = carregar_anuncios_cadastrados()
    ads_url = [a for a in cadastrados if str(a.get("url", "")).startswith("https://")]
    pool = ads_url if ads_url else ANUNCIOS_PADRAO

    pesos_cat = {}
    df_pre_ss = st.session_state.get("_ss_pre_lista_df")
    if isinstance(df_pre_ss, pd.DataFrame) and not df_pre_ss.empty:
        pend = df_pre_ss[~df_pre_ss["Comprado"]] if "Comprado" in df_pre_ss else df_pre_ss
        for cat in pend["Categoria"].dropna().tolist():
            pesos_cat[str(cat)] = pesos_cat.get(str(cat), 0) + 3

    df_cmp_ss = st.session_state.get("_ss_compras_df")
    if isinstance(df_cmp_ss, pd.DataFrame) and not df_cmp_ss.empty:
        for cat in df_cmp_ss["Categoria"].tail(12).dropna().tolist():
            pesos_cat[str(cat)] = pesos_cat.get(str(cat), 0) + 1

    reg_u = normalizar_texto(regiao_usuario)
    candidatos = []
    for ad in pool:
        reg_ad, cat_ad = normalizar_texto(ad.get("regiao", "")), str(ad.get("categoria") or "Geral")
        score, motivo = 0, "OFERTA PARCEIRA"
        if reg_ad:
            if reg_u and (reg_ad in reg_u or reg_u in reg_ad):
                score += 100
                motivo = f"DESTAQUE EM {ad['regiao'].upper()}"
            else:
                continue
        if cat_ad != "Geral" and cat_ad in pesos_cat:
            score += 20 + min(pesos_cat[cat_ad], 15)
            if not reg_ad:
                motivo = f"PARA SUA COMPRA · {cat_ad.upper()}"
        elif cat_ad == "Geral":
            score += 2
        candidatos.append((score, motivo, ad))

    if not candidatos:
        candidatos = [(1, "OFERTA PARCEIRA", ad) for ad in ANUNCIOS_PADRAO]

    max_score = max(c[0] for c in candidatos)
    melhores = [c for c in candidatos if c[0] >= max_score - 2]
    seed = st.session_state.setdefault("anuncio_seed", random.randrange(100))
    idx = (seed + sum(ord(ch) for ch in str(pagina_atual))) % len(melhores)
    _, motivo_final, ad_final = melhores[idx]
    return ad_final, motivo_final


# --- Localização, Orçamento e Supermercados ---
def carregar_preferencias_gps(usuario):
    if supabase_ativo():
        u_reg = obter_perfil_atual(usuario)
        if u_reg.get("gps_lat") is not None and u_reg.get("gps_lon") is not None:
            return {"lat": u_reg["gps_lat"], "lon": u_reg["gps_lon"], "regiao": u_reg.get("gps_regiao", "")}
        return {}
    return ler_json(obter_arquivo_usuario(usuario, "preferencias_gps.json"), dict)


def salvar_preferencias_gps(lat, lon, regiao, usuario):
    if supabase_ativo():
        atualizar_campos_perfil(usuario, gps_lat=lat, gps_lon=lon, gps_regiao=regiao)
    else:
        salvar_json(obter_arquivo_usuario(usuario, "preferencias_gps.json"), {"lat": lat, "lon": lon, "regiao": regiao})


def carregar_orcamento_mensal(usuario):
    if supabase_ativo():
        u_reg = obter_perfil_atual(usuario)
        return {"limite": max(0.0, float(u_reg.get("limite_mensal") or 0.0)), "bloquear": bool(u_reg.get("bloquear_limite") or False)}
    dados = ler_json(obter_arquivo_usuario(usuario, "orcamento.json"), dict)
    try:
        return {"limite": max(0.0, float(dados.get("limite", 0.0))), "bloquear": bool(dados.get("bloquear", False))}
    except (TypeError, ValueError):
        return {"limite": 0.0, "bloquear": False}


def salvar_orcamento_mensal(limite, bloquear, usuario):
    lim_f, bloq_b = max(0.0, float(limite)), bool(bloquear)
    if supabase_ativo():
        atualizar_campos_perfil(usuario, limite_mensal=lim_f, bloquear_limite=bloq_b)
    else:
        salvar_json(obter_arquivo_usuario(usuario, "orcamento.json"), {"limite": lim_f, "bloquear": bloq_b})
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
    bbox = f"{lon - d_lon},{lat - d_lat},{lon + d_lon},{lat + d_lat}"
    enc, ok = {}, False
    for params in [
        {"q": "supermercado", "lat": lat, "lon": lon, "limit": 25, "osm_tag": "shop"},
        {"q": "mercado", "lat": lat, "lon": lon, "bbox": bbox, "limit": 25},
    ]:
        try:
            resp = http.get("https://photon.komoot.io/api/", params=params, timeout=6)
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


def consultar_nominatim_mercados(lat, lon, raio):
    http = obter_http_session()
    d_lat, d_lon = raio / 111320.0, raio / (111320.0 * max(0.2, abs(math.cos(math.radians(lat)))))
    viewbox = f"{lon - d_lon},{lat + d_lat},{lon + d_lon},{lat - d_lat}"
    enc, ok = {}, False
    for termo in ("supermercado", "mercado"):
        try:
            resp = http.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": termo, "format": "jsonv2", "viewbox": viewbox, "bounded": 1, "limit": 25, "accept-language": "pt-BR"},
                timeout=6,
            )
            if resp.status_code != 200:
                continue
            ok = True
            for item in resp.json():
                elat, elon = float(item["lat"]), float(item["lon"])
                dist = calcular_distancia_metros(lat, lon, elat, elon)
                if dist > raio:
                    continue
                nome = (item.get("name") or item.get("display_name", "").split(",")[0]).strip()
                if nome:
                    _registrar_ponto_mercado(enc, nome, TRADUCAO_LOJA.get(item.get("type", ""), "Supermercado"), "", elat, elon, dist)
        except Exception:
            continue
    return sorted(enc.values(), key=lambda x: x["Distância (m)"]) if ok else None


@st.cache_data(ttl=900, show_spinner=False)
def _consultar_mercados_apis(lat_r, lon_r, raio):
    http = obter_http_session()
    filtros = "".join(f'nw(around:{raio},{lat_r},{lon_r})["shop"="{s}"];' for s in TRADUCAO_LOJA)
    query = f"[out:json][timeout:10];({filtros});out center tags;"
    for srv in OVERPASS_SERVERS:
        try:
            resp = http.post(srv, data={"data": query}, timeout=10)
            if resp.status_code == 200:
                enc = {}
                for el in resp.json().get("elements", []):
                    tags = el.get("tags", {})
                    nome = (tags.get("name") or tags.get("brand") or "").strip()
                    elat, elon = el.get("lat") or el.get("center", {}).get("lat"), el.get("lon") or el.get("center", {}).get("lon")
                    if nome and elat is not None and elon is not None:
                        end = ", ".join(p for p in [f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip(), tags.get("addr:suburb", "")] if p)
                        _registrar_ponto_mercado(enc, nome, TRADUCAO_LOJA.get(tags.get("shop", "supermarket"), "Supermercado"), end, float(elat), float(elon), calcular_distancia_metros(lat_r, lon_r, float(elat), float(elon)))
                return sorted(enc.values(), key=lambda x: x["Distância (m)"])
        except Exception:
            continue
    if (res := consultar_photon_mercados(lat_r, lon_r, raio)) is not None:
        return res
    if (res_nom := consultar_nominatim_mercados(lat_r, lon_r, raio)) is not None:
        return res_nom
    raise RuntimeError("Servidores de mapa ocupados no momento. Tente novamente.")


def consultar_overpass_mercados(lat, lon, raio):
    return _consultar_mercados_apis(round(float(lat), 3), round(float(lon), 3), int(raio))


def resumir_mercados(lista):
    vistos, out = set(), []
    for x in lista:
        if x["Supermercado"] not in vistos:
            vistos.add(x["Supermercado"])
            out.append((x["Supermercado"], x["Distância (m)"]))
    return out


@st.cache_data(ttl=900, show_spinner=False)
def buscar_nome_regiao_gps(lat_r, lon_r):
    try:
        r = obter_http_session().get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat_r, "lon": lon_r, "format": "json", "accept-language": "pt-BR"},
            timeout=6,
        )
        if r.status_code == 200:
            a = r.json().get("address", {})
            cid = a.get("city") or a.get("town") or a.get("municipality") or a.get("village") or ""
            bai = a.get("suburb") or a.get("neighbourhood") or a.get("city_district") or ""
            return f"{cid} - {bai}" if (cid and bai) else (cid or bai)
    except Exception:
        pass
    return ""


def buscar_regiao_e_mercados_proximos(lat, lon):
    regiao = buscar_nome_regiao_gps(round(float(lat), 3), round(float(lon), 3)) or "Minha Região (GPS)"
    try:
        detalhes = consultar_overpass_mercados(lat, lon, 3000)
        return regiao, resumir_mercados(detalhes), detalhes, ""
    except Exception as erro:
        return regiao, [], [], str(erro)


@st.cache_data(ttl=900, show_spinner=False)
def buscar_supermercados_por_regiao(texto, raio=3000):
    r = obter_http_session().get("https://nominatim.openstreetmap.org/search", params={"q": texto, "countrycodes": "br", "format": "json", "limit": 1, "accept-language": "pt-BR"}, timeout=6)
    if r.status_code != 200 or not r.json():
        return None, []
    lugar = r.json()[0]
    return lugar.get("display_name", texto), consultar_overpass_mercados(float(lugar["lat"]), float(lugar["lon"]), raio)


@st.cache_data(ttl=600, show_spinner=False)
def carregar_mercados():
    if supabase_ativo():
        rows = sb_req("GET", "supermercados", params={"select": "regiao,nome"}) or []
        if rows:
            mapa = {}
            for r in rows:
                mapa.setdefault(r["regiao"], set()).add(r["nome"])
            return {k: sorted(v) for k, v in mapa.items()}
        iniciais = [{"regiao": "Centro (Exemplo)", "nome": m} for m in ("Atacadão", "Carrefour", "Supermercado Local")]
        sb_req("POST", "supermercados", params={"on_conflict": "regiao,nome"}, json_data=iniciais, extra_headers={"Prefer": "resolution=ignore-duplicates"})
        return {"Centro (Exemplo)": ["Atacadão", "Carrefour", "Supermercado Local"]}

    if isinstance(dados := ler_json(ARQUIVO_MERCADOS, dict), dict) and dados:
        return dados
    iniciais = {"Centro (Exemplo)": ["Atacadão", "Carrefour", "Supermercado Local"]}
    salvar_json(ARQUIVO_MERCADOS, iniciais)
    return iniciais


def registrar_varios_mercados(regiao, nomes):
    if not (regiao := regiao.strip()) or not nomes:
        return 0
    mercados = carregar_mercados().copy()
    atual = set(mercados.get(regiao, []))
    novos = [n.strip() for n in nomes if n.strip() and n.strip() not in atual]
    if not novos and regiao in mercados:
        return 0
    if supabase_ativo():
        payload = [{"regiao": regiao, "nome": n} for n in (novos or [nomes[0].strip()])]
        sb_req("POST", "supermercados", params={"on_conflict": "regiao,nome"}, json_data=payload, extra_headers={"Prefer": "resolution=ignore-duplicates"})
    else:
        atual.update(novos)
        mercados[regiao] = sorted(atual)
        salvar_json(ARQUIVO_MERCADOS, mercados)
    carregar_mercados.clear()
    return len(novos)


def processar_leitura_gps(loc, usuario):
    if loc and loc.get("latitude") is not None and loc.get("longitude") is not None:
        lat, lon = round(float(loc["latitude"]), 4), round(float(loc["longitude"]), 4)
        if st.session_state.get("gps_ultima_leitura") != (lat, lon):
            with st.spinner("Localizando supermercados próximos..."):
                reg_g, mercs_g, det_g, err_mapa = buscar_regiao_e_mercados_proximos(lat, lon)
                if det_g:
                    registrar_varios_mercados(reg_g, [m["Supermercado"] for m in det_g])
                else:
                    salvos = carregar_mercados().get(reg_g, [])
                    mercs_g = [(m, None) for m in salvos]
                salvar_preferencias_gps(lat, lon, reg_g, usuario)
                st.session_state.update({
                    "gps_ultima_leitura": (lat, lon),
                    "gps_coords": (lat, lon),
                    "gps_regiao": reg_g,
                    "gps_mercados": mercs_g,
                    "gps_detalhes": det_g,
                    "gps_raio_atual": 3,
                    "mkt_limite_exib": 15,
                    "regiao_para_selecionar": reg_g,
                })
                if err_mapa:
                    st.session_state["msg_limite_alerta"] = f"📍 Região **{reg_g}** salva, mas os servidores de mapa estavam ocupados para buscar novos mercados agora. Toque em **Atualizar** em alguns segundos."
                else:
                    st.session_state["msg_sucesso"] = f"Localização atualizada: **{reg_g}**."
                st.rerun()


# --- Persistência de Compras, Comunidade & Pré-Lista ---
def _ler_csv_seguro(caminho, colunas, cols_num):
    if not (os.path.exists(caminho) and os.path.getsize(caminho) > 0):
        return pd.DataFrame(columns=colunas)
    df, alt = pd.read_csv(caminho), False
    for c in colunas:
        if c not in df.columns:
            alt, df[c] = True, (0.0 if c in cols_num else "")
    df = df[colunas]
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    if alt:
        df.to_csv(caminho, index=False)
    return df


def carregar_dados(usuario):
    if st.session_state.get("_ss_compras_owner") == usuario and isinstance(st.session_state.get("_ss_compras_df"), pd.DataFrame):
        return st.session_state["_ss_compras_df"]

    if supabase_ativo():
        rows = sb_req("GET", "compras", params={"usuario": f"eq.{usuario}", "select": "id,data,regiao,supermercado,produto,categoria,quantidade,preco_unitario,total", "order": "id.asc"}) or []
        if not rows:
            df = pd.DataFrame(columns=COLUNAS)
        else:
            df = pd.DataFrame([{
                "Data": r.get("data", ""), "Região": r.get("regiao", ""), "Supermercado": r.get("supermercado", ""),
                "Produto": r.get("produto", ""), "Categoria": r.get("categoria", "Outros"),
                "Quantidade": r.get("quantidade", 1), "Preço Unitário": r.get("preco_unitario", 0.0), "Total": r.get("total", 0.0),
            } for r in rows], index=[r["id"] for r in rows])
            for c in ("Quantidade", "Preço Unitário", "Total"):
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
            df = df[COLUNAS]
    else:
        df = _ler_csv_seguro(obter_arquivo_usuario(usuario, "compras.csv"), COLUNAS, ["Quantidade", "Preço Unitário", "Total"])

    st.session_state["_ss_compras_df"] = df
    st.session_state["_ss_compras_owner"] = usuario
    st.session_state["_ss_compras_ver"] = st.session_state.get("_ss_compras_ver", 0) + 1
    return df


def _invalidar_proc_compras():
    st.session_state["_ss_compras_ver"] = st.session_state.get("_ss_compras_ver", 0) + 1
    st.session_state.pop("_ss_compras_proc", None)


def obter_compras_com_datas(usuario):
    df = carregar_dados(usuario)
    ver = st.session_state.get("_ss_compras_ver", 0)
    if (
        st.session_state.get("_ss_compras_owner") == usuario
        and st.session_state.get("_ss_compras_proc_ver") == ver
        and isinstance(st.session_state.get("_ss_compras_proc"), tuple)
    ):
        return st.session_state["_ss_compras_proc"]

    if df.empty:
        res = (df, pd.DataFrame(columns=COLUNAS))
    else:
        df_c = df.copy()
        df_c["Data_dt"] = pd.to_datetime(df_c["Data"], errors="coerce")
        df_v = df_c.dropna(subset=["Data_dt"]).copy()
        if not df_v.empty:
            df_v["Mês"] = df_v["Data_dt"].dt.strftime("%Y-%m")
        res = (df_c, df_v)

    st.session_state["_ss_compras_proc"] = res
    st.session_state["_ss_compras_proc_ver"] = ver
    return res


def obter_gasto_mes_atual(usuario, mes_ref):
    _, df_v = obter_compras_com_datas(usuario)
    return 0.0 if df_v.empty else float(df_v.loc[df_v["Mês"] == mes_ref, "Total"].sum())


def salvar_compra_usuario(usuario, nova_df):
    df_at = carregar_dados(usuario)
    if supabase_ativo():
        payload = [{
            "usuario": usuario, "data": str(r["Data"]), "regiao": str(r["Região"]), "supermercado": str(r["Supermercado"]),
            "produto": str(r["Produto"]), "categoria": str(r["Categoria"]), "quantidade": int(r["Quantidade"]),
            "preco_unitario": float(r["Preço Unitário"]), "total": float(r["Total"]),
        } for r in nova_df.to_dict("records")]
        resp = sb_req("POST", "compras", json_data=payload, extra_headers={"Prefer": "return=representation"}) or []
        novos_ids = [r["id"] for r in resp if "id" in r]
    else:
        inicio = len(df_at)
        novos_ids = list(range(inicio, inicio + len(nova_df)))
        pd.concat([df_at, nova_df], ignore_index=True).to_csv(obter_arquivo_usuario(usuario, "compras.csv"), index=False)

    if len(novos_ids) == len(nova_df):
        nova_cop = nova_df.copy()
        nova_cop.index = novos_ids
        st.session_state["_ss_compras_df"] = pd.concat([df_at, nova_cop]) if not df_at.empty else nova_cop
    else:
        st.session_state.pop("_ss_compras_df", None)
    _invalidar_proc_compras()
    return novos_ids


def atualizar_compra_usuario(usuario, idx_edit, dt_iso, merc, prod, cat, qtd, preco):
    v_tot = float(qtd) * float(preco)
    if supabase_ativo():
        sb_req("PATCH", "compras", params={"id": f"eq.{int(idx_edit)}", "usuario": f"eq.{usuario}"}, json_data={
            "data": dt_iso, "supermercado": merc, "produto": prod, "categoria": cat,
            "quantidade": int(qtd), "preco_unitario": float(preco), "total": v_tot,
        })
    df_edit = carregar_dados(usuario).copy()
    if idx_edit in df_edit.index:
        df_edit.loc[idx_edit, ["Data", "Supermercado", "Produto", "Categoria", "Quantidade", "Preço Unitário", "Total"]] = [dt_iso, merc, prod, cat, int(qtd), float(preco), v_tot]
        st.session_state["_ss_compras_df"] = df_edit
        if not supabase_ativo():
            df_edit[COLUNAS].to_csv(obter_arquivo_usuario(usuario, "compras.csv"), index=False)
    _invalidar_proc_compras()


def excluir_compras_usuario(usuario, ids=None, tudo=False):
    if supabase_ativo():
        if tudo:
            sb_req("DELETE", "compras", params={"usuario": f"eq.{usuario}"})
        elif ids:
            sb_req("DELETE", "compras", params={"usuario": f"eq.{usuario}", "id": f"in.({','.join(str(int(i)) for i in ids)})"})
    cam = obter_arquivo_usuario(usuario, "compras.csv")
    if tudo:
        if not supabase_ativo() and os.path.exists(cam):
            os.remove(cam)
        st.session_state["_ss_compras_df"] = pd.DataFrame(columns=COLUNAS)
    elif ids:
        df_c = carregar_dados(usuario)
        df_novo = df_c.drop(index=[i for i in ids if i in df_c.index])[COLUNAS]
        if not supabase_ativo():
            df_novo.reset_index(drop=True, inplace=True)
            df_novo.to_csv(cam, index=False)
            ids_set = set(ids)
            if sess_ids := st.session_state.get("compra_sessao_ids", []):
                st.session_state["compra_sessao_ids"] = [sid - sum(1 for d in ids_set if d < sid) for sid in sess_ids if sid not in ids_set]
        st.session_state["_ss_compras_df"] = df_novo
    _invalidar_proc_compras()


@st.cache_data(ttl=600, show_spinner=False)
def carregar_comunidade_ordenada():
    if supabase_ativo():
        rows = sb_req("GET", "precos_comunidade", params={"select": "data,regiao,supermercado,produto,categoria,preco_unitario,usuario_nome", "order": "preco_unitario.asc,id.desc", "limit": "500"}) or []
        if not rows:
            return pd.DataFrame(columns=COLUNAS_COMUNIDADE)
        df = pd.DataFrame([{
            "Data": r.get("data", ""), "Região": r.get("regiao", ""), "Supermercado": r.get("supermercado", ""),
            "Produto": r.get("produto", ""), "Categoria": r.get("categoria", "Outros"),
            "Preço Unitário": r.get("preco_unitario", 0.0), "Usuário": r.get("usuario_nome", ""),
        } for r in rows])
        df["Preço Unitário"] = pd.to_numeric(df["Preço Unitário"], errors="coerce").fillna(0.0)
        df = df[COLUNAS_COMUNIDADE]
    else:
        df = _ler_csv_seguro(ARQUIVO_COMUNIDADE, COLUNAS_COMUNIDADE, ["Preço Unitário"])

    if df.empty:
        return df
    df = df.copy()
    df["Data_dt"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Prod_norm"] = df["Produto"].map(normalizar_texto)
    df["Merc_norm"] = df["Supermercado"].map(normalizar_texto)
    return df.sort_values(by=["Data_dt", "Preço Unitário"], ascending=[False, True]).reset_index(drop=True)


def salvar_preco_comunidade(nova_df):
    if supabase_ativo():
        payload = [{
            "data": str(r["Data"]), "regiao": str(r["Região"]), "supermercado": str(r["Supermercado"]),
            "produto": str(r["Produto"]), "categoria": str(r["Categoria"]),
            "preco_unitario": float(r["Preço Unitário"]), "usuario_nome": str(r["Usuário"]),
        } for r in nova_df.to_dict("records")]
        sb_req("POST", "precos_comunidade", json_data=payload)
    else:
        ant = _ler_csv_seguro(ARQUIVO_COMUNIDADE, COLUNAS_COMUNIDADE, ["Preço Unitário"])
        pd.concat([ant, nova_df], ignore_index=True).to_csv(ARQUIVO_COMUNIDADE, index=False)
    carregar_comunidade_ordenada.clear()


def limpar_comunidade():
    if supabase_ativo():
        sb_req("DELETE", "precos_comunidade", params={"id": "gt.0"})
    elif os.path.exists(ARQUIVO_COMUNIDADE):
        os.remove(ARQUIVO_COMUNIDADE)
    carregar_comunidade_ordenada.clear()


def carregar_pre_lista(dono_lista):
    if st.session_state.get("_ss_pre_lista_owner") == dono_lista and isinstance(st.session_state.get("_ss_pre_lista_df"), pd.DataFrame):
        return st.session_state["_ss_pre_lista_df"]

    if supabase_ativo():
        rows = sb_req("GET", "pre_lista", params={"usuario": f"eq.{dono_lista}", "select": "id,produto,quantidade,categoria,comprado", "order": "criado_em.asc"}) or []
        if not rows:
            df = pd.DataFrame(columns=COLUNAS_PRE_LISTA)
        else:
            df = pd.DataFrame([{
                "ID": str(r["id"]), "Produto": r.get("produto", ""), "Quantidade": int(r.get("quantidade") or 1),
                "Categoria": r.get("categoria") or "Outros", "Comprado": bool(r.get("comprado") or False),
            } for r in rows])[COLUNAS_PRE_LISTA]
    else:
        caminho = obter_arquivo_usuario(dono_lista, "pre_lista.csv")
        if not (os.path.exists(caminho) and os.path.getsize(caminho) > 0):
            df = pd.DataFrame(columns=COLUNAS_PRE_LISTA)
        else:
            df = pd.read_csv(caminho)
            for col in COLUNAS_PRE_LISTA:
                if col not in df.columns:
                    df[col] = 1 if col == "Quantidade" else (False if col == "Comprado" else ([str(uuid.uuid4()) for _ in range(len(df))] if col == "ID" else ""))
            df = df[COLUNAS_PRE_LISTA]
            df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(1).astype(int)
            df["Comprado"] = df["Comprado"].map(lambda v: str(v).strip().lower() in ("true", "1", "sim"))
            df["ID"] = df["ID"].astype(str)

    st.session_state["_ss_pre_lista_df"] = df
    st.session_state["_ss_pre_lista_owner"] = dono_lista
    return df


def adicionar_itens_pre_lista(texto, qtd, api_key, dono_lista):
    itens = [i.strip() for i in texto.split(",") if i.strip()]
    if not itens:
        return 0
    cats = identificar_categorias_em_lote(itens, api_key)
    novos_regs = [{"ID": str(uuid.uuid4()), "Produto": p, "Quantidade": max(1, int(qtd)), "Categoria": cat, "Comprado": False} for p, cat in zip(itens, cats)]
    if supabase_ativo():
        payload = [{"id": r["ID"], "usuario": dono_lista, "produto": r["Produto"], "quantidade": r["Quantidade"], "categoria": r["Categoria"], "comprado": False} for r in novos_regs]
        sb_req("POST", "pre_lista", json_data=payload)
    df_atual = carregar_pre_lista(dono_lista)
    df_novo = pd.concat([df_atual, pd.DataFrame(novos_regs, columns=COLUNAS_PRE_LISTA)], ignore_index=True)[COLUNAS_PRE_LISTA]
    st.session_state["_ss_pre_lista_df"] = df_novo
    if not supabase_ativo():
        df_novo.to_csv(obter_arquivo_usuario(dono_lista, "pre_lista.csv"), index=False)
    return len(itens)


def copiar_itens_para_familia(usuario, dono_destino):
    df_orig = carregar_pre_lista(usuario)
    df_pend = df_orig[~df_orig["Comprado"]] if not df_orig.empty else df_orig
    if df_pend.empty:
        return 0
    novos_regs = [{"ID": str(uuid.uuid4()), "Produto": r["Produto"], "Quantidade": max(1, int(r["Quantidade"])), "Categoria": r["Categoria"] or "Outros", "Comprado": False} for r in df_pend.to_dict("records")]
    if supabase_ativo():
        payload = [{"id": r["ID"], "usuario": dono_destino, "produto": r["Produto"], "quantidade": r["Quantidade"], "categoria": r["Categoria"], "comprado": False} for r in novos_regs]
        sb_req("POST", "pre_lista", json_data=payload)
    else:
        df_dest = carregar_pre_lista(dono_destino)
        df_novo = pd.concat([df_dest, pd.DataFrame(novos_regs, columns=COLUNAS_PRE_LISTA)], ignore_index=True)[COLUNAS_PRE_LISTA]
        df_novo.to_csv(obter_arquivo_usuario(dono_destino, "pre_lista.csv"), index=False)
    return len(novos_regs)


def atualizar_item_pre_lista(dono_lista, item_id, **campos):
    if supabase_ativo():
        mapa = {"Produto": "produto", "Quantidade": "quantidade", "Categoria": "categoria", "Comprado": "comprado"}
        sb_req("PATCH", "pre_lista", params={"id": f"eq.{item_id}", "usuario": f"eq.{dono_lista}"}, json_data={mapa[k]: v for k, v in campos.items() if k in mapa})
    df_pre = carregar_pre_lista(dono_lista).copy()
    mask = df_pre["ID"] == str(item_id)
    for k, v in campos.items():
        df_pre.loc[mask, k] = v
    st.session_state["_ss_pre_lista_df"] = df_pre
    if not supabase_ativo():
        df_pre[COLUNAS_PRE_LISTA].to_csv(obter_arquivo_usuario(dono_lista, "pre_lista.csv"), index=False)


def remover_pre_lista(dono_lista, item_id=None, apenas_marcados=False, tudo=False):
    if supabase_ativo():
        if tudo:
            sb_req("DELETE", "pre_lista", params={"usuario": f"eq.{dono_lista}"})
        elif apenas_marcados:
            sb_req("DELETE", "pre_lista", params={"usuario": f"eq.{dono_lista}", "comprado": "is.true"})
        elif item_id:
            sb_req("DELETE", "pre_lista", params={"id": f"eq.{item_id}", "usuario": f"eq.{dono_lista}"})
    cp = obter_arquivo_usuario(dono_lista, "pre_lista.csv")
    if tudo:
        if not supabase_ativo() and os.path.exists(cp):
            os.remove(cp)
        st.session_state["_ss_pre_lista_df"] = pd.DataFrame(columns=COLUNAS_PRE_LISTA)
    else:
        df_pre = carregar_pre_lista(dono_lista)
        df_novo = (df_pre[~df_pre["Comprado"]] if apenas_marcados else df_pre[df_pre["ID"] != str(item_id)]).reset_index(drop=True)
        st.session_state["_ss_pre_lista_df"] = df_novo
        if not supabase_ativo():
            df_novo[COLUNAS_PRE_LISTA].to_csv(cp, index=False)


# --- Inteligência de Preços, Ranking & Funções v2.0 ---
def calcular_ranking_precos_mercados(df_com):
    if df_com.empty:
        return {}
    df = df_com.copy()
    if "Prod_norm" not in df.columns:
        df["Prod_norm"] = df["Produto"].map(normalizar_texto)
    if "Merc_norm" not in df.columns:
        df["Merc_norm"] = df["Supermercado"].map(normalizar_texto)

    df = df.sort_values(by=["Data_dt", "Preço Unitário"], ascending=[False, True], na_position="last")
    df_ult = df.drop_duplicates(subset=["Merc_norm", "Prod_norm"], keep="first").copy()

    stats_prod = df_ult.groupby("Prod_norm", as_index=False)["Preço Unitário"].agg(media="mean", minimo="min", qtd_mercados="count")
    df_m = df_ult.merge(stats_prod, on="Prod_norm", how="left")
    df_m["diff_pct"] = ((df_m["Preço Unitário"] - df_m["media"]) / df_m["media"].clip(lower=0.01)) * 100.0
    df_m["eh_menor"] = (df_m["qtd_mercados"] > 1) & (df_m["Preço Unitário"] <= df_m["minimo"] + 0.01)

    ranking = {}
    for merc_n, grp in df_m.groupby("Merc_norm"):
        comp = grp[grp["qtd_mercados"] > 1]
        indice_pct = float(comp["diff_pct"].mean()) if not comp.empty else 0.0
        ranking[merc_n] = {
            "qtd_precos": int(len(grp)),
            "wins": int(grp["eh_menor"].sum()),
            "indice_pct": indice_pct,
            "preco_medio": float(grp["Preço Unitário"].mean()),
            "tem_comparacao": not comp.empty,
            "ultima_data": grp["Data_dt"].max() if "Data_dt" in grp else pd.NaT,
        }
    return ranking


def classificar_selo_preco(info):
    if not info:
        return "🏷️ Sem preços ainda", "listai-pill-muted"
    idx = info["indice_pct"]
    if not info["tem_comparacao"]:
        return f"🏷️ {info['qtd_precos']} preço(s)", "listai-pill-muted"
    if idx <= -2.0:
        return f"💚 {abs(idx):.0f}% mais barato", "listai-pill-best"
    if idx >= 2.0:
        return f"💸 +{idx:.0f}% acima da média", "listai-pill-high"
    return "⚖️ Preço na média", "listai-pill-mid"


def _casar_item_mercado(it_n, tokens, prods_merc):
    melhor, melhor_score = None, (99, 999, 999999.0)
    for pm in prods_merc:
        pn = pm["norm"]
        if pn == it_n:
            sc = (0, len(pn), pm["preco"])
        elif re.search(rf"\b{re.escape(it_n)}\b", pn):
            sc = (1, len(pn), pm["preco"])
        elif all(re.search(rf"\b{re.escape(t)}\b", pn) for t in tokens):
            sc = (2, len(pn), pm["preco"])
        elif it_n in pn or pn in it_n:
            sc = (3, len(pn), pm["preco"])
        else:
            continue
        if sc < melhor_score:
            melhor_score, melhor = sc, pm
    return melhor


def comparar_lista_nos_mercados(df_pend, df_com, regiao_alvo=""):
    if df_pend.empty or df_com.empty:
        return [], ""

    df_base = df_com[df_com["Região"] == regiao_alvo] if (regiao_alvo and (df_com["Região"] == regiao_alvo).any()) else df_com
    escopo = regiao_alvo if (regiao_alvo and (df_com["Região"] == regiao_alvo).any()) else "Todas as regiões"

    df_ult = (
        df_base.sort_values(by=["Data_dt", "Preço Unitário"], ascending=[False, True], na_position="last")
        .drop_duplicates(subset=["Merc_norm", "Prod_norm"], keep="first")
    )

    itens_lista = [
        {"nome": str(r["Produto"]), "norm": normalizar_texto(r["Produto"]), "qtd": max(1, int(r["Quantidade"]))}
        for r in df_pend.to_dict("records")
        if str(r.get("Produto", "")).strip()
    ]
    if not itens_lista:
        return [], escopo

    resultados = []
    for (_, reg_m), grp in df_ult.groupby(["Merc_norm", "Região"]):
        merc_nome = str(grp.iloc[0]["Supermercado"] or "Mercado")
        prods_merc = [{"prod": str(r["Produto"]), "norm": str(r["Prod_norm"]), "preco": float(r["Preço Unitário"])} for r in grp.to_dict("records")]
        encontrados, faltando, total_est = [], [], 0.0

        for it in itens_lista:
            it_n = it["norm"]
            tokens = [w for w in it_n.split() if len(w) >= 2] or [it_n]
            if melhor := _casar_item_mercado(it_n, tokens, prods_merc):
                sub = it["qtd"] * melhor["preco"]
                total_est += sub
                encontrados.append({"item": it["nome"], "banco": melhor["prod"], "qtd": it["qtd"], "preco": melhor["preco"], "subtotal": sub})
            else:
                faltando.append(it["nome"])

        if encontrados:
            resultados.append({
                "mercado": merc_nome, "regiao": str(reg_m or "-"),
                "qtd_enc": len(encontrados), "qtd_total": len(itens_lista),
                "total": total_est, "itens": encontrados, "faltando": faltando,
            })

    resultados.sort(key=lambda r: (-r["qtd_enc"], r["total"], r["mercado"].lower()))
    return resultados, escopo


def calcular_cesta_dividida(df_pend, df_com, regiao_alvo="", res_comp=None):
    """v2.0: Verifica se dividir a compra entre 2 mercados gera economia real (>= R$ 1,50)."""
    if df_pend.empty or df_com.empty or len(df_pend) < 2:
        return None
    if res_comp is None:
        res_comp, _ = comparar_lista_nos_mercados(df_pend, df_com, regiao_alvo)
    if len(res_comp) < 2:
        return None

    vencedor = res_comp[0]
    if vencedor["qtd_enc"] < 2:
        return None

    # Mapeia preços por mercado para os itens que o vencedor cobre
    itens_v = {it["item"]: it["subtotal"] for it in vencedor["itens"]}
    por_merc = {r["mercado"]: {it["item"]: it for it in r["itens"]} for r in res_comp}
    nomes_m = list(por_merc.keys())

    melhor_par, melhor_tot = None, vencedor["total"]
    for i in range(len(nomes_m)):
        for j in range(i + 1, len(nomes_m)):
            m1, m2 = nomes_m[i], nomes_m[j]
            d1, d2 = por_merc[m1], por_merc[m2]
            if not all((it in d1 or it in d2) for it in itens_v):
                continue
            it_1, it_2, tot_par = [], [], 0.0
            for it_nome in itens_v:
                c1, c2 = d1.get(it_nome), d2.get(it_nome)
                if c1 and (not c2 or c1["subtotal"] <= c2["subtotal"]):
                    it_1.append(c1)
                    tot_par += c1["subtotal"]
                else:
                    it_2.append(c2)
                    tot_par += c2["subtotal"]
            if it_1 and it_2 and tot_par < melhor_tot:
                melhor_tot = tot_par
                melhor_par = (m1, it_1, m2, it_2, tot_par)

    if not melhor_par:
        return None
    m1, it_1, m2, it_2, tot_div = melhor_par
    economia = vencedor["total"] - tot_div
    if economia < 1.50:
        return None

    return {
        "mercado_1": m1, "itens_1": it_1, "sub_1": sum(x["subtotal"] for x in it_1),
        "mercado_2": m2, "itens_2": it_2, "sub_2": sum(x["subtotal"] for x in it_2),
        "total_dividido": tot_div, "total_unico": vencedor["total"],
        "economia": economia, "qtd_enc": vencedor["qtd_enc"], "qtd_total": vencedor["qtd_total"],
    }


def listar_produtos_evolucao(df_c, df_com, regiao_alvo=""):
    """v2.0: Lista produtos disponíveis para análise de histórico/inflação."""
    contagem = {}
    if not df_c.empty:
        for p, cnt in df_c["Produto"].dropna().value_counts().items():
            contagem[str(p).strip()] = contagem.get(str(p).strip(), 0) + int(cnt) * 2
    if not df_com.empty:
        df_b = df_com[df_com["Região"] == regiao_alvo] if (regiao_alvo and (df_com["Região"] == regiao_alvo).any()) else df_com
        for p, cnt in df_b["Produto"].dropna().value_counts().head(40).items():
            contagem[str(p).strip()] = contagem.get(str(p).strip(), 0) + int(cnt)
    return [p for p, _ in sorted(contagem.items(), key=lambda x: (-x[1], x[0].lower())) if p]


def analisar_evolucao_produto(df_c, df_com, termo, regiao_alvo=""):
    """v2.0: Monta a série histórica de preços de um produto (suas compras + comunidade)."""
    t_norm = normalizar_texto(termo)
    if not t_norm:
        return pd.DataFrame(), None

    registros, vistos = [], set()
    fontes = []
    if not df_c.empty:
        fontes.append(("Minha compra", df_c))
    if not df_com.empty:
        df_b = df_com[df_com["Região"] == regiao_alvo] if (regiao_alvo and (df_com["Região"] == regiao_alvo).any()) else df_com
        fontes.append(("Comunidade", df_b))

    for origem, df_src in fontes:
        for r in df_src.to_dict("records"):
            pn = normalizar_texto(r.get("Produto", ""))
            preco = float(r.get("Preço Unitário") or 0.0)
            if preco <= 0 or (t_norm not in pn and pn not in t_norm):
                continue
            dt_str = str(r.get("Data") or "")[:10]
            merc = str(r.get("Supermercado") or "Não informado")
            chave = (dt_str, normalizar_texto(merc), round(preco, 2))
            if chave in vistos:
                continue
            vistos.add(chave)
            registros.append({
                "Data": dt_str,
                "Data_dt": pd.to_datetime(dt_str, errors="coerce"),
                "Produto": str(r.get("Produto") or termo),
                "Supermercado": merc,
                "Preço": preco,
                "Origem": origem,
            })

    if not registros:
        return pd.DataFrame(), None

    df_out = pd.DataFrame(registros).dropna(subset=["Data_dt"]).sort_values(by=["Data_dt", "Preço"], ascending=[True, True]).reset_index(drop=True)
    if df_out.empty:
        return pd.DataFrame(), None

    primeiro, ultimo = float(df_out.iloc[0]["Preço"]), float(df_out.iloc[-1]["Preço"])
    var_pct = ((ultimo - primeiro) / max(primeiro, 0.01)) * 100.0 if len(df_out) >= 2 else 0.0
    melhor_row = df_out.sort_values(by="Preço", ascending=True).iloc[0]
    resumo = {
        "minimo": float(df_out["Preço"].min()),
        "maximo": float(df_out["Preço"].max()),
        "medio": float(df_out["Preço"].mean()),
        "ultimo": ultimo,
        "variacao_pct": var_pct,
        "melhor_mercado": str(melhor_row["Supermercado"]),
        "qtd": len(df_out),
    }
    return df_out, resumo


def detectar_alertas_oferta(usuario, df_com, regiao_alvo="", favoritos=None):
    """v2.0: Detecta ofertas abaixo da média para favoritos, lista pendente e itens mais comprados."""
    if df_com.empty:
        return []

    df_base = df_com[df_com["Região"] == regiao_alvo] if (regiao_alvo and (df_com["Região"] == regiao_alvo).any()) else df_com
    df_ult = (
        df_base.sort_values(by=["Data_dt", "Preço Unitário"], ascending=[False, True], na_position="last")
        .drop_duplicates(subset=["Merc_norm", "Prod_norm"], keep="first")
    )
    stats = df_base.groupby("Prod_norm", as_index=False)["Preço Unitário"].agg(media="mean", qtd="count")
    stats_map = {r["Prod_norm"]: (float(r["media"]), int(r["qtd"])) for r in stats.to_dict("records")}

    alvos = []
    vistos_t = set()
    for f in (favoritos or []):
        fn = normalizar_texto(f)
        if fn and fn not in vistos_t:
            vistos_t.add(fn)
            alvos.append((f, fn, True))

    df_pre = carregar_pre_lista(obter_dono_lista(usuario))
    if not df_pre.empty:
        for p in df_pre[~df_pre["Comprado"]]["Produto"].dropna().tolist():
            pn = normalizar_texto(p)
            if pn and pn not in vistos_t:
                vistos_t.add(pn)
                alvos.append((p, pn, False))

    df_u = carregar_dados(usuario)
    if not df_u.empty:
        for p in df_u["Produto"].dropna().value_counts().head(8).index.tolist():
            pn = normalizar_texto(p)
            if pn and pn not in vistos_t:
                vistos_t.add(pn)
                alvos.append((p, pn, False))

    prods_base = df_ult.to_dict("records")
    alertas, vistos_prod = [], set()
    for termo, t_n, eh_fav in alvos:
        melhor = None
        for r in prods_base:
            pn = str(r.get("Prod_norm") or "")
            if t_n in pn or pn in t_n:
                if melhor is None or float(r["Preço Unitário"]) < float(melhor["Preço Unitário"]):
                    melhor = r
        if not melhor:
            continue
        pn_m = str(melhor["Prod_norm"])
        if pn_m in vistos_prod:
            continue
        media, qtd_r = stats_map.get(pn_m, (float(melhor["Preço Unitário"]), 1))
        preco = float(melhor["Preço Unitário"])
        desc_pct = ((media - preco) / max(media, 0.01)) * 100.0
        if (qtd_r >= 2 and desc_pct >= 5.0) or eh_fav:
            vistos_prod.add(pn_m)
            alertas.append({
                "termo": termo,
                "produto": str(melhor["Produto"]),
                "mercado": str(melhor["Supermercado"] or "Mercado"),
                "regiao": str(melhor["Região"] or "-"),
                "preco": preco,
                "media": media,
                "desconto_pct": max(0.0, desc_pct),
                "economia": max(0.0, media - preco),
                "eh_favorito": eh_fav,
            })

    alertas.sort(key=lambda a: (0 if a["eh_favorito"] else 1, -a["desconto_pct"], -a["economia"]))
    return alertas[:6]


def montar_lista_mercados_classificada(regiao_alvo, detalhes_gps, mercados_salvos, df_com):
    df_reg = df_com[df_com["Região"] == regiao_alvo] if (not df_com.empty and regiao_alvo) else df_com
    if df_reg.empty:
        df_reg = df_com
    ranking = calcular_ranking_precos_mercados(df_reg)

    por_nome = {}
    for item in (detalhes_gps or []):
        mn = normalizar_texto(item["Supermercado"])
        if mn not in por_nome or (item.get("Distância (m)") or 999999) < (por_nome[mn].get("Distância (m)") or 999999):
            por_nome[mn] = dict(item)

    for nome_s in (mercados_salvos or []):
        mn = normalizar_texto(nome_s)
        if mn not in por_nome:
            por_nome[mn] = {"Supermercado": nome_s, "Tipo": "Cadastrado na região", "Endereço": regiao_alvo or "-", "Distância (m)": None, "lat": None, "lon": None}

    if not df_reg.empty:
        for nome_c in df_reg["Supermercado"].dropna().unique():
            mn = normalizar_texto(nome_c)
            if mn and mn not in por_nome:
                por_nome[mn] = {"Supermercado": nome_c, "Tipo": "Com preços registrados", "Endereço": regiao_alvo or "-", "Distância (m)": None, "lat": None, "lon": None}

    lista_final = []
    for mn, item in por_nome.items():
        item["preco_info"] = ranking.get(mn)
        lista_final.append(item)

    def chave_ordem(x):
        info = x.get("preco_info")
        dist_ord = x.get("Distância (m)") if x.get("Distância (m)") is not None else 999999
        if info and info.get("tem_comparacao"):
            return (0, info["indice_pct"], -info["wins"], dist_ord, x["Supermercado"].lower())
        if info:
            return (1, info["preco_medio"], -info["qtd_precos"], dist_ord, x["Supermercado"].lower())
        return (2, 0.0, 0, dist_ord, x["Supermercado"].lower())

    return sorted(lista_final, key=chave_ordem)