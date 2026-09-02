import asyncio
import json
import logging
from typing import List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from ..config import settings
from .groq_engine import groq_engine

logger = logging.getLogger("spresy.gemini")
logging.getLogger("google_genai.models").setLevel(logging.WARNING)

class LeadScore(BaseModel):
    score: float
    category: str
    summary: str

class LeadExtracted(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    website: Optional[str]

class GeminiEngine:
    """Primary AI engine powered by Google Gemini, with key rotation and Groq fallback."""

    def __init__(self):
        self._api_keys = settings.gemini_api_keys
        self.available = len(self._api_keys) > 0
        self._clients = [genai.Client(api_key=k) for k in self._api_keys]
        self._current_index = 0
        logger.info("GeminiEngine initialized with %d API key(s)", len(self._api_keys))

    async def _execute_with_fallback(self, coro_func):
        """Execute an API call with sticky fallback across all available Gemini keys."""
        if not self.available:
            return None

        errors = []
        for i in range(len(self._clients)):
            client_idx = (self._current_index + i) % len(self._clients)
            client = self._clients[client_idx]
            try:
                resp = await asyncio.wait_for(coro_func(client), timeout=25.0)
                # Success — stick with this key
                self._current_index = client_idx
                return resp
            except asyncio.TimeoutError:
                errors.append(f"Timeout on Gemini key {client_idx}")
                logger.debug("Gemini client %d timed out", client_idx)
            except Exception as e:
                error_str = str(e)
                # 400 = bad prompt, don't retry with other keys
                if "400" in error_str and "Bad Request" in error_str:
                    logger.debug("Gemini 400 Bad Request on key %d: %s. Not retrying.", client_idx, e)
                    return None
                errors.append(error_str)
                logger.debug("Gemini client %d failed: %s", client_idx, e)

        logger.warning("All %d Gemini API keys failed. Errors: %s", len(self._clients), errors)
        return None

    async def generate_queries(self, keyword: str, location: Optional[str]) -> List[str]:
        """Expand a user keyword into multiple effective search queries."""
        if not self.available:
            return await groq_engine.generate_queries(keyword, location)

        loc_str = f" in {location}" if location else ""
        prompt = (
            f"You are a lead-generation expert. Your job is to find REAL, LOCAL BUSINESSES "
            f"that match: '{keyword}'{loc_str}.\n\n"
            "Generate 6 search queries designed to surface INDIVIDUAL BUSINESS WEBSITES "
            "(e.g. a specific café's own website, a restaurant's contact page, a shop's homepage). "
            "IMPORTANT RULES:\n"
            "- Each query MUST be designed to return a specific business's own website, NOT lists/articles.\n"
            "- Do NOT generate queries that would return news articles, government pages, Wikipedia, "
            "Forbes lists, Billboard charts, or market cap databases.\n"
            "- Use formats like: '<business type> <location> contact', "
            "'<business type> <location> phone number', '<specific business name> <location>'.\n"
            "- Include 1-2 queries targeting Indian directories: prefix with 'site:justdial.com' or "
            "'site:sulekha.com' if the location is Indian.\n"
            "- Output ONLY the raw queries, one per line, no numbering, no explanation."
        )

        async def call(client):
            return await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7),
            )

        resp = await self._execute_with_fallback(call)
        if resp and resp.text:
            queries = [q.strip() for q in resp.text.splitlines() if q.strip() and not q.startswith("```")]
            if queries:
                return queries

        # Fallback to Groq
        logger.info("Gemini query generation failed; falling back to Groq.")
        return await groq_engine.generate_queries(keyword, location)

    async def qualify_lead(self, name: str, description: str = "", keyword: str = "") -> dict:
        """Score a lead (0-100) for relevance to the search keyword."""
        if not self.available:
            return await groq_engine.qualify_lead(name, description, keyword)

        prompt = (
            "Rate this business lead's relevance to the query on a scale of 0 to 100. "
            "If the business is completely unrelated to the query, OR if the business is clearly located in the WRONG city/location (based on its name or description), you MUST return a score of 0. "
            f'\n\nQuery: "{keyword}"\nBusiness name: "{name}"\nDescription: "{description[:500]}"\n\n'
            "You MUST return a valid JSON object with the following keys: "
            '"score" (float), "category" (string), "summary" (string).'
        )

        async def call(client):
            return await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )

        resp = await self._execute_with_fallback(call)
        if resp and resp.text:
            try:
                data = json.loads(resp.text)
                return {
                    "score": max(0.0, min(100.0, float(data.get("score", 50)))),
                    "summary": str(data.get("summary", "")),
                    "category": str(data.get("category", "")),
                }
            except Exception:
                pass

        # Fallback to Groq
        logger.info("Gemini lead scoring failed; falling back to Groq.")
        return await groq_engine.qualify_lead(name, description, keyword)

    async def extract_structured(self, text: str) -> dict:
        """Extract name/email/phone/address from raw text."""
        if not self.available:
            return await groq_engine.extract_structured(text)

        if not text or len(text.strip()) < 10:
            return {}

        prompt = (
            "Extract business contact info from the text below.\n"
            "Use null for missing fields.\n\nTEXT:\n" + text[:3000] +
            '\n\nYou MUST return a valid JSON object with the following keys: '
            '"name" (string or null), "email" (string or null), "phone" (string or null), "address" (string or null), "website" (string or null).'
        )

        async def call(client):
            return await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )

        resp = await self._execute_with_fallback(call)
        if resp and resp.text:
            try:
                return json.loads(resp.text)
            except Exception:
                pass

        # Fallback to Groq
        logger.info("Gemini extraction failed; falling back to Groq.")
        return await groq_engine.extract_structured(text)

gemini_engine = GeminiEngine()
