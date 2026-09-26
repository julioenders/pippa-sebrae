"""Normaliza e valida codigos IBGE e classifica localidade das emendas."""

from __future__ import annotations

import logging

import pandas as pd

from config import UF_CODES, UF_REGIAO

logger = logging.getLogger(__name__)

# Codigo IBGE da UF (2 digitos) extraido dos primeiros 2 digitos do codigo do municipio (7 digitos)
COD_UF_IBGE = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF",
}


class IbgeNormalizer:
    def normalizar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preenche UF e regiao a partir do codigo IBGE quando ausentes."""
        if "cod_ibge_municipio" in df.columns:
            mask_mun = df["cod_ibge_municipio"].notna() & (df["cod_ibge_municipio"].str.len() >= 2)

            if "uf_destino" in df.columns:
                mask_sem_uf = mask_mun & (df["uf_destino"].isna() | (df["uf_destino"].str.strip() == ""))
                df.loc[mask_sem_uf, "uf_destino"] = (
                    df.loc[mask_sem_uf, "cod_ibge_municipio"]
                    .str[:2]
                    .map(COD_UF_IBGE)
                )

            if "regiao" in df.columns:
                mask_sem_regiao = mask_mun & (df["regiao"].isna() | (df["regiao"].str.strip() == ""))
                df.loc[mask_sem_regiao, "regiao"] = (
                    df.loc[mask_sem_regiao, "uf_destino"].map(UF_REGIAO)
                )

        preenchidos_uf = df["uf_destino"].notna().sum() if "uf_destino" in df.columns else 0
        preenchidos_regiao = df["regiao"].notna().sum() if "regiao" in df.columns else 0
        logger.info(
            "IBGE normalizado: %d/%d com UF, %d/%d com Região",
            preenchidos_uf, len(df), preenchidos_regiao, len(df),
        )

        return df
