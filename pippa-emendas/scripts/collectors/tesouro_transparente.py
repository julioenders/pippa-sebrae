"""Coletor do CSV de repasses de emendas do Tesouro Transparente.

Fonte: https://www.tesourotransparente.gov.br/ckan/dataset/emendas-parlamentares-individuais-e-de-bancada
Arquivo: emendas-parlamentares.csv (~67 MB)
Encoding: Latin-1, separador ponto-e-virgula, decimais com virgula
Cobertura: 2015+
Atualizacao: mensal
Uso: validacao cruzada dos valores pagos contra o Portal da Transparencia
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache_manager import CacheManager
from collectors.base import BaseCollector
from config import (
    ANO_MINIMO,
    TESOURO_CSV_ENCODING,
    TESOURO_CSV_SEPARATOR,
    TESOURO_TRANSPARENTE_CSV_URL,
)

logger = logging.getLogger(__name__)

COLUNAS_RENOMEAR = {
    "Nome Ente": "nome_ente",
    "UF": "uf",
    "Codigo Siafi": "cod_siafi",
    "Codigo IBGE": "cod_ibge",
    "Data": "data",
    "Ano": "ano",
    "Mes": "mes",
    "Tipo Ente": "tipo_ente",
    "OB": "ordem_bancaria",
    "CNPJ do Favorecido": "cnpj_favorecido",
    "Nome Favorecido": "nome_favorecido",
    "Nome Emenda": "tipo_emenda",
    "Transferencia Especial": "transferencia_especial",
    "Categoria Economica Despesa": "categoria_despesa",
    "Valor": "valor",
}


class TesouroTransparenteCollector(BaseCollector):
    def __init__(self, cache: CacheManager | None = None):
        if cache is None:
            cache = CacheManager(
                Path(__file__).parent.parent.parent / "data" / "raw",
                ttl_seconds=7 * 24 * 3600,
            )
        super().__init__(cache)

    def collect(self, **kwargs) -> pd.DataFrame:
        """Baixa e processa o CSV de repasses do Tesouro Transparente."""
        csv_path = self.cache.get_file_path("repasses_tesouro.csv")

        if not self.cache.is_fresh("repasses_tesouro.csv"):
            logger.info("Baixando CSV do Tesouro Transparente...")
            self._download(csv_path)
        else:
            logger.info("Usando CSV em cache: %s", csv_path)

        df = self._parse_csv(csv_path)
        df = self._limpar(df)
        return df

    def _download(self, output_path: Path) -> None:
        response = requests.get(TESOURO_TRANSPARENTE_CSV_URL, timeout=180, stream=True)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        logger.info("CSV salvo em %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)

    def _parse_csv(self, path: Path) -> pd.DataFrame:
        logger.info("Lendo CSV %s...", path.name)
        df = pd.read_csv(
            path,
            sep=TESOURO_CSV_SEPARATOR,
            encoding=TESOURO_CSV_ENCODING,
            dtype=str,
            low_memory=False,
        )
        logger.info("CSV lido: %d linhas, %d colunas", len(df), len(df.columns))
        return df

    def _limpar(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {}
        for col_orig, col_novo in COLUNAS_RENOMEAR.items():
            matches = [c for c in df.columns if c.strip() == col_orig]
            if matches:
                rename_map[matches[0]] = col_novo

        df = df.rename(columns=rename_map)

        if "valor" in df.columns:
            df["valor"] = (
                df["valor"]
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .astype(float)
            )

        if "ano" in df.columns:
            df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
            df = df[df["ano"] >= ANO_MINIMO]

        if "cod_ibge" in df.columns:
            df["cod_ibge"] = df["cod_ibge"].str.strip()

        logger.info(
            "Dados limpos: %d linhas, anos %s a %s",
            len(df),
            df["ano"].min() if "ano" in df.columns else "?",
            df["ano"].max() if "ano" in df.columns else "?",
        )
        return df

    def agregar_por_uf_ano(self) -> pd.DataFrame:
        """Agrega valores por UF e ano para validacao cruzada."""
        df = self.collect()
        return (
            df.groupby(["uf", "ano"], as_index=False)["valor"]
            .sum()
            .rename(columns={"valor": "valor_tesouro"})
        )
