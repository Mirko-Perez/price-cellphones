from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pricecomp.domain.models import SupplierItem


class SupplierParser(Protocol):
    """Convierte el archivo de un proveedor en items normalizados."""

    name: str

    def parse(self, path: Path) -> list[SupplierItem]: ...
