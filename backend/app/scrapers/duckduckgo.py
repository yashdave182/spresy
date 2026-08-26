import logging
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger("spresy.duckduckgo")


class DuckDuckGoScraper(BaseScraper):
    """Searches DuckDuckGo (HTML endpoint) for business sites matching the query."""

    name = "duckduckgo"
    display_name = "DuckDuckGo"
    yields_leads = False

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                logger.debug("DDG returned %s", resp.status_code)
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            for result in soup.select(".result")[:limit]:
                link = result.select_one("a.result__a")
                if not link or not link.get("href"):
                    continue
                href = link["href"]
                if href.startswith("//duckduckgo.com/l/"):
                    # Extract real URL from redirect
                    from urllib.parse import parse_qs, urlparse
                    parsed = parse_qs(urlparse(href).query)
                    href = parsed.get("uddg", [href])[0]
                snippet = result.select_one(".result__snippet")
                title = link.get_text(strip=True)
                results.append({
                    "name": title,
                    "website": href,
                    "description": snippet.get_text(strip=True) if snippet else "",
                    "title": title,
                })
        except Exception as e:
            logger.warning("DDG search failed for %s: %s", query, e)
        return results
