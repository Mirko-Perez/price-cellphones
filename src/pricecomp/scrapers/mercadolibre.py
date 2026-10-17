from __future__ import annotations

import os

import httpx

from pricecomp.domain.models import MarketOffer, Phone
from pricecomp.scrapers.base import Scraper

API = "https://api.mercadolibre.com"
CELLPHONES = "MLA1055"  # Celulares y Smartphones


class MercadoLibreScraper(Scraper):
    """API oficial con token de aplicación (MELI_CLIENT_ID / MELI_CLIENT_SECRET en .env).

    Sin token la API devuelve 403 y el sitio web bloquea navegadores automatizados
    ("suspicious traffic"), así que sin credenciales esta fuente se omite.
    """

    name = "mercadolibre"
    _token: str | None = None

    async def fetch(self, phone: Phone) -> list[MarketOffer]:
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            token = await self._get_token(client)
            if not token:
                raise RuntimeError("faltan MELI_CLIENT_ID/MELI_CLIENT_SECRET; fuente omitida")
            resp = await client.get(
                f"{API}/sites/MLA/search",
                params={"q": phone.query, "category": CELLPHONES, "condition": "new", "limit": 30},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
        return [
            MarketOffer(source=self.name, title=r["title"], price=float(r["price"]), url=r.get("permalink"))
            for r in resp.json().get("results", [])
            if r.get("price")
        ]

    async def _get_token(self, client: httpx.AsyncClient) -> str | None:
        if self._token:
            return self._token
        cid, secret = os.getenv("MELI_CLIENT_ID"), os.getenv("MELI_CLIENT_SECRET")
        if not (cid and secret):
            return None
        resp = await client.post(
            f"{API}/oauth/token",
            data={"grant_type": "client_credentials", "client_id": cid, "client_secret": secret},
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token
