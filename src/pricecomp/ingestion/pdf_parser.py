from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from pricecomp.domain.models import SupplierItem
from pricecomp.normalization.matcher import parse_phone

_PRICE = re.compile(r"(U\$S|USD|US\$|\$)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+)")
_LINE = re.compile(r"^(?P<name>.*?[A-Za-z].*?)\s+(?P<cur>U\$S|USD|US\$|\$)\s*(?P<price>[\d.,]+)\s*$", re.I)


def parse_price(raw: str) -> float | None:
    """Acepta "1.234,56", "1,234.56", "1234", "$ 350"."""
    m = _PRICE.search(raw.replace("\xa0", " "))
    if not m:
        return None
    num = m.group(2)
    if "," in num and "." in num:
        dec = "," if num.rfind(",") > num.rfind(".") else "."
        num = num.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in num or "." in num:
        sep = "," if "," in num else "."
        head, _, tail = num.rpartition(sep)
        num = f"{head.replace(sep, '')}{tail}" if len(tail) == 3 else f"{head.replace(sep, '')}.{tail}"
    try:
        return float(num)
    except ValueError:
        return None


def _currency(text: str) -> str:
    return "USD" if re.search(r"U\$S|USD|US\$", text, re.I) else "ARS"


class GenericPdfParser:
    """Extrae filas (equipo, precio) de PDFs con texto: primero tablas, luego líneas sueltas.

    Para un proveedor con formato propio, crear otro parser y registrarlo en registry.py.
    """

    name = "generic"

    def parse(self, path: Path) -> list[SupplierItem]:
        items: list[SupplierItem] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        items += self._from_table(table)
                else:
                    items += self._from_text(page.extract_text() or "")
        return items

    def _from_table(self, table: list[list[str | None]]) -> list[SupplierItem]:
        out = []
        for row in table:
            cells = [c.strip() for c in row if c and c.strip()]
            if len(cells) < 2:
                continue
            price = parse_price(cells[-1])
            name = cells[0]
            if price and re.search(r"[A-Za-z]", name):
                out.append(self._item(name, price, cells[-1]))
        return out

    def _from_text(self, text: str) -> list[SupplierItem]:
        out = []
        for line in text.splitlines():
            if (m := _LINE.match(line.strip())) and (price := parse_price(m["price"])):
                out.append(self._item(m["name"], price, m["cur"]))
        return out

    @staticmethod
    def _item(name: str, price: float, price_text: str) -> SupplierItem:
        return SupplierItem(raw_name=name, phone=parse_phone(name), cost=price, currency=_currency(price_text))


class CategoryColumnPdfParser(GenericPdfParser):
    """Listas en N columnas con títulos de categoría (p.ej. "CELULARES SAMSUNG") y líneas "PRODUCTO u$s 1.234,00".

    Lee columna por columna (la categoría de la última línea de una columna continúa en la siguiente)
    y conserva solo las categorías que empiezan con alguno de `category_prefixes`.
    """

    def __init__(self, name: str = "lista_dolares", columns: int = 2, category_prefixes: tuple[str, ...] = ("CELULARES",)):
        self.name = name
        self.columns = columns
        self.category_prefixes = category_prefixes

    def parse(self, path: Path) -> list[SupplierItem]:
        items: list[SupplierItem] = []
        category = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                width = page.width / self.columns
                for c in range(self.columns):
                    box = (c * width, 0, (c + 1) * width, page.height)
                    for line in (page.crop(box).extract_text() or "").splitlines():
                        line = line.strip()
                        if m := _LINE.match(line):
                            if category.startswith(self.category_prefixes) and (price := parse_price(m["price"])):
                                items.append(self._item(m["name"], price, m["cur"]))
                        elif line.isupper() and not line.startswith("PRODUCTO"):
                            category = line
        return items
