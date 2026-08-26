import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..utils.contact_extractor import extract_phones
from .base import BaseScraper

logger = logging.getLogger("spresy.tradeindia")


class TradeIndiaScraper(BaseScraper):
    """
    Tier 2. TradeIndia — major Indian B2B marketplace.
    Uses the keyword search results page (most reliable format).
    """

    name = "tradeindia"
    display_name = "TradeIndia"
    yields_leads = True
    tier = 2

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        url = f"https://www.tradeindia.com/search.html?keyword={quote_plus(query)}"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("div.fullwidthcard")
            if not cards:
                cards = soup.select("div.card")
            for card in cards[:limit]:
                name_el = card.select_one("h2 a, h2")
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if not name or len(name) < 3:
                    continue
                href = name_el.get("href", "") if name_el.name == "a" else (card.select_one("a[href]").get("href", "") if card.select_one("a[href]") else "")
                website = href if href.startswith("http") else (f"https://www.tradeindia.com{href}" if href.startswith("/") else "")
                text = card.get_text(" ", strip=True)
                phones = extract_phones(text)
                addr_el = card.select_one(".company, .address, .location, .addr")
                results.append({
                    "name": name,
                    "website": website or f"https://www.tradeindia.com/search.html?keyword={quote_plus(query)}",
                    "phone": phones[0] if phones else None,
                    "address": addr_el.get_text(" ", strip=True) if addr_el else None,
                    "description": text[:300],
                    "verified": True,
                    "source": "tradeindia",
                })
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.warning("TradeIndia search failed for %s: %s", query, e)
        return results
