import logging
from typing import List
from urllib.parse import quote_plus

import httpx

from ..config import settings
from .base import BaseScraper

logger = logging.getLogger("spresy.gmaps")


class GoogleMapsScraper(BaseScraper):
    """
    Google Maps local results.
    Requires SERPAPI_KEY to be set. Falls back gracefully (returns []) otherwise.
    """

    name = "google_maps"
    display_name = "Google Maps"
    yields_leads = True

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        if not settings.SERPAPI_KEY:
            logger.info("SERPAPI_KEY not set; skipping Google Maps source.")
            return []
        params = {
            "engine": "google_maps",
            "q": query,
            "api_key": settings.SERPAPI_KEY,
            "type": "search",
            "hl": "en",
        }
        # We do not pass `ll` because it requires lat/long coordinates, not a city string.
        # The location is already injected into the `q` (query) string by groq_engine.
        results: List[dict] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get("https://serpapi.com/search.json", params=params)
                data = resp.json()
            for item in data.get("local_results", [])[:limit]:
                address = " ".join([
                    a for a in [
                        item.get("address"),
                        item.get("street_address", ""),
                        item.get("city", ""),
                        item.get("state", ""),
                        item.get("country", ""),
                    ] if a
                ]) or None
                results.append({
                    "name": item.get("title") or item.get("name", ""),
                    "website": item.get("website") or item.get("link"),
                    "email": item.get("email"),
                    "phone": item.get("phone") or item.get("phone_number"),
                    "address": address,
                    "rating": item.get("rating"),
                    "description": item.get("description") or item.get("snippet", ""),
                    "verified": True,
                })
        except Exception as e:
            logger.warning("Google Maps search failed for %s: %s", query, e)
        return results
