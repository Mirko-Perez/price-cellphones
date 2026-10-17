from __future__ import annotations

import httpx

URL = "https://dolarapi.com/v1/dolares/{kind}"


def fetch_usd_rate(kind: str = "blue", timeout_s: int = 15) -> float:
    """Cotización de venta del dólar en ARS (dolarapi.com)."""
    resp = httpx.get(URL.format(kind=kind), timeout=timeout_s)
    resp.raise_for_status()
    return float(resp.json()["venta"])
