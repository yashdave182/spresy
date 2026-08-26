import base64
import logging
from typing import List
from urllib.parse import parse_qs, quote_plus, urlparse, unquote

from bs4 import BeautifulSoup

from .base import BaseScraper

logger = logging.getLogger("spresy.bing")


def _decode_bing_url(href: str) -> str:
    """Bing wraps result links in /ck/a redirects with base64-encoded real URLs."""
    if href.startswith("//") or "bing.com/ck/a" not in href:
        return href
    parsed = parse_qs(urlparse(href).query)
    target = parsed.get("u", [None])[0]
    if target:
        # Bing encodes the real URL as base64 (sometimes prefixed with 'a1')
        try:
            b64 = target[2:] if target.startswith("a1") else target
            decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
            if decoded.startswith("http"):
                return decoded
        except Exception:
            pass
        return unquote(target)
    return href


class BingScraper(BaseScraper):
    """Searches Bing for business sites matching the query."""

    name = "bing"
    display_name = "Bing"
    yields_leads = False

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        url = f"https://www.bing.com/search?q={quote_plus(query)}&count={limit}"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            for li in soup.select("li.b_algo")[:limit]:
                link = li.select_one("h2 a")
                if not link or not link.get("href"):
                    continue
                href = link["href"]
                href = _decode_bing_url(href)
                snippet = li.select_one(".b_caption p, .b_lineclamp2, .b_caption")
                caption = li.select_one("cite, .b_attribution")
                results.append({
                    "name": link.get_text(strip=True),
                    "website": href,
                    "description": snippet.get_text(strip=True) if snippet else "",
                    "title": link.get_text(strip=True),
                    "display_url": caption.get_text(strip=True) if caption else "",
                })
        except Exception as e:
            logger.warning("Bing search failed for %s: %s", query, e)
        return results
