"""Coletor do CSV de Emendas Parlamentares do Portal da Transparencia (CGU).

Fonte: https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares
Arquivo: EmendasParlamentares.zip (~32 MB) contendo EmendasParlamentares.csv (~47 MB, ~94k linhas)
Encoding: Latin-1, separador ponto-e-virgula, decimais com virgula
Cobertura: 2014+ (usamos 2015+ por qualidade dos dados)
Atualizacao: diaria
"""

from __future__ import annotations

import io
import logging
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache_manager import CacheManager
from collectors.base import BaseCollector
from config import (
    ANO_MINIMO,
    PORTAL_CSV_ENCODING,
    PORTAL_CSV_SEPARATOR,
    PORTAL_TRANSPARENCIA_CSV_URL,
    UF_REGIAO,
)

logger = logging.getLogger(__name__)

COLUNAS_RENOMEAR = {
    "Código da Emenda": "codigo_emenda",
    "Ano da Emenda": "ano",
    "Tipo de Emenda": "tipo_emenda",
    "Código do Autor da Emenda": "codigo_autor",
    "Nome do Autor da Emenda": "nome_autor",
    "Número da emenda": "numero_emenda",
    "Localidade de aplicação do recurso": "localidade_aplicacao",
    "Código Município IBGE": "cod_ibge_municipio",
    "Município": "municipio",
    "Código UF IBGE": "cod_ibge_uf",
    "UF": "uf_destino",
    "Região": "regiao",
    "Código Função": "cod_funcao",
    "Nome Função": "funcao",
    "Código Subfunção": "cod_subfuncao",
    "Nome Subfunção": "subfuncao",
    "Código Programa": "cod_programa",
    "Nome Programa": "programa",
    "Código Ação": "cod_acao",
    "Nome Ação": "acao",
    "Código Plano Orçamentário": "cod_plano_orcamentario",
    "Nome Plano Orçamentário": "plano_orcamentario",
    "Valor Empenhado": "valor_empenhado",
    "Valor Liquidado": "valor_liquidado",
    "Valor Pago": "valor_pago",
    "Valor Restos A Pagar Inscritos": "valor_rp_inscrito",
    "Valor Restos A Pagar Cancelados": "valor_rp_cancelado",
    "Valor Restos A Pagar Pagos": "valor_rp_pago",
}

COLUNAS_VALOR = [
    "valor_empenhado",
    "valor_liquidado",
    "valor_pago",
    "valor_rp_inscrito",
    "valor_rp_cancelado",
    "valor_rp_pago",
]


class PortalTransparenciaCollector(BaseCollector):
    def __init__(self, cache: CacheManager | None = None):
        if cache is None:
            cache = CacheManager(
                Path(__file__).parent.parent.parent / "data" / "raw",
                ttl_seconds=24 * 3600,
            )
        super().__init__(cache)

    def collect(self, **kwargs) -> pd.DataFrame:
        """Baixa e processa o CSV de emendas do Portal da Transparencia."""
        csv_path = self.cache.get_file_path("emendas_portal.csv")

        if not self.cache.is_fresh("emendas_portal.csv"):
            logger.info("Baixando CSV do Portal da Transparência (%s)...", PORTAL_TRANSPARENCIA_CSV_URL)
            self._download_and_extract(csv_path)
        else:
            logger.info("Usando CSV em cache: %s", csv_path)

        df = self._parse_csv(csv_path)
        df = self._limpar(df)
        return df

    def _download_and_extract(self, output_path: Path) -> None:
        response = requests.get(PORTAL_TRANSPARENCIA_CSV_URL, timeout=120, stream=True)
        response.raise_for_status()

        content = io.BytesIO(response.content)
        with zipfile.ZipFile(content) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv") and "Emendas" in n and "Convenio" not in n and "Favorecido" not in n]
            if not csv_names:
                csv_names = [n for n in zf.namelist() if n.endswith(".csv")]

            target = csv_names[0]
            logger.info("Extraindo %s do ZIP...", target)

            with zf.open(target) as src:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(src.read())

        logger.info("CSV salvo em %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)

    def _parse_csv(self, path: Path) -> pd.DataFrame:
        logger.info("Lendo CSV %s...", path.name)
        df = pd.read_csv(
            path,
            sep=PORTAL_CSV_SEPARATOR,
            encoding=PORTAL_CSV_ENCODING,
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

        for col in COLUNAS_VALOR:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                    .astype(float)
                )

        if "ano" in df.columns:
            df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
            df = df[df["ano"] >= ANO_MINIMO]

        if "cod_ibge_municipio" in df.columns:
            df["cod_ibge_municipio"] = df["cod_ibge_municipio"].str.strip()

        if "cod_ibge_uf" in df.columns:
            df["cod_ibge_uf"] = df["cod_ibge_uf"].str.strip()

        df["localidade_tipo"] = df.apply(self._classificar_localidade, axis=1)

        if "uf_destino" in df.columns and "regiao" in df.columns:
            mask_sem_regiao = df["regiao"].isna() | (df["regiao"].str.strip() == "")
            df.loc[mask_sem_regiao, "regiao"] = df.loc[mask_sem_regiao, "uf_destino"].map(
                lambda uf: UF_REGIAO.get(str(uf).strip(), None)
            )

        sem_info = ["Sem informação", "Sem informacao", "SEM INFORMAÇÃO", ""]
        for col in ["nome_autor", "municipio", "uf_destino"]:
            if col in df.columns:
                df[col] = df[col].replace(sem_info, pd.NA)

        logger.info(
            "Dados limpos: %d linhas, anos %s a %s",
            len(df),
            df["ano"].min() if "ano" in df.columns else "?",
            df["ano"].max() if "ano" in df.columns else "?",
        )
        return df

    @staticmethod
    def _classificar_localidade(row) -> str:
        mun = str(row.get("cod_ibge_municipio", "")).strip()
        uf = str(row.get("cod_ibge_uf", "")).strip()
        loc = str(row.get("localidade_aplicacao", "")).strip().upper()

        if mun and mun not in ("", "nan", "None"):
            return "municipal"
        if uf and uf not in ("", "nan", "None"):
            return "estadual"
        if "NACIONAL" in loc:
            return "nacional"
        return "sem_informacao"
