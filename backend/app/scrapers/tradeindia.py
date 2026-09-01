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
    Tier 2. TradeIndia — Indian B2B marketplace.
    Uses the COMPANY/SUPPLIER directory, not the product search.
    Product search returns furniture/equipment, not businesses.
    """

    name = "tradeindia"
    display_name = "TradeIndia"
    yields_leads = True
    tier = 2

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []

        # Build a slug for the company directory URL
        # e.g. "cafes in Ahmedabad" -> "cafes-in-ahmedabad"
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower().strip()).strip("-")
        loc = (self.location or "").lower().strip()

        # Try company directory first — this returns actual supplier/business listings
        urls_to_try = [
            f"https://www.tradeindia.com/companies/{quote_plus(query)}.html",
            f"https://www.tradeindia.com/sellers/{slug}.html",
        ]
        if loc:
            loc_slug = re.sub(r"[^a-z0-9]+", "-", loc).strip("-")
            urls_to_try.insert(0, f"https://www.tradeindia.com/companies/{loc_slug}/{slug}.html")

        html = None
        for url in urls_to_try:
            try:
                resp = await self.client.get(url)
                if resp.status_code == 200 and len(resp.text) > 2000:
                    html = resp.text
                    break
            except Exception:
                pass

        if not html:
            logger.warning("TradeIndia: no company directory results for %r", query)
            return results

        soup = BeautifulSoup(html, "lxml")

        # Company cards on the directory page
        cards = soup.select("div.company-listing, div.supplier-card, div.comp-dtl, li.comp-list-item, div.card-wrap")
        if not cards:
            # Fallback: any block with a company link
            cards = soup.select("li.clearfix, div.clearfix")

        for card in cards[:limit]:
            name_el = card.select_one("h2 a, h3 a, .comp-name a, a.company-name")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            if not name or len(name) < 3:
                continue

            href = name_el.get("href", "")
            website = href if href.startswith("http") else (
                f"https://www.tradeindia.com{href}" if href.startswith("/") else ""
            )

            text = card.get_text(" ", strip=True)
            phones = extract_phones(text)

            # Location
            loc_el = card.select_one(".location, .city, .addr, .address")
            addr = loc_el.get_text(" ", strip=True) if loc_el else (self.location or None)

            # Description / category
            desc_el = card.select_one(".description, .nature-of-business, .catname, p")
            desc = desc_el.get_text(" ", strip=True)[:300] if desc_el else text[:200]

            results.append({
                "name": name,
                "website": website,
                "phone": phones[0] if phones else None,
                "address": addr,
                "description": desc,
                "verified": True,
                "source": "tradeindia",
            })
            if len(results) >= limit:
                break

        return results
