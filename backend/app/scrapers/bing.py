import base64
import logging
import os
from typing import List
from urllib.parse import parse_qs, quote_plus, urlparse, unquote

from bs4 import BeautifulSoup

from ..utils.contact_extractor import extract_phones
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
            # Add padding
            b64 += "=" * ((4 - len(b64) % 4) % 4)
            # Use urlsafe decode and fallback to standard decode
            decoded = base64.urlsafe_b64decode(b64).decode("utf-8", errors="ignore")
            if decoded.startswith("http"):
                return decoded
        except Exception:
            try:
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

    @property
    def yields_leads(self) -> bool:  # type: ignore[override]
        # On Vercel the website crawler is disabled — produce leads directly.
        # On Render/local, feed URLs to the Playwright crawler instead.
        return bool(os.environ.get("VERCEL"))

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        results: List[dict] = []
        url = f"https://www.bing.com/search?q={quote_plus(query)}&count={limit}"
        try:
            resp = await self.client.get(url)
            if resp.status_code >= 300:
                return results
            soup = BeautifulSoup(resp.text, "lxml")
            for li in soup.select("li.b_algo")[:limit]:
                link = li.select_one("h2 a")
                if not link or not link.get("href"):
                    continue
                href = link["href"]
                href = _decode_bing_url(href)
                snippet = li.select_one(".b_caption p, .b_lineclamp2, .b_caption")
                snippet_text = snippet.get_text(strip=True) if snippet else ""
                phones = extract_phones(snippet_text)
                results.append({
                    "name": link.get_text(strip=True),
                    "website": href,
                    "description": snippet_text,
                    "phone": phones[0] if phones else None,
                    "address": self.location or None,
                    "source": "bing",
                })
        except Exception as e:
            logger.warning("Bing search failed for %s: %s", query, e)
        return results

