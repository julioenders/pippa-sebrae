"""Coletores de dados para o PIPPA - Emendas."""

from .portal_transparencia import PortalTransparenciaCollector
from .tesouro_transparente import TesouroTransparenteCollector
from .camara_api import CamaraApiCollector
from .senado_api import SenadoApiCollector

__all__ = [
    "PortalTransparenciaCollector",
    "TesouroTransparenteCollector",
    "CamaraApiCollector",
    "SenadoApiCollector",
]
