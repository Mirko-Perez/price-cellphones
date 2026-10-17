from __future__ import annotations

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

from pricecomp.domain.models import MarketOffer, Phone


class Scraper(ABC):
    """Una fuente de precios de mercado. Agregar una = subclase + registro en registry.py."""

    name: str

    def __init__(self, cache_dir: Path, timeout_s: int = 20, cache_ttl_h: int = 12, max_offers: int = 10):
        self.cache_dir = cache_dir
        self.timeout_s = timeout_s
        self.cache_ttl_s = cache_ttl_h * 3600
        self.max_offers = max_offers

    async def search(self, phone: Phone) -> list[MarketOffer]:
        key = hashlib.sha1(phone.query.lower().encode()).hexdigest()[:16]
        return await self._cached(key, lambda: self.fetch(phone))

    @abstractmethod
    async def fetch(self, phone: Phone) -> list[MarketOffer]:
        """Devuelve ofertas crudas para el equipo (sin filtrar por matching)."""

    async def _cached(self, key: str, loader) -> list[MarketOffer]:
        cache_file = self.cache_dir / f"{self.name}_{key}.json"
        if cache_file.exists() and time.time() - cache_file.stat().st_mtime < self.cache_ttl_s:
            return [MarketOffer(**o) for o in json.loads(cache_file.read_text())]
        try:
            offers = await loader()
        except Exception as exc:  # una fuente caída no debe tumbar el pipeline
            print(f"[{self.name}] error: {exc}")
            return []
        if offers:  # no cachear fallos/vacíos
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps([o.model_dump() for o in offers], ensure_ascii=False))
        return offers


class CatalogScraper(Scraper):
    """Fuente sin buscador usable: se baja el catálogo completo una vez (caché en disco + memoria) y se filtra luego."""

    _lock: asyncio.Lock | None = None
    _catalog: list[MarketOffer] | None = None

    async def search(self, phone: Phone) -> list[MarketOffer]:
        self._lock = self._lock or asyncio.Lock()
        async with self._lock:
            if self._catalog is None:
                self._catalog = await self._cached("catalog", self.load_catalog)
        return self._catalog

    async def fetch(self, phone: Phone) -> list[MarketOffer]:
        return await self.search(phone)

    @abstractmethod
    async def load_catalog(self) -> list[MarketOffer]:
        """Todas las ofertas de celulares de la fuente."""
