from __future__ import annotations

from pydantic import BaseModel


class Phone(BaseModel):
    brand: str | None = None
    model: str
    storage_gb: int | None = None
    ram_gb: int | None = None

    @property
    def query(self) -> str:
        parts = [self.brand, self.model, f"{self.storage_gb}GB" if self.storage_gb else None]
        return " ".join(p for p in parts if p)


class SupplierItem(BaseModel):
    raw_name: str
    phone: Phone
    cost: float
    currency: str = "ARS"


class MarketOffer(BaseModel):
    source: str
    title: str
    price: float
    url: str | None = None


class Comparison(BaseModel):
    item: SupplierItem
    offers: list[MarketOffer]
    cost_ars: float
    market_min: float | None = None
    market_median: float | None = None
    market_mean: float | None = None
    suggested_price: float | None = None
    margin_pct: float | None = None  # margen del precio sugerido sobre costo
    status: str = "Sin datos de mercado"
