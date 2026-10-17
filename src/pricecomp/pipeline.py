from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from pricecomp.analysis.pricing import compare
from pricecomp.analysis.table import build_table
from pricecomp.config import Settings
from pricecomp.domain.models import Comparison, MarketOffer, SupplierItem
from pricecomp.export.drive import upload_to_drive
from pricecomp.export.excel import write_excel
from pricecomp.fx import fetch_usd_rate
from pricecomp.ingestion.registry import get_parser
from pricecomp.normalization.matcher import offer_matches
from pricecomp.scrapers.base import Scraper
from pricecomp.scrapers.registry import build_scrapers

ProgressFn = Callable[[str, int, int], None]  # (etapa, hechos, total)


@dataclass
class Result:
    comparisons: list[Comparison]
    table: pd.DataFrame
    usd_to_ars: float | None


def parse_items(pdf: Path, parser_name: str = "lista_dolares") -> list[SupplierItem]:
    """1. PDF -> datos celus/precios."""
    items = get_parser(parser_name).parse(pdf)
    if not items:
        raise ValueError(f"No se encontraron equipos en {pdf.name}. ¿Es la lista de precios correcta?")
    return items


async def collect_offers(item: SupplierItem, scrapers: list[Scraper], settings: Settings, sem: asyncio.Semaphore) -> list[MarketOffer]:
    async def run(s: Scraper) -> list[MarketOffer]:
        async with sem:
            return await s.search(item.phone)

    results = await asyncio.gather(*(run(s) for s in scrapers))
    return [o for offers in results for o in offers if offer_matches(item.phone, o.title, settings.matching.min_score)]


async def compare_items(items: list[SupplierItem], settings: Settings, sources: list[str] | None = None, on_progress: ProgressFn | None = None) -> Result:
    """2. recolección web + 3. tabla comparativa."""
    notify = on_progress or (lambda *_: None)

    usd_to_ars = settings.usd_to_ars
    if usd_to_ars is None and any(i.currency == "USD" for i in items):
        notify("Consultando cotización del dólar", 0, len(items))
        usd_to_ars = await asyncio.to_thread(fetch_usd_rate, settings.fx_rate_type)

    scrapers = build_scrapers(settings, sources)
    sem = asyncio.Semaphore(settings.scraping.concurrency)
    done = 0
    notify("Consultando tiendas (puede tardar ~1 minuto)", done, len(items))

    async def one(item: SupplierItem) -> list[MarketOffer]:
        nonlocal done
        offers = await collect_offers(item, scrapers, settings, sem)
        done += 1
        notify("Comparando equipos", done, len(items))
        return offers

    all_offers = await asyncio.gather(*(one(i) for i in items))
    comparisons: list[Comparison] = [compare(i, offers, settings.pricing, usd_to_ars) for i, offers in zip(items, all_offers)]
    return Result(comparisons, build_table(comparisons, [s.name for s in scrapers]), usd_to_ars)


def export_excel(result: Result, settings: Settings) -> Path:
    return write_excel(result.table, settings.output_dir / f"comparativa_{date.today():%Y%m%d}.xlsx")


def upload_excel(path: Path, settings: Settings) -> str:
    """4. Excel -> Drive."""
    return upload_to_drive(path, settings.drive_folder_id, settings.google_client_secret_path, settings.google_token_path)


async def run_pipeline(pdf: Path, settings: Settings, parser_name: str = "lista_dolares", upload: bool = True, sources: list[str] | None = None) -> tuple[Path, str | None]:
    result = await compare_items(parse_items(pdf, parser_name), settings, sources)
    if result.usd_to_ars:
        print(f"Dólar: {result.usd_to_ars:,.0f} ARS")
    out = export_excel(result, settings)
    return out, upload_excel(out, settings) if upload else None
