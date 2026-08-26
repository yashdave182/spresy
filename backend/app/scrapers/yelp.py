import json
import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger("spresy.yelp")


class YelpScraper(BaseScraper):
    """
    Yelp business directory. Parses embedded JSON-LD / structured data
    present in public search pages to extract phone & website legally.
    """

    name = "yelp"
    display_name = "Yelp"
    yields_leads = True

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
        url = f"https://www.yelp.com/search?find_desc={quote_plus(query)}"
        if self.location:
            url += f"&find_loc={quote_plus(self.location)}"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            # 1) Embedded JSON-LD scripts
            for script in soup.select("script[type='application/ld+json']"):
                try:
                    data = json.loads(script.string)
                except Exception:
                    continue
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict) or item.get("@type") not in ("LocalBusiness", "Restaurant", "Place"):
                        continue
                    results.append(self._from_jsonld(item))
                    if len(results) >= limit:
                        return results
            # 2) Fallback: h3/a anchors with data-hovercard-id
            if len(results) < limit:
                for card in soup.select("div[data-hovercard-id]"):
                    name_el = card.select_one("h3 a")
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    href = name_el.get("href", "")
                    results.append({
                        "name": name,
                        "website": f"https://www.yelp.com{href}" if href.startswith("/") else href,
                        "description": "",
                    })
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.warning("Yelp search failed for %s: %s", query, e)
        return results

    def _from_jsonld(self, item: dict) -> dict:
        addr = item.get("address") or {}
        return {
            "name": item.get("name", ""),
            "website": item.get("url") or item.get("website"),
            "phone": item.get("telephone"),
            "address": ", ".join([
                a for a in [
                    addr.get("streetAddress"),
                    addr.get("addressLocality"),
                    addr.get("addressRegion"),
                    addr.get("postalCode"),
                ] if a
            ]) or None,
            "rating": item.get("aggregateRating", {}).get("ratingValue") if isinstance(item.get("aggregateRating"), dict) else None,
            "description": item.get("description", ""),
            "verified": True,
        }
