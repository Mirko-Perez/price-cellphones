from __future__ import annotations

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from pricecomp.domain.models import MarketOffer
from pricecomp.ingestion.pdf_parser import parse_price
from pricecomp.scrapers.base import CatalogScraper

BASE = "https://tiendaonline.movistar.com.ar"
BRANDS = ["samsung", "motorola", "xiaomi", "tcl", "zte", "nubia", "oppo", "apple"]

_JS_CARDS = """() => [...document.querySelectorAll('.product-item-name')].map(n => {
    const card = n.closest('.product-item') || n.parentElement.parentElement;
    const price = card.querySelector('.special-price') || card.querySelector('.normal-price');
    return {
        brand: n.querySelector('.brand')?.innerText || '',
        name: n.querySelector('.name')?.innerText || '',
        storage: card.querySelector('.product-storage')?.innerText || '',
        price: price?.dataset.specialPrice || price?.dataset.normalPrice || price?.innerText || '',
        href: card.querySelector('a')?.href || '',
    };
})"""


class MovistarScraper(CatalogScraper):
    """Tienda Movistar: una página por marca; los productos aparecen al hacer scroll (lazy)."""

    name = "movistar"

    async def load_catalog(self) -> list[MarketOffer]:
        offers: list[MarketOffer] = []
        timeout = max(self.timeout_s, 30) * 1000
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                page = await browser.new_page(locale="es-AR")
                for brand in BRANDS:
                    await page.goto(f"{BASE}/celulares-{brand}.html", wait_until="domcontentloaded", timeout=timeout)
                    try:
                        await page.wait_for_selector(".product-item-name", timeout=timeout)
                    except PlaywrightTimeout:  # marca sin productos publicados
                        print(f"[{self.name}] sin productos en {brand}")
                        continue
                    await self._scroll_all(page)
                    for c in await page.evaluate(_JS_CARDS):
                        if price := parse_price(c["price"]):
                            title = " ".join(f"{c['brand']} {c['name']} {c['storage']}".split())
                            offers.append(MarketOffer(source=self.name, title=title, price=price, url=c["href"] or None))
            finally:
                await browser.close()
        return offers

    @staticmethod
    async def _scroll_all(page, max_rounds: int = 15) -> None:
        count = -1
        for _ in range(max_rounds):
            await page.mouse.wheel(0, 6000)
            await page.wait_for_timeout(1000)
            now = await page.locator(".product-item-name").count()
            if now == count:
                return
            count = now
