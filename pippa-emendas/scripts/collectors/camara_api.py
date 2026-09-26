"""Coletor de dados de deputados da API da Camara dos Deputados.

Fonte: https://dadosabertos.camara.leg.br/api/v2
Endpoints: /deputados (com filtro por legislatura)
Uso: enriquecimento de partido e UF do autor da emenda
Autenticacao: nenhuma (API aberta)
"""

from __future__ import annotations

import logging
import sys
import time
import unicodedata
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache_manager import CacheManager
from collectors.base import BaseCollector
from config import CAMARA_API_BASE, LEGISLATURAS
from models import Parlamentar

logger = logging.getLogger(__name__)


def normalizar_nome(nome: str) -> str:
    """Remove acentos, converte para maiusculo e remove espacos extras."""
    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    return " ".join(nome.upper().split())


class CamaraApiCollector(BaseCollector):
    def __init__(self, cache: CacheManager | None = None):
        if cache is None:
            cache = CacheManager(
                Path(__file__).parent.parent.parent / "data" / "cache",
                ttl_seconds=7 * 24 * 3600,
            )
        super().__init__(cache)

    def collect(self, **kwargs) -> list[Parlamentar]:
        """Coleta deputados de todas as legislaturas configuradas."""
        todos = []
        for legislatura_id in LEGISLATURAS:
            deputados = self._collect_legislatura(legislatura_id)
            todos.extend(deputados)
        logger.info("Total de deputados coletados: %d (todas as legislaturas)", len(todos))
        return todos

    def _collect_legislatura(self, legislatura: int) -> list[Parlamentar]:
        cache_key = {"source": "camara", "legislatura": legislatura}
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Deputados legislatura %d: cache hit (%d registros)", legislatura, len(cached))
            return [Parlamentar(**p) for p in cached]

        logger.info("Coletando deputados da legislatura %d via API Câmara...", legislatura)
        deputados = []
        pagina = 1

        while True:
            url = f"{CAMARA_API_BASE}/deputados"
            params = {
                "idLegislatura": legislatura,
                "ordem": "ASC",
                "ordenarPor": "nome",
                "pagina": pagina,
                "itens": 100,
            }

            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                logger.error("Erro na API Câmara (pag %d, leg %d): %s", pagina, legislatura, e)
                break

            items = data.get("dados", [])
            if not items:
                break

            for dep in items:
                deputados.append(Parlamentar(
                    nome=dep.get("nome", ""),
                    nome_normalizado=normalizar_nome(dep.get("nome", "")),
                    partido=dep.get("siglaPartido", ""),
                    uf=dep.get("siglaUf", ""),
                    legislatura=legislatura,
                    casa="camara",
                    id_externo=str(dep.get("id", "")),
                ))

            links = data.get("links", [])
            has_next = any(l.get("rel") == "next" for l in links)
            if not has_next:
                break

            pagina += 1
            time.sleep(0.2)

        logger.info("Legislatura %d: %d deputados coletados", legislatura, len(deputados))
        self.cache.set(cache_key, [p.to_dict() for p in deputados])
        return deputados
