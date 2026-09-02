import logging
from typing import List

import httpx

from ..config import settings
from .base import BaseScraper

logger = logging.getLogger("spresy.gmaps")


class GoogleMapsScraper(BaseScraper):
    """
    Google Maps local results via SerpAPI.
    Supports multiple API keys with automatic fallback.
    """

    name = "google_maps"
    display_name = "Google Maps"
    yields_leads = True

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        keys = settings.serpapi_keys
        if not keys:
            logger.info("No SERPAPI_KEY set; skipping Google Maps source.")
            return []

        search_query = query
        if self.location and self.location.lower() not in query.lower():
            search_query = f"{query} {self.location}"

        base_params = {
            "engine": "google_maps",
            "q": search_query,
            "type": "search",
            "hl": "en",
        }

        results: List[dict] = []
        for idx, key in enumerate(keys):
            try:
                params = {**base_params, "api_key": key}
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get("https://serpapi.com/search.json", params=params)
                    data = resp.json()

                # Check for API errors
                if "error" in data:
                    logger.warning("Google Maps SerpAPI key %d error: %s", idx, data["error"])
                    continue  # Try next key

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

                logger.info("Google Maps key %d returned %d results for %r", idx, len(results), search_query)
                return results  # Success — stop trying more keys

            except Exception as e:
                logger.warning("Google Maps SerpAPI key %d failed for %s: %s", idx, query, e)
                continue  # Try next key

        logger.warning("All %d SerpAPI keys exhausted for Google Maps query: %s", len(keys), query)
        return results
