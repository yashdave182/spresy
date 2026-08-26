import logging
from typing import List
from urllib.parse import quote_plus

import httpx

from ..config import settings
from .base import BaseScraper

logger = logging.getLogger("spresy.googleplaces")

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GooglePlacesScraper(BaseScraper):
    """
    Tier 1 official API. Google Places Text Search + Place Details.
    Returns verified business name, address, phone, website, rating.
    Requires GOOGLE_PLACES_API_KEY.
    """

    name = "google_places"
    display_name = "Google Places (API)"
    yields_leads = True
    tier = 1

    async def search(self, query: str, limit: int = 20) -> List[dict]:
        if not settings.GOOGLE_PLACES_API_KEY:
            logger.info("GOOGLE_PLACES_API_KEY not set; skipping.")
            return []
        key = settings.GOOGLE_PLACES_API_KEY
        results: List[dict] = []

        # Geocode location to lat,lng so results are region-locked
        location_bias = ""
        if self.location:
            geocode = await self._geocode(key, self.location)
            if geocode:
                location_bias = f"&location={geocode}&radius=50000"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = (
                    f"{TEXT_SEARCH_URL}?query={quote_plus(query)}"
                    f"{location_bias}&region=in&key={key}"
                )
                resp = await client.get(url)
                data = resp.json()
                places = data.get("results", [])[:limit]
                for place in places:
                    place_id = place.get("place_id")
                    detail = await self._details(client, key, place_id) if place_id else {}
                    results.append(self._from_place(place, detail))
        except Exception as e:
            logger.warning("Google Places search failed for %s: %s", query, e)
        return results

    async def _geocode(self, key: str, location: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{GEOCODE_URL}?address={quote_plus(location)}&key={key}")
                data = resp.json()
                loc = data.get("results", [{}])[0].get("geometry", {}).get("location")
                if loc:
                    return f"{loc['lat']},{loc['lng']}"
        except Exception:
            pass
        return ""

    async def _details(self, client, key: str, place_id: str) -> dict:
        """Fetch full details (phone, website) via Place Details endpoint."""
        try:
            fields = "formatted_address,international_phone_number,website,rating,url,name,types"
            resp = await client.get(
                f"{DETAILS_URL}?place_id={place_id}&fields={fields}&key={key}"
            )
            return resp.json().get("result", {})
        except Exception:
            return {}

    def _from_place(self, place: dict, detail: dict) -> dict:
        merged = {**place, **(detail or {})}
        return {
            "name": merged.get("name", ""),
            "website": merged.get("website") or merged.get("url"),
            "phone": merged.get("international_phone_number") or merged.get("formatted_phone_number"),
            "address": merged.get("formatted_address"),
            "rating": merged.get("rating"),
            "description": " ".join(merged.get("types", [])) or "",
            "category": ", ".join(merged.get("types", [])[:2]),
            "verified": True,
            "source": "google_places",
        }
