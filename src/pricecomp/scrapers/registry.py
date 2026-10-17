from __future__ import annotations

from pricecomp.config import Settings
from pricecomp.scrapers.base import Scraper
from pricecomp.scrapers.mercadolibre import MercadoLibreScraper
from pricecomp.scrapers.movistar import MovistarScraper
from pricecomp.scrapers.personal import PersonalScraper

SCRAPERS: dict[str, type[Scraper]] = {
    cls.name: cls for cls in (MercadoLibreScraper, PersonalScraper, MovistarScraper)
}


def build_scrapers(settings: Settings, only: list[str] | None = None) -> list[Scraper]:
    names = only or settings.sources
    unknown = set(names) - SCRAPERS.keys()
    if unknown:
        raise ValueError(f"Fuentes desconocidas: {', '.join(sorted(unknown))}. Disponibles: {', '.join(SCRAPERS)}")
    return [
        SCRAPERS[n](
            cache_dir=settings.cache_dir,
            timeout_s=settings.scraping.timeout_s,
            cache_ttl_h=settings.scraping.cache_ttl_h,
            max_offers=settings.matching.max_offers_per_source * 3,  # se filtra luego por matching
        )
        for n in names
    ]
