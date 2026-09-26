"""Modelo de dados do PIPPA - Emendas Parlamentares."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


class TipoEmenda(Enum):
    INDIVIDUAL_DEFINIDA = "Emenda Individual - Transferências com Finalidade Definida"
    INDIVIDUAL_ESPECIAL = "Emenda Individual - Transferências Especiais"
    BANCADA = "Emenda de Bancada"
    COMISSAO = "Emenda de Comissão"
    RELATOR = "Emenda de Relator"
    DESCONHECIDO = "Tipo não identificado"


class MatchConfianca(Enum):
    EXATO = "exato"
    FUZZY = "fuzzy"
    NAO_ENCONTRADO = "nao_encontrado"
    NAO_APLICAVEL = "nao_aplicavel"


class LocalidadeTipo(Enum):
    MUNICIPAL = "municipal"
    ESTADUAL = "estadual"
    NACIONAL = "nacional"
    SEM_INFORMACAO = "sem_informacao"


class QualityStatus(Enum):
    OK = "OK"
    ALERTA = "ALERTA"
    CRITICO = "CRITICO"


@dataclass
class Parlamentar:
    nome: str
    nome_normalizado: str
    partido: str
    uf: str
    legislatura: int
    casa: str  # "camara" | "senado"
    id_externo: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Emenda:
    codigo: str
    ano: int
    tipo: str
    nome_autor: str
    numero: str
    cod_ibge_municipio: Optional[str]
    municipio: Optional[str]
    cod_ibge_uf: Optional[str]
    uf_destino: Optional[str]
    regiao: Optional[str]
    localidade_tipo: str
    funcao: str
    subfuncao: str
    valor_empenhado: float
    valor_liquidado: float
    valor_pago: float
    valor_rp_inscrito: float
    valor_rp_cancelado: float
    valor_rp_pago: float
    partido: Optional[str] = None
    uf_autor: Optional[str] = None
    legislatura: Optional[int] = None
    match_confianca: str = MatchConfianca.NAO_ENCONTRADO.value

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QualityFlag:
    uf: str
    ano: int
    valor_portal: float
    valor_tesouro: float
    divergencia_pct: float
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineStats:
    total_emendas: int = 0
    total_autores_unicos: int = 0
    match_exato: int = 0
    match_fuzzy: int = 0
    match_nao_encontrado: int = 0
    match_nao_aplicavel: int = 0
    quality_flags_alerta: int = 0
    quality_flags_critico: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)
