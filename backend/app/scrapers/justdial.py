import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..utils.contact_extractor import extract_phones
from .base import BaseScraper

logger = logging.getLogger("spresy.justdial")


class JustDialScraper(BaseScraper):
    """
    Tier 2. JustDial — India's largest local search / directory.
    Note: JustDial has aggressive anti-bot (Cloudflare). May return []
    from some networks; results are best-effort.
    """

    name = "justdial"
    display_name = "JustDial"
    yields_leads = True
    tier = 2

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        slug = re.sub(r"[\s]+", "-", query.lower().strip())
        slug = re.sub(r"[^a-z0-9\-]", "", slug)
        if not slug:
            return results
        loc = (self.location or "india").lower().replace(" ", "-")
        url = f"https://www.justdial.com/{loc}/{slug}"
        try:
            resp = await self.client.get(url)
            html = resp.text if resp.status_code == 200 else None
            if html is None:
                from ..utils.playwright_fetcher import playwright_fetch
                html = await playwright_fetch(url, wait_selector=".store, .cntanr, .jcard")
            if not html:
                logger.debug("JustDial returned no usable HTML for %s", url)
                return results
            soup = BeautifulSoup(html, "lxml")
            for store in soup.select(".store, .cntanr, .jcard")[:limit]:
                name_el = store.select_one("h2 a, .jcn h2 a, .store-name a")
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                href = name_el.get("href", "")
                website = f"https://www.justdial.com{href}" if href.startswith("/") else href
                phone_el = store.select_one(".telnowpr, a[class*='tel']")
                phone = None
                if phone_el:
                    phones = extract_phones(phone_el.get_text(" ", strip=True))
                    phone = phones[0] if phones else None
                addr_el = store.select_one(".address-info, .jcnt, .add")
                results.append({
                    "name": name,
                    "website": website,
                    "phone": phone,
                    "address": addr_el.get_text(" ", strip=True) if addr_el else None,
                    "description": "",
                    "verified": True,
                    "source": "justdial",
                })
        except Exception as e:
            logger.warning("JustDial search failed for %s: %s", query, e)
        return results
