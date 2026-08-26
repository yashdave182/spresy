import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger("spresy.bbb")


class BBBScraper(BaseScraper):
    """
    Better Business Bureau directory (US). Reliable, permissionless public data.
    """

    name = "bbb"
    display_name = "BBB"
    yields_leads = True

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        url = f"https://www.bbb.org/search?find_text={quote_plus(query)}"
        if self.location:
            url += f"&find_loc={quote_plus(self.location)}"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                logger.debug("BBB returned %s", resp.status_code)
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select(".m-pg-search__listing, .search-results__item, .listing")[:limit]:
                name_el = card.select_one("a, h3 a, .listing__title a")
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                href = name_el.get("href", "")
                phone_el = card.select_one("[data-phone], .m-pg-search__phone, .listing__phone")
                addr_el = card.select_one(".m-pg-search__address, .listing__address, [data-address]")
                website_el = card.select_one("a[href*='http']")
                results.append({
                    "name": name,
                    "website": website_el.get("href") if website_el and website_el.get("href", "").startswith("http") else (f"https://www.bbb.org{href}" if href.startswith("/") else href),
                    "phone": phone_el.get_text(" ", strip=True) if phone_el else None,
                    "address": addr_el.get_text(" ", strip=True) if addr_el else None,
                    "description": "",
                    "verified": True,
                })
            # Fallback: parse JSON-LD when present
            if not results:
                for script in soup.select("script[type='application/ld+json']"):
                    import json
                    try:
                        data = json.loads(script.string or "")
                    except Exception:
                        continue
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if not isinstance(item, dict) or item.get("@type") not in ("LocalBusiness", "Organization", "ProfessionalService"):
                            continue
                        addr = item.get("address") or {}
                        results.append({
                            "name": item.get("name", ""),
                            "website": item.get("url") or item.get("sameAs", [None])[0] if isinstance(item.get("sameAs"), list) else item.get("url"),
                            "phone": item.get("telephone"),
                            "address": ", ".join([a for a in [
                                addr.get("streetAddress"), addr.get("addressLocality"),
                                addr.get("addressRegion"), addr.get("postalCode"),
                            ] if a]) or None,
                            "description": item.get("description", ""),
                            "verified": True,
                        })
        except Exception as e:
            logger.warning("BBB search failed for %s: %s", query, e)
        return results
