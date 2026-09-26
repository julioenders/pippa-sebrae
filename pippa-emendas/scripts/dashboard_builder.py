"""Prepara dados agregados para o dashboard PIPPA - Emendas (Chart.js)."""

from __future__ import annotations

import pandas as pd
from config import UF_SIGLAS, UF_CODES


def _to_sigla(nome: str) -> str:
    """Converte nome de estado para sigla. Aceita nome completo ou sigla."""
    s = nome.strip().upper()
    if s in UF_CODES:
        return s
    norm = s.title()
    if norm in UF_SIGLAS:
        return UF_SIGLAS[norm]
    for full, sigla in UF_SIGLAS.items():
        if full.upper() == s:
            return sigla
    return nome


def fmt_reais(valor: float) -> str:
    if abs(valor) >= 1e9:
        return f"R$ {valor/1e9:,.1f} bi"
    if abs(valor) >= 1e6:
        return f"R$ {valor/1e6:,.1f} mi"
    if abs(valor) >= 1e3:
        return f"R$ {valor/1e3:,.0f} mil"
    return f"R$ {valor:,.0f}"


def build_estado_data(df_estado: pd.DataFrame) -> list[dict]:
    df = df_estado.dropna(subset=["uf_destino"])
    return [
        {
            "uf": _to_sigla(row["uf_destino"]),
            "ano": int(row["ano"]),
            "empenhado": round(float(row["valor_empenhado"]), 2),
            "pago": round(float(row.get("valor_pago", 0)), 2),
            "qtd": int(row["qtd_emendas"]),
        }
        for _, row in df.iterrows()
    ]


def build_partido_data(df_partido: pd.DataFrame) -> list[dict]:
    df = df_partido.dropna(subset=["partido"])
    return [
        {
            "partido": row["partido"],
            "ano": int(row["ano"]),
            "empenhado": round(float(row["valor_empenhado"]), 2),
            "pago": round(float(row.get("valor_pago", 0)), 2),
            "qtd": int(row["qtd_emendas"]),
        }
        for _, row in df.iterrows()
    ]


def build_autor_data(df_autor: pd.DataFrame) -> list[dict]:
    df = df_autor.copy()
    df = df[df["match_confianca"].isin(["exato", "fuzzy"])]
    df = df.sort_values("valor_empenhado", ascending=False)

    return [
        {
            "nome": row["nome_autor"],
            "partido": row.get("partido", "?"),
            "uf": row.get("uf_autor", "?"),
            "empenhado": round(float(row["valor_empenhado"]), 2),
            "pago": round(float(row.get("valor_pago", 0)), 2),
            "confianca": row["match_confianca"],
            "qtd": int(row.get("qtd_emendas", 0)),
        }
        for _, row in df.iterrows()
    ]


def build_serie_data(df_serie: pd.DataFrame) -> list[dict]:
    df = df_serie.sort_values("ano")
    return [
        {
            "ano": int(row["ano"]),
            "empenhado": round(float(row["valor_empenhado"]), 2),
            "pago": round(float(row["valor_pago"]), 2),
            "liquidado": round(float(row.get("valor_liquidado", 0)), 2),
            "qtd": int(row.get("qtd_emendas", 0)),
        }
        for _, row in df.iterrows()
    ]


def build_tipo_data(df_tipo: pd.DataFrame) -> list[dict]:
    df = df_tipo.copy()
    df["tipo_label"] = df["tipo_emenda"].str.replace("Emenda ", "").str.replace("Individual - ", "Ind. ")
    return [
        {
            "tipo": row["tipo_label"],
            "tipo_original": row["tipo_emenda"],
            "ano": int(row["ano"]),
            "empenhado": round(float(row["valor_empenhado"]), 2),
            "pago": round(float(row.get("valor_pago", 0)), 2),
            "qtd": int(row.get("qtd_emendas", 0)),
        }
        for _, row in df.iterrows()
    ]


