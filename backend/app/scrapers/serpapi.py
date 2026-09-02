import logging
from typing import List

import httpx

from ..config import settings
from ..utils.contact_extractor import extract_phones
from .base import BaseScraper

logger = logging.getLogger("spresy.serpapi")


def _get_serpapi_keys() -> List[str]:
    """Collect all SerpAPI keys: SERPAPI_KEY, SERPAPI_KEY1, SERPAPI_KEY2, ..."""
    return settings.serpapi_keys


class SerpApiScraper(BaseScraper):
    """
    Google Search via SerpAPI — structured, geo-targeted, no captcha issues.
    Supports multiple API keys with automatic fallback.
    Returns URLs for the Playwright crawler (yields_leads = False).
    """

    name = "serpapi"
    display_name = "Google (SerpAPI)"
    yields_leads = False  # Feed URLs to the Playwright website crawler

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        keys = _get_serpapi_keys()
        if not keys:
            logger.info("No SERPAPI_KEY set; skipping SerpAPI Google Search.")
            return []

        search_query = query
        if self.location and self.location.lower() not in query.lower():
            search_query = f"{query} {self.location}"

        base_params = {
            "engine": "google",
            "q": search_query,
            "num": str(min(limit, 20)),
            "hl": "en",
        }
        if self.location:
            base_params["location"] = self.location

        results: List[dict] = []
        for idx, key in enumerate(keys):
            try:
                params = {**base_params, "api_key": key}
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get("https://serpapi.com/search.json", params=params)
                    data = resp.json()

                # Check for API errors (rate limit, invalid key, etc.)
                if "error" in data:
                    logger.warning("SerpAPI key %d error: %s", idx, data["error"])
                    continue  # Try next key

                for item in data.get("organic_results", [])[:limit]:
                    link = item.get("link", "")
                    if not link:
                        continue
                    snippet = item.get("snippet", "")
                    phones = extract_phones(snippet)
                    results.append({
                        "name": item.get("title", ""),
                        "website": link,
                        "description": snippet,
                        "phone": phones[0] if phones else None,
                        "address": self.location or None,
                        "source": "serpapi",
                    })

                logger.info("SerpAPI key %d returned %d organic results for %r", idx, len(results), search_query)
                return results  # Success — stop trying more keys

            except Exception as e:
                logger.warning("SerpAPI key %d failed for %s: %s", idx, query, e)
                continue  # Try next key

        logger.warning("All %d SerpAPI keys exhausted for query: %s", len(keys), query)
        return results
