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
    """Primary AI engine powered by Google Gemini, with Groq fallback."""

    def __init__(self):
        self._api_key = settings.GEMINI_API_KEY
        self.available = bool(self._api_key)
        if self.available:
            self.client = genai.Client(api_key=self._api_key)
        else:
            self.client = None

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

        try:
            resp = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7),
            )
            content = resp.text or ""
            queries = [q.strip() for q in content.splitlines() if q.strip() and not q.startswith("```")]
            if queries:
                return queries
        except Exception as e:
            logger.warning("Gemini failed to generate queries: %s. Falling back to Groq.", e)
            return await groq_engine.generate_queries(keyword, location)

        return groq_engine._fallback_queries(keyword, location)

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

        try:
            resp = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            if resp.text:
                data = json.loads(resp.text)
                return {
                    "score": max(0.0, min(100.0, float(data.get("score", 50)))),
                    "summary": str(data.get("summary", "")),
                    "category": str(data.get("category", "")),
                }
        except Exception as e:
            logger.warning("Gemini failed to score lead: %s. Falling back to Groq.", e)
            return await groq_engine.qualify_lead(name, description, keyword)

        return {"score": 50.0, "summary": "", "category": ""}

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

        try:
            resp = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            if resp.text:
                return json.loads(resp.text)
        except Exception as e:
            logger.warning("Gemini failed to extract info: %s. Falling back to Groq.", e)
            return await groq_engine.extract_structured(text)

        return {}

gemini_engine = GeminiEngine()
