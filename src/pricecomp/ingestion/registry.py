from __future__ import annotations

from pricecomp.ingestion.base import SupplierParser
from pricecomp.ingestion.pdf_parser import CategoryColumnPdfParser, GenericPdfParser

PARSERS: dict[str, SupplierParser] = {
    GenericPdfParser.name: GenericPdfParser(),
    "lista_dolares": CategoryColumnPdfParser(),
    # "proveedor_x": ProveedorXParser(),
}


def get_parser(name: str = "lista_dolares") -> SupplierParser:
    try:
        return PARSERS[name]
    except KeyError:
        raise ValueError(f"Parser desconocido '{name}'. Disponibles: {', '.join(PARSERS)}") from None
