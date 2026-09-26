"""Coletor de dados de senadores da API do Senado Federal.

Fonte: https://legis.senado.leg.br/dadosabertos
Endpoints:
  - /senador/lista/atual (em exercicio, dados completos com partido e UF)
  - /senador/lista/legislatura/{id} (todos, mas dados parciais para suplentes)
  - /senador/{codigo} (detalhes individuais, fallback para dados faltantes)
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
from config import LEGISLATURAS, SENADO_API_BASE
from models import Parlamentar

logger = logging.getLogger(__name__)

LEGISLATURA_ATUAL = max(LEGISLATURAS.keys())


def normalizar_nome(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    return " ".join(nome.upper().split())


class SenadoApiCollector(BaseCollector):
    def __init__(self, cache: CacheManager | None = None):
        if cache is None:
            cache = CacheManager(
                Path(__file__).parent.parent.parent / "data" / "cache",
                ttl_seconds=7 * 24 * 3600,
            )
        super().__init__(cache)

    def collect(self, **kwargs) -> list[Parlamentar]:
        """Coleta senadores de todas as legislaturas configuradas."""
        todos = []
        for legislatura_id in LEGISLATURAS:
            senadores = self._collect_legislatura(legislatura_id)
            todos.extend(senadores)
        logger.info("Total de senadores coletados: %d (todas as legislaturas)", len(todos))
        return todos

    def _collect_legislatura(self, legislatura: int) -> list[Parlamentar]:
        cache_key = {"source": "senado_v2", "legislatura": legislatura}
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Senadores legislatura %d: cache hit (%d registros)", legislatura, len(cached))
            return [Parlamentar(**p) for p in cached]

        logger.info("Coletando senadores da legislatura %d via API Senado...", legislatura)

        senadores_por_lista = self._fetch_lista_legislatura(legislatura)

        if legislatura == LEGISLATURA_ATUAL:
            senadores_atuais = self._fetch_lista_atual()
            senadores_por_lista = self._merge_senadores(senadores_por_lista, senadores_atuais, legislatura)

        incompletos = [s for s in senadores_por_lista if not s.partido or not s.uf]
        if incompletos:
            logger.info("Buscando detalhes para %d senadores sem partido/UF...", len(incompletos))
            for s in incompletos:
                if s.id_externo:
                    detalhes = self._fetch_detalhe(s.id_externo)
                    if detalhes:
                        if not s.partido and detalhes.get("partido"):
                            s.partido = detalhes["partido"]
                        if not s.uf and detalhes.get("uf"):
                            s.uf = detalhes["uf"]
                    time.sleep(0.3)

        com_partido = sum(1 for s in senadores_por_lista if s.partido)
        logger.info(
            "Legislatura %d: %d senadores (%d com partido)",
            legislatura, len(senadores_por_lista), com_partido,
        )

        self.cache.set(cache_key, [p.to_dict() for p in senadores_por_lista])
        return senadores_por_lista

    def _fetch_lista_legislatura(self, legislatura: int) -> list[Parlamentar]:
        url = f"{SENADO_API_BASE}/senador/lista/legislatura/{legislatura}"
        headers = {"Accept": "application/json"}

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Erro na API Senado lista legislatura %d: %s", legislatura, e)
            return []

        lista = (
            data
            .get("ListaParlamentarLegislatura", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        if isinstance(lista, dict):
            lista = [lista]

        return [self._parse_parlamentar(sen, legislatura) for sen in lista]

    def _fetch_lista_atual(self) -> list[Parlamentar]:
        url = f"{SENADO_API_BASE}/senador/lista/atual"
        headers = {"Accept": "application/json"}

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Erro na API Senado lista atual: %s", e)
            return []

        lista = (
            data
            .get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        if isinstance(lista, dict):
            lista = [lista]

        return [self._parse_parlamentar(sen, LEGISLATURA_ATUAL) for sen in lista]

    def _fetch_detalhe(self, codigo: str) -> dict | None:
        url = f"{SENADO_API_BASE}/senador/{codigo}"
        headers = {"Accept": "application/json"}

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            return None

        parlamentar = (
            data
            .get("DetalheParlamentar", {})
            .get("Parlamentar", {})
        )
        if not parlamentar:
            return None

        ident = parlamentar.get("IdentificacaoParlamentar", {})
        dados_basicos = parlamentar.get("DadosBasicosParlamentar", {})

        return {
            "partido": ident.get("SiglaPartidoParlamentar", ""),
            "uf": ident.get("UfParlamentar", "") or dados_basicos.get("UfNaturalidade", ""),
        }

    def _merge_senadores(
        self,
        lista_leg: list[Parlamentar],
        lista_atual: list[Parlamentar],
        legislatura: int,
    ) -> list[Parlamentar]:
        """Enriquece a lista da legislatura com dados da lista atual (que tem partido/UF)."""
        atuais_por_id = {s.id_externo: s for s in lista_atual if s.id_externo}
        atuais_por_nome = {s.nome_normalizado: s for s in lista_atual}

        for s in lista_leg:
            atual = atuais_por_id.get(s.id_externo) or atuais_por_nome.get(s.nome_normalizado)
            if atual:
                if not s.partido and atual.partido:
                    s.partido = atual.partido
                if not s.uf and atual.uf:
                    s.uf = atual.uf

        return lista_leg

    @staticmethod
    def _parse_parlamentar(sen: dict, legislatura: int) -> Parlamentar:
        ident = sen.get("IdentificacaoParlamentar", {})
        mandato = sen.get("Mandato", {})

        partido = ident.get("SiglaPartidoParlamentar", "")
        uf = ident.get("UfParlamentar", "")
        nome = ident.get("NomeParlamentar", "") or ident.get("NomeCompletoParlamentar", "")

        if not partido and isinstance(mandato, dict):
            partido = mandato.get("SiglaPartido", "")
        if not uf and isinstance(mandato, dict):
            uf = mandato.get("UfParlamentar", "")

        return Parlamentar(
            nome=nome,
            nome_normalizado=normalizar_nome(nome),
            partido=partido,
            uf=uf,
            legislatura=legislatura,
            casa="senado",
            id_externo=str(ident.get("CodigoParlamentar", "")),
        )
