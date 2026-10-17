from pricecomp.analysis.pricing import compare
from pricecomp.config import PricingConfig
from pricecomp.domain.models import MarketOffer, Phone, SupplierItem
from pricecomp.ingestion.pdf_parser import parse_price

CFG = PricingConfig(margin_min=0.10, undercut=0.02)


def _item(cost, cur="ARS"):
    return SupplierItem(raw_name="X", phone=Phone(model="X"), cost=cost, currency=cur)


def _offers(*prices):
    return [MarketOffer(source="ml", title="X", price=p) for p in prices]


def test_competitive():
    c = compare(_item(1000), _offers(1400, 1500, 1600), CFG)
    assert c.market_median == 1500
    assert c.suggested_price == 1470
    assert c.status == "Competitivo"


def test_market_below_floor():
    c = compare(_item(1000), _offers(1000, 1050), CFG)
    assert c.suggested_price == 1100
    assert c.status == "Mercado bajo el margen mínimo"


def test_no_offers_and_usd():
    assert compare(_item(1000), [], CFG).status == "Sin datos de mercado"
    assert compare(_item(100, "USD"), _offers(1), CFG).status == "Falta USD_TO_ARS"
    assert compare(_item(100, "USD"), _offers(150000), CFG, usd_to_ars=1000).cost_ars == 100000


def test_parse_price():
    assert parse_price("$ 1.234,56") == 1234.56
    assert parse_price("1,234.56") == 1234.56
    assert parse_price("U$S 350") == 350
    assert parse_price("1.200.000") == 1200000
    assert parse_price("sin precio") is None
