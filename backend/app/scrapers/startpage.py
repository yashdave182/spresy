import logging
import os
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..utils.contact_extractor import extract_phones
from .base import BaseScraper

logger = logging.getLogger("spresy.startpage")


class StartpageScraper(BaseScraper):
    """
    Startpage (privacy proxy over Google) search results.
    Reliable, no API key required.
    On Vercel: produces leads directly (crawler is disabled).
    On Render/local: feeds URLs to the Playwright crawler.
    """

    name = "startpage"
    display_name = "Startpage"

    @property
    def yields_leads(self) -> bool:  # type: ignore[override]
        return bool(os.environ.get("VERCEL"))

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        url = f"https://www.startpage.com/sp/search?query={quote_plus(query)}"
        try:
            resp = await self.client.get(url)
            if resp.status_code >= 300:
                logger.debug("Startpage returned %s", resp.status_code)
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            for result in soup.select(".w-gl__result, .result, [data-testid='result']")[:limit]:
                link = result.select_one("a.result-link, h2 a, a[href]")
                if not link:
                    continue
                href = link.get("href", "")
                if not href or href.startswith(("//", "#", "javascript:")):
                    continue
                snippet = result.select_one(".w-gl__description, .result-description, p")
                title = link.get_text(strip=True) or href
                snippet_text = snippet.get_text(strip=True) if snippet else ""
                phones = extract_phones(snippet_text)
                results.append({
                    "name": title,
                    "website": href,
                    "description": snippet_text,
                    "phone": phones[0] if phones else None,
                    "address": self.location or None,
                    "source": "startpage",
                })
        except Exception as e:
            logger.warning("Startpage search failed for %s: %s", query, e)
        return results

