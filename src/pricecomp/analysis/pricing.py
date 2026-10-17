from __future__ import annotations

import statistics

from pricecomp.config import PricingConfig
from pricecomp.domain.models import Comparison, MarketOffer, SupplierItem


def compare(item: SupplierItem, offers: list[MarketOffer], cfg: PricingConfig, usd_to_ars: float | None = None) -> Comparison:
    """Calcula estadísticas de mercado, precio sugerido y estado para un equipo."""
    cost = item.cost * usd_to_ars if item.currency == "USD" and usd_to_ars else item.cost
    comp = Comparison(item=item, offers=offers, cost_ars=cost)
    if item.currency == "USD" and not usd_to_ars:
        comp.status = "Falta USD_TO_ARS"
        return comp
    if not offers:
        return comp

    prices = [o.price for o in offers]
    comp.market_min = min(prices)
    comp.market_median = statistics.median(prices)
    comp.market_mean = statistics.fmean(prices)

    floor = cost * (1 + cfg.margin_min)
    target = comp.market_median * (1 - cfg.undercut)
    comp.suggested_price = round(max(floor, target), 2)
    comp.margin_pct = (comp.suggested_price - cost) / cost if cost else None

    if comp.market_median < floor:
        comp.status = "Mercado bajo el margen mínimo"
    elif comp.suggested_price > comp.market_median * (1 + cfg.expensive_threshold):
        comp.status = "Caro"
    elif comp.suggested_price < comp.market_median * (1 - cfg.cheap_threshold):
        comp.status = "Barato (margen de sobra)"
    else:
        comp.status = "Competitivo"
    return comp
