from __future__ import annotations

import pandas as pd

from pricecomp.domain.models import Comparison


def build_table(comparisons: list[Comparison], sources: list[str]) -> pd.DataFrame:
    rows = []
    for c in comparisons:
        row = {
            "Equipo": c.item.raw_name,
            "Costo proveedor": c.cost_ars,
        }
        for s in sources:
            prices = [o.price for o in c.offers if o.source == s]
            row[f"{s} (mín)"] = min(prices) if prices else None
        row |= {
            "Mercado mín": c.market_min,
            "Mercado mediana": c.market_median,
            "Mercado promedio": c.market_mean,
            "Precio sugerido": c.suggested_price,
            "Margen %": c.margin_pct,
            "Estado": c.status,
            "# ofertas": len(c.offers),
        }
        rows.append(row)
    return pd.DataFrame(rows)
