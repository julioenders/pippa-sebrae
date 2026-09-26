"""Cache de dados em filesystem para o PIPPA - Emendas."""

import hashlib
import json
import time
from pathlib import Path


class CacheManager:
    def __init__(self, base_dir: str | Path, ttl_seconds: int = 86400):
        self.base_dir = Path(base_dir)
        self.ttl = ttl_seconds

    def _key(self, params: dict) -> str:
        payload = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _path(self, key: str, ext: str = "json") -> Path:
        return self.base_dir / f"{key}.{ext}"

    def get(self, params: dict) -> dict | list | None:
        key = self._key(params)
        path = self._path(key)
        if path.exists() and (time.time() - path.stat().st_mtime) < self.ttl:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def set(self, params: dict, data: dict | list) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        key = self._key(params)
        self._path(key).write_text(
            json.dumps(data, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def get_file_path(self, name: str) -> Path:
        """Retorna caminho para arquivos nomeados (CSVs baixados)."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        return self.base_dir / name

    def is_fresh(self, name: str) -> bool:
        """Verifica se um arquivo nomeado ainda esta dentro do TTL."""
        path = self.base_dir / name
        if not path.exists():
            return False
        return (time.time() - path.stat().st_mtime) < self.ttl

    def clear(self) -> int:
        count = 0
        if self.base_dir.exists():
            for f in self.base_dir.iterdir():
                if f.is_file():
                    f.unlink()
                    count += 1
        return count
