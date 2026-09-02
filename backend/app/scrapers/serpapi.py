import logging
from typing import List

import httpx

from ..config import settings
from ..utils.contact_extractor import extract_phones
from .base import BaseScraper

logger = logging.getLogger("spresy.serpapi")


class SerpApiScraper(BaseScraper):
    """
    Google Search via SerpAPI — structured, geo-targeted, no captcha issues.
    Requires SERPAPI_KEY to be set. Falls back gracefully (returns []) otherwise.
    Returns URLs for the Playwright crawler (yields_leads = False).
    """

    name = "serpapi"
    display_name = "Google (SerpAPI)"
    yields_leads = False  # Feed URLs to the Playwright website crawler

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        if not settings.SERPAPI_KEY:
            logger.info("SERPAPI_KEY not set; skipping SerpAPI Google Search.")
            return []

        search_query = query
        if self.location and self.location.lower() not in query.lower():
            search_query = f"{query} {self.location}"

        params = {
            "engine": "google",
            "q": search_query,
            "api_key": settings.SERPAPI_KEY,
            "num": str(min(limit, 20)),
            "hl": "en",
        }
        # If a location is provided, use SerpAPI's location targeting
        if self.location:
            params["location"] = self.location

        results: List[dict] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get("https://serpapi.com/search.json", params=params)
                data = resp.json()

            # Process organic results
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

            logger.info("SerpAPI returned %d organic results for %r", len(results), search_query)
        except Exception as e:
            logger.warning("SerpAPI search failed for %s: %s", query, e)
        return results
