"""Resolve partido e UF do autor da emenda via cruzamento com APIs Camara/Senado.

Estrategia:
1. Monta indice nome_normalizado -> Parlamentar por legislatura
2. Para cada emenda, identifica a legislatura pelo ano
3. Busca o autor por nome exato normalizado
4. Se nao encontra, tenta fuzzy match (score >= threshold)
5. Emendas de bancada/comissao/relator recebem flag NAO_APLICAVEL
"""

from __future__ import annotations

import logging
import unicodedata
from collections import defaultdict

import pandas as pd

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

from config import FUZZY_MATCH_THRESHOLD, LEGISLATURAS, TIPOS_SEM_AUTOR_INDIVIDUAL
from models import MatchConfianca, Parlamentar

logger = logging.getLogger(__name__)


def normalizar_nome(nome: str) -> str:
    if not nome or not isinstance(nome, str):
        return ""
    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    return " ".join(nome.upper().split())


def ano_para_legislatura(ano: int) -> int | None:
    for leg_id, info in LEGISLATURAS.items():
        if info["inicio"] <= ano <= info["fim"]:
            return leg_id
    return None


class PartidoResolver:
    def __init__(self, parlamentares: list[Parlamentar]):
        self.indice: dict[int, dict[str, Parlamentar]] = defaultdict(dict)
        self.nomes_por_leg: dict[int, list[str]] = defaultdict(list)

        for p in parlamentares:
            self.indice[p.legislatura][p.nome_normalizado] = p
            self.nomes_por_leg[p.legislatura].append(p.nome_normalizado)

        total = sum(len(v) for v in self.indice.values())
        logger.info(
            "Índice de parlamentares: %d registros em %d legislaturas",
            total, len(self.indice),
        )

    def resolver(self, nome_autor: str, ano: int) -> tuple[str | None, str | None, str]:
        """Retorna (partido, uf, match_confianca) para um autor/ano."""
        if not nome_autor or pd.isna(nome_autor):
            return None, None, MatchConfianca.NAO_ENCONTRADO.value

        nome_norm = normalizar_nome(nome_autor)
        legislatura = ano_para_legislatura(ano)

        if legislatura is None:
            return None, None, MatchConfianca.NAO_ENCONTRADO.value

        if nome_norm in self.indice[legislatura]:
            p = self.indice[legislatura][nome_norm]
            return p.partido, p.uf, MatchConfianca.EXATO.value

        if HAS_RAPIDFUZZ and self.nomes_por_leg.get(legislatura):
            best_score = 0
            best_match = None
            for candidato in self.nomes_por_leg[legislatura]:
                score = fuzz.ratio(nome_norm, candidato)
                if score > best_score:
                    best_score = score
                    best_match = candidato

            if best_score >= FUZZY_MATCH_THRESHOLD and best_match:
                p = self.indice[legislatura][best_match]
                logger.debug(
                    "Fuzzy match: '%s' → '%s' (score=%d)", nome_autor, p.nome, best_score
                )
                return p.partido, p.uf, MatchConfianca.FUZZY.value

        return None, None, MatchConfianca.NAO_ENCONTRADO.value

    def enriquecer(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona colunas partido, uf_autor, legislatura e match_confianca ao DataFrame."""
        partidos = []
        ufs = []
        legislaturas = []
        confiancas = []

        total = len(df)
        for i, (_, row) in enumerate(df.iterrows()):
            tipo = str(row.get("tipo_emenda", ""))
            nome = row.get("nome_autor")
            ano = row.get("ano")

            if any(t in tipo for t in TIPOS_SEM_AUTOR_INDIVIDUAL):
                partidos.append(None)
                ufs.append(None)
                legislaturas.append(ano_para_legislatura(int(ano)) if pd.notna(ano) else None)
                confiancas.append(MatchConfianca.NAO_APLICAVEL.value)
                continue

            ano_int = int(ano) if pd.notna(ano) else 0
            partido, uf, confianca = self.resolver(nome, ano_int)

            partidos.append(partido)
            ufs.append(uf)
            legislaturas.append(ano_para_legislatura(ano_int))
            confiancas.append(confianca)

            if (i + 1) % 10000 == 0:
                logger.info("Enriquecimento: %d/%d (%.0f%%)", i + 1, total, (i + 1) / total * 100)

        df["partido"] = partidos
        df["uf_autor"] = ufs
        df["legislatura"] = legislaturas
        df["match_confianca"] = confiancas

        stats = df["match_confianca"].value_counts()
        logger.info("Match stats: %s", stats.to_dict())

        return df
