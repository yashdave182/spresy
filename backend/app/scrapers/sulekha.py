import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..utils.contact_extractor import extract_phones
from .base import BaseScraper

logger = logging.getLogger("spresy.sulekha")


class SulekhaScraper(BaseScraper):
    """
    Tier 2. Sulekha — Indian local services directory.
    """

    name = "sulekha"
    display_name = "Sulekha"
    yields_leads = True
    tier = 2

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        slug = re.sub(r"[^a-z0-9\-]+", "-", query.lower().strip()).strip("-")
        if not slug:
            return results
        from urllib.parse import quote_plus
        loc = (self.location or "india").lower().replace(" ", "-")
        url = f"https://www.sulekha.com/search?query={quote_plus(query)}&city={loc}"
        try:
            resp = await self.client.get(url)
            html = resp.text if resp.status_code == 200 else None
            if html is None or "couldn’t find an exact match" in (html or ""):
                from ..utils.playwright_fetcher import playwright_fetch
                html = await playwright_fetch(url, wait_selector=".services-cards, .service-card, .listCard, article")
            if not html:
                return results
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select(".services-cards, .service-card, .listCard, .cards, article, .srp_card, .results-block")[:limit]:
                name_el = card.select_one("h2 a, h3 a, .services-name a, a[href*='services']")
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if not name or len(name) < 3:
                    continue
                href = name_el.get("href", "")
                website = href if href.startswith("http") else (f"https://www.sulekha.com{href}" if href.startswith("/") else "")
                phones = extract_phones(card.get_text(" ", strip=True))
                addr_el = card.select_one(".address, .location, .addr")
                results.append({
                    "name": name,
                    "website": website,
                    "phone": phones[0] if phones else None,
                    "address": addr_el.get_text(" ", strip=True) if addr_el else None,
                    "description": card.select_one(".summary, p").get_text(" ", strip=True)[:300] if card.select_one(".summary, p") else "",
                    "verified": True,
                    "source": "sulekha",
                })
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.warning("Sulekha search failed for %s: %s", query, e)
        return results