def build_tipo_uf_data(df_emendas: pd.DataFrame) -> list[dict]:
    """Agrega tipo x ano x uf a partir das emendas enriquecidas."""
    required = {"tipo_emenda", "ano", "uf_destino", "valor_empenhado", "valor_pago"}
    if not required.issubset(set(df_emendas.columns)):
        return []

    df = df_emendas.dropna(subset=["tipo_emenda", "uf_destino"]).copy()
    df["uf_sigla"] = df["uf_destino"].apply(_to_sigla)
    df = df[df["uf_sigla"] != ""]
    df["tipo_label"] = df["tipo_emenda"].str.replace("Emenda ", "").str.replace("Individual - ", "Ind. ")

    agg = df.groupby(["tipo_label", "ano", "uf_sigla"], as_index=False).agg(
        empenhado=("valor_empenhado", "sum"),
        pago=("valor_pago", "sum"),
        qtd=("codigo_emenda", "nunique") if "codigo_emenda" in df.columns else ("valor_empenhado", "count"),
    )

    return [
        {
            "tipo": row["tipo_label"],
            "ano": int(row["ano"]),
            "uf": row["uf_sigla"],
            "empenhado": round(float(row["empenhado"]), 2),
            "pago": round(float(row["pago"]), 2),
            "qtd": int(row["qtd"]),
        }
        for _, row in agg.iterrows()
    ]


def build_funcao_data(df_funcao: pd.DataFrame) -> list[dict]:
    df = df_funcao.dropna(subset=["funcao"])
    return [
        {
            "funcao": row["funcao"],
            "ano": int(row["ano"]),
            "empenhado": round(float(row["valor_empenhado"]), 2),
            "pago": round(float(row.get("valor_pago", 0)), 2),
            "qtd": int(row["qtd_emendas"]),
        }
        for _, row in df.iterrows()
    ]


def build_funcao_uf_data(df_emendas: pd.DataFrame) -> list[dict]:
    required = {"funcao", "ano", "uf_destino", "valor_empenhado", "valor_pago"}
    if not required.issubset(set(df_emendas.columns)):
        return []

    df = df_emendas.dropna(subset=["funcao", "uf_destino"]).copy()
    df["uf_sigla"] = df["uf_destino"].apply(_to_sigla)
    df = df[df["uf_sigla"] != ""]

    agg = df.groupby(["funcao", "ano", "uf_sigla"], as_index=False).agg(
        empenhado=("valor_empenhado", "sum"),
        pago=("valor_pago", "sum"),
        qtd=("codigo_emenda", "nunique") if "codigo_emenda" in df.columns else ("valor_empenhado", "count"),
    )

    return [
        {
            "funcao": row["funcao"],
            "ano": int(row["ano"]),
            "uf": row["uf_sigla"],
            "empenhado": round(float(row["empenhado"]), 2),
            "pago": round(float(row["pago"]), 2),
            "qtd": int(row["qtd"]),
        }
        for _, row in agg.iterrows()
    ]


def build_municipio_data(df_municipio: pd.DataFrame) -> list[dict]:
    required = {"municipio", "uf_destino", "valor_empenhado", "valor_pago", "qtd_emendas"}
    if not required.issubset(set(df_municipio.columns)):
        return []

    rows = []
    for _, r in df_municipio.iterrows():
        mun = r.get("municipio")
        if pd.isna(mun) or not mun:
            continue
        rows.append({
            "municipio": str(mun),
            "uf": _to_sigla(str(r.get("uf_destino", ""))),
            "empenhado": round(float(r.get("valor_empenhado", 0)), 2),
            "pago": round(float(r.get("valor_pago", 0)), 2),
            "qtd": int(r.get("qtd_emendas", 0)),
        })
    return rows


def build_all_data(
    df_estado: pd.DataFrame,
    df_municipio: pd.DataFrame,
    df_autor: pd.DataFrame,
    df_partido: pd.DataFrame,
    df_tipo: pd.DataFrame,
    df_serie: pd.DataFrame,
    df_emendas: pd.DataFrame | None = None,
    df_funcao: pd.DataFrame | None = None,
) -> dict:
    return {
        "estados": build_estado_data(df_estado),
        "partidos": build_partido_data(df_partido),
        "autores": build_autor_data(df_autor),
        "serie": build_serie_data(df_serie),
        "tipos": build_tipo_data(df_tipo),
        "tipos_uf": build_tipo_uf_data(df_emendas) if df_emendas is not None else [],
        "funcoes": build_funcao_data(df_funcao) if df_funcao is not None else [],
        "funcoes_uf": build_funcao_uf_data(df_emendas) if df_emendas is not None else [],
        "municipios": build_municipio_data(df_municipio),
    }
