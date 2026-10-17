from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from pricecomp.analysis.pricing import compare
from pricecomp.analysis.table import build_table
from pricecomp.config import Settings
from pricecomp.domain.models import Comparison, MarketOffer, SupplierItem
from pricecomp.export.drive import upload_to_drive
from pricecomp.fx import fetch_usd_rate
from pricecomp.export.excel import write_excel
from pricecomp.ingestion.registry import get_parser
from pricecomp.normalization.matcher import offer_matches
from pricecomp.scrapers.base import Scraper
from pricecomp.scrapers.registry import build_scrapers


async def collect_offers(item: SupplierItem, scrapers: list[Scraper], settings: Settings, sem: asyncio.Semaphore) -> list[MarketOffer]:
    async def run(s: Scraper) -> list[MarketOffer]:
        async with sem:
            return await s.search(item.phone)

    results = await asyncio.gather(*(run(s) for s in scrapers))
    return [o for offers in results for o in offers if offer_matches(item.phone, o.title, settings.matching.min_score)]


async def run_pipeline(pdf: Path, settings: Settings, parser_name: str = "lista_dolares", upload: bool = True, sources: list[str] | None = None) -> tuple[Path, str | None]:
    items = get_parser(parser_name).parse(pdf)  # 1. PDF -> datos celus/precios
    if not items:
        raise SystemExit(f"No se encontraron equipos en {pdf}. Revisar el parser.")

    usd_to_ars = settings.usd_to_ars
    if usd_to_ars is None and any(i.currency == "USD" for i in items):
        usd_to_ars = fetch_usd_rate(settings.fx_rate_type)
        print(f"Dólar {settings.fx_rate_type}: {usd_to_ars:,.0f} ARS")

    scrapers = build_scrapers(settings, sources)  # 2. recolección web
    sem = asyncio.Semaphore(settings.scraping.concurrency)
    all_offers = await asyncio.gather(*(collect_offers(i, scrapers, settings, sem) for i in items))

    comparisons: list[Comparison] = [  # 3. tabla comparativa
        compare(i, offers, settings.pricing, usd_to_ars) for i, offers in zip(items, all_offers)
    ]
    df = build_table(comparisons, [s.name for s in scrapers])
    out = write_excel(df, settings.output_dir / f"comparativa_{date.today():%Y%m%d}.xlsx")

    link = upload_to_drive(out, settings.drive_folder_id, settings.google_client_secret_path, settings.google_token_path) if upload else None  # 4. Drive
    return out, link
