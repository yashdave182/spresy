import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..utils.contact_extractor import extract_phones
from .base import BaseScraper

logger = logging.getLogger("spresy.indiamart")


class IndiaMartScraper(BaseScraper):
    """
    Tier 2. IndiaMART — India's largest B2B marketplace.
    Scrapes public seller/product listing pages (light anti-bot).
    """

    name = "indiamart"
    display_name = "IndiaMART"
    yields_leads = True
    tier = 2

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        slugs = self._make_slugs(query)
        for slug in slugs:
            url = f"https://dir.indiamart.com/impcat/{slug}.html"
            try:
                resp = await self.client.get(url)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "lxml")
                cards = soup.select("article.template7-product-card, article")
                if not cards:
                    cards = soup.select(".card, .lng_contnt")
                for card in cards[:limit]:
                    name_el = card.select_one("h2 a, h2, .prd-name a, .titles h2")
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue
                    href = name_el.get("href", "") if name_el.name == "a" else (card.select_one("a[href]").get("href", "") if card.select_one("a[href]") else "")
                    website = href if href.startswith("http") else (f"https://www.indiamart.com{href}" if href.startswith("/") else "")
                    card_text = card.get_text(" ", strip=True)
                    phones = extract_phones(card_text)
                    phone = phones[0] if phones else None
                    addr_el = card.select_one(".addr, .clr2, .adress, .company")
                    results.append({
                        "name": name,
                        "website": website or f"https://www.indiamart.com/search/?q={quote_plus(query)}",
                        "phone": phone,
                        "address": addr_el.get_text(" ", strip=True) if addr_el else None,
                        "description": card_text[:300],
                        "verified": True,
                        "source": "indiamart",
                    })
                    if len(results) >= limit:
                        return results
            except Exception as e:
                logger.warning("IndiaMART search failed for %s: %s", slug, e)
            if results:
                break

        # Fallback: generic seller search page (works for any keyword/location)
        if len(results) < limit:
            q = quote_plus(query)
            url = f"https://dir.indiamart.com/search.mp?ss={q}&src=as-rcnt&qt={q}"
            try:
                resp = await self.client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    for card in soup.select("article, .lng_contnt, .search-cat")[:limit]:
                        name_el = card.select_one("h2 a, h2, a[href*='company']")
                        if not name_el:
                            continue
                        name = name_el.get_text(strip=True)
                        if not name or len(name) < 3:
                            continue
                        card_text = card.get_text(" ", strip=True)
                        phones = extract_phones(card_text)
                        results.append({
                            "name": name,
                            "website": f"https://www.indiamart.com/search/?q={q}",
                            "phone": phones[0] if phones else None,
                            "address": card.select_one(".addr, .add").get_text(" ", strip=True) if card.select_one(".addr, .add") else None,
                            "description": card_text[:300],
                            "verified": True,
                            "source": "indiamart",
                        })
                        if len(results) >= limit:
                            break
            except Exception as e:
                logger.warning("IndiaMART search fallback failed: %s", e)
        return results

    @staticmethod
    def _make_slugs(query: str) -> List[str]:
        q = query.lower()
        q = re.sub(r"[\s]+", "-", q.strip())
        q = re.sub(r"[^a-z0-9\-]", "", q)
        return [q] if q else []
