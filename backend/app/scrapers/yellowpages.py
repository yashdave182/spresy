import logging
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger("spresy.yellowpages")


class YellowPagesScraper(BaseScraper):
    """Yellow Pages business directory."""

    name = "yellowpages"
    display_name = "YellowPages"
    yields_leads = True

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        url = f"https://www.yellowpages.com/search?search_terms={quote_plus(query)}"
        if self.location:
            url += f"&geo_location_terms={quote_plus(self.location)}"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            for v in soup.select(".v-card, .result")[:limit]:
                name_el = v.select_one("h2 a, .business-name a")
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                href = name_el.get("href", "")
                website = None
                if "yellowpages.com" in href and "/buy/" not in href:
                    website = f"https://www.yellowpages.com{href}" if href.startswith("/") else href
                phone_el = v.select_one(".phone")
                addr_el = v.select_one(".street-address, .adr")
                results.append({
                    "name": name,
                    "website": website,
                    "phone": phone_el.get_text(strip=True) if phone_el else None,
                    "address": addr_el.get_text(" ", strip=True) if addr_el else None,
                    "description": "",
                    "verified": True,
                })
        except Exception as e:
            logger.warning("YellowPages search failed for %s: %s", query, e)
        return results
