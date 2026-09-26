"""Pipeline de dados do PIPPA - Emendas Parlamentares.

Orquestra: coleta → enriquecimento → validacao cruzada → persistencia.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from collectors import (
    CamaraApiCollector,
    PortalTransparenciaCollector,
    SenadoApiCollector,
    TesouroTransparenteCollector,
)
from config import DIVERGENCIA_ALERTA_PCT, DIVERGENCIA_CRITICO_PCT
from enrichment import IbgeNormalizer, PartidoResolver
from models import MatchConfianca, PipelineStats, QualityFlag

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def run_pipeline(ano_filtro: int | None = None) -> tuple[pd.DataFrame, list[QualityFlag], PipelineStats]:
    """Executa o pipeline completo e retorna (df_enriquecido, quality_flags, stats)."""

    # --- Fase 1: Coleta ---
    logger.info("=" * 60)
    logger.info("FASE 1 — COLETA")
    logger.info("=" * 60)

    df_emendas = PortalTransparenciaCollector().collect()
    df_repasses = TesouroTransparenteCollector().collect()

    # --- Fase 2: Enriquecimento ---
    logger.info("=" * 60)
    logger.info("FASE 2 — ENRIQUECIMENTO")
    logger.info("=" * 60)

    parlamentares_camara = CamaraApiCollector().collect()
    parlamentares_senado = SenadoApiCollector().collect()
    todos_parlamentares = parlamentares_camara + parlamentares_senado

    resolver = PartidoResolver(todos_parlamentares)
    df_emendas = resolver.enriquecer(df_emendas)

    normalizer = IbgeNormalizer()
    df_emendas = normalizer.normalizar(df_emendas)

    # --- Fase 3: Filtro por ano (opcional) ---
    if ano_filtro:
        logger.info("Filtrando por ano: %d", ano_filtro)
        df_emendas = df_emendas[df_emendas["ano"] == ano_filtro]

    # --- Fase 4: Validacao cruzada ---
    logger.info("=" * 60)
    logger.info("FASE 4 — VALIDAÇÃO CRUZADA")
    logger.info("=" * 60)

    quality_flags = _validar_cruzamento(df_emendas, df_repasses)

    # --- Fase 5: Persistencia ---
    logger.info("=" * 60)
    logger.info("FASE 5 — PERSISTÊNCIA")
    logger.info("=" * 60)

    stats = _calcular_stats(df_emendas, quality_flags)
    _salvar(df_emendas, quality_flags, stats, ano_filtro)

    return df_emendas, quality_flags, stats


def _validar_cruzamento(df_portal: pd.DataFrame, df_tesouro: pd.DataFrame) -> list[QualityFlag]:
    """Compara totais pagos entre Portal da Transparência e Tesouro Transparente."""
    flags = []

    if "valor_pago" not in df_portal.columns or "valor" not in df_tesouro.columns:
        logger.warning("Colunas de valor não encontradas para validação cruzada")
        return flags

    agg_portal = (
        df_portal
        .groupby(["uf_destino", "ano"], dropna=False)["valor_pago"]
        .sum()
    )

    agg_tesouro = (
        df_tesouro
        .groupby(["uf", "ano"], dropna=False)["valor"]
        .sum()
    )

    for (uf, ano), valor_p in agg_portal.items():
        if pd.isna(uf) or pd.isna(ano):
            continue

        valor_t = agg_tesouro.get((uf, int(ano)), 0)
        if valor_t == 0:
            continue

        div = abs(valor_p - valor_t) / valor_t * 100

        if div < DIVERGENCIA_ALERTA_PCT:
            status = "OK"
        elif div < DIVERGENCIA_CRITICO_PCT:
            status = "ALERTA"
        else:
            status = "CRITICO"

        flags.append(QualityFlag(
            uf=str(uf),
            ano=int(ano),
            valor_portal=round(valor_p, 2),
            valor_tesouro=round(valor_t, 2),
            divergencia_pct=round(div, 2),
            status=status,
        ))

    alertas = sum(1 for f in flags if f.status == "ALERTA")
    criticos = sum(1 for f in flags if f.status == "CRITICO")
    logger.info(
        "Validação cruzada: %d pares UF/ano verificados, %d alertas, %d críticos",
        len(flags), alertas, criticos,
    )

    return flags


def _calcular_stats(df: pd.DataFrame, flags: list[QualityFlag]) -> PipelineStats:
    confianca = df["match_confianca"].value_counts() if "match_confianca" in df.columns else pd.Series()
    return PipelineStats(
        total_emendas=len(df),
        total_autores_unicos=df["nome_autor"].nunique() if "nome_autor" in df.columns else 0,
        match_exato=int(confianca.get(MatchConfianca.EXATO.value, 0)),
        match_fuzzy=int(confianca.get(MatchConfianca.FUZZY.value, 0)),
        match_nao_encontrado=int(confianca.get(MatchConfianca.NAO_ENCONTRADO.value, 0)),
        match_nao_aplicavel=int(confianca.get(MatchConfianca.NAO_APLICAVEL.value, 0)),
        quality_flags_alerta=sum(1 for f in flags if f.status == "ALERTA"),
        quality_flags_critico=sum(1 for f in flags if f.status == "CRITICO"),
    )


def _salvar(
    df: pd.DataFrame,
    flags: list[QualityFlag],
    stats: PipelineStats,
    ano_filtro: int | None,
) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sufixo = f"_{ano_filtro}" if ano_filtro else "_completo"

    parquet_path = PROCESSED_DIR / f"emendas_enriquecidas{sufixo}.parquet"
    df.to_parquet(parquet_path, index=False)
    logger.info("DataFrame salvo: %s (%d linhas)", parquet_path, len(df))

    quality_path = OUTPUT_DIR / f"quality_report{sufixo}.json"
    quality_data = {
        "stats": stats.to_dict(),
        "flags": [f.to_dict() for f in flags],
    }
    quality_path.write_text(
        json.dumps(quality_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Relatório de qualidade salvo: %s", quality_path)

    _salvar_agregacoes(df, sufixo)


def _salvar_agregacoes(df: pd.DataFrame, sufixo: str) -> None:
    colunas_valor = [
        "valor_empenhado", "valor_liquidado", "valor_pago",
        "valor_rp_inscrito", "valor_rp_cancelado", "valor_rp_pago",
    ]
    colunas_valor_presentes = [c for c in colunas_valor if c in df.columns]
    agg_spec = {c: (c, "sum") for c in colunas_valor_presentes}
    agg_spec["qtd_emendas"] = ("codigo_emenda", "count")

    agrupamentos = {
        "por_estado": ["uf_destino", "ano"],
        "por_municipio": ["cod_ibge_municipio", "municipio", "uf_destino"],
        "por_autor": ["nome_autor", "partido", "uf_autor", "match_confianca"],
        "por_partido": ["partido", "ano"],
        "por_tipo": ["tipo_emenda", "ano"],
        "por_funcao": ["funcao", "ano"],
        "serie_temporal": ["ano"],
    }

    for nome, cols in agrupamentos.items():
        cols_presentes = [c for c in cols if c in df.columns]
        if not cols_presentes:
            continue

        agg = df.groupby(cols_presentes, dropna=False).agg(**agg_spec).reset_index()

        path = PROCESSED_DIR / f"agg_{nome}{sufixo}.parquet"
        agg.to_parquet(path, index=False)
        logger.info("Agregação '%s' salva: %s (%d linhas)", nome, path, len(agg))
