from __future__ import annotations

import json

import httpx

from pricecomp.domain.models import MarketOffer
from pricecomp.scrapers.base import CatalogScraper

LIST_URL = "https://www.personal.com.ar/tienda/celulares/liberados"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
_decoder = json.JSONDecoder()


def _extract(html: str, key: str, after: str | None = None):
    """Saca el valor JSON de `"key":...` embebido en el HTML (la tienda es Next.js).

    `after` desambigua claves repetidas: se busca `key` a partir de la primera aparición de `after`.
    """
    start = max(html.find(f'"{after}":'), 0) if after else 0
    marker = f'"{key}":'
    i = html.find(marker, start)
    if i < 0:
        return None
    value, _ = _decoder.raw_decode(html, i + len(marker))
    return value


class PersonalScraper(CatalogScraper):
    """Tienda Personal: el listado trae los productos como JSON en el HTML, paginado (?page=N)."""

    name = "personal"

    async def load_catalog(self) -> list[MarketOffer]:
        offers: list[MarketOffer] = []
        async with httpx.AsyncClient(timeout=self.timeout_s, headers=HEADERS, follow_redirects=True) as client:
            page, pages = 1, 1
            while page <= pages:
                resp = await client.get(LIST_URL, params={"page": page})
                resp.raise_for_status()
                pages = (_extract(resp.text, "pagination") or {}).get("totalPages", 1)
                for p in _extract(resp.text, "products", after="pagination") or []:
                    if p.get("price"):
                        offers.append(MarketOffer(
                            source=self.name,
                            title=p["name"],
                            price=float(p["price"]),
                            url=f"https://www.personal.com.ar/tienda/celulares/{p.get('slug', '')}",
                        ))
                page += 1
        return offers
