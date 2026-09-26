"""Entrypoint do PIPPA - Emendas Parlamentares.

Uso:
    python gerar_dashboard.py                  # pipeline completo, todos os anos
    python gerar_dashboard.py --ano 2025       # filtra por ano
    python gerar_dashboard.py --skip-dashboard # so coleta e processa, sem gerar HTML
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline import run_pipeline, PROCESSED_DIR, OUTPUT_DIR
from dashboard_builder import build_all_data
from html_renderer import render_dashboard

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pippa-emendas")


def main():
    parser = argparse.ArgumentParser(description="PIPPA - Emendas Parlamentares")
    parser.add_argument("--ano", type=int, default=None, help="Filtrar por ano específico")
    parser.add_argument("--skip-dashboard", action="store_true", help="Pular geração do dashboard HTML")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("PIPPA - Emendas Parlamentares")
    logger.info("=" * 60)

    df, quality_flags, stats = run_pipeline(ano_filtro=args.ano)

    logger.info("=" * 60)
    logger.info("RESUMO DO PIPELINE")
    logger.info("=" * 60)
    logger.info("Total de emendas: %d", stats.total_emendas)
    logger.info("Autores únicos: %d", stats.total_autores_unicos)
    logger.info("Match exato: %d", stats.match_exato)
    logger.info("Match fuzzy: %d", stats.match_fuzzy)
    logger.info("Não encontrado: %d", stats.match_nao_encontrado)
    logger.info("Não aplicável (bancada/comissão/relator): %d", stats.match_nao_aplicavel)
    logger.info("Alertas de qualidade: %d", stats.quality_flags_alerta)
    logger.info("Críticos de qualidade: %d", stats.quality_flags_critico)

    if not args.skip_dashboard:
        logger.info("=" * 60)
        logger.info("GERANDO DASHBOARD")
        logger.info("=" * 60)

        sufixo = f"_{args.ano}" if args.ano else "_completo"

        df_estado = pd.read_parquet(PROCESSED_DIR / f"agg_por_estado{sufixo}.parquet")
        df_municipio = pd.read_parquet(PROCESSED_DIR / f"agg_por_municipio{sufixo}.parquet")
        df_autor = pd.read_parquet(PROCESSED_DIR / f"agg_por_autor{sufixo}.parquet")
        df_partido = pd.read_parquet(PROCESSED_DIR / f"agg_por_partido{sufixo}.parquet")
        df_tipo = pd.read_parquet(PROCESSED_DIR / f"agg_por_tipo{sufixo}.parquet")
        df_serie = pd.read_parquet(PROCESSED_DIR / f"agg_serie_temporal{sufixo}.parquet")
        df_emendas = pd.read_parquet(PROCESSED_DIR / f"emendas_enriquecidas{sufixo}.parquet")

        funcao_path = PROCESSED_DIR / f"agg_por_funcao{sufixo}.parquet"
        df_funcao = pd.read_parquet(funcao_path) if funcao_path.exists() else None

        data = build_all_data(df_estado, df_municipio, df_autor, df_partido, df_tipo, df_serie, df_emendas, df_funcao)
        html = render_dashboard(data, stats, quality_flags, df_estado, args.ano)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"pippa_emendas{sufixo}.html"
        output_path.write_text(html, encoding="utf-8")
        logger.info("Dashboard salvo: %s (%.1f KB)", output_path, output_path.stat().st_size / 1024)

    logger.info("Pipeline concluído com sucesso.")


if __name__ == "__main__":
    main()
