"""Classe base abstrata para coletores de dados de emendas."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache_manager import CacheManager


class BaseCollector(ABC):
    def __init__(self, cache: CacheManager):
        self.cache = cache

    @abstractmethod
    def collect(self, **kwargs) -> pd.DataFrame:
        ...
