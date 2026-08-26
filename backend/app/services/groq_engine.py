import asyncio
import json
import logging
from typing import List, Optional

from groq import AsyncGroq

from ..config import settings

logger = logging.getLogger("spresy.groq")


class GroqEngine:
    """AI engine powered by Groq Cloud API (fast LLM inference)."""

    def __init__(self, api_keys: List[str] = None):
        if api_keys is None:
            self._api_keys = getattr(settings, "groq_api_keys", [])
            if not self._api_keys and settings.GROQ_API_KEY:
                self._api_keys = [settings.GROQ_API_KEY]
        else:
            self._api_keys = api_keys

        self.available = len(self._api_keys) > 0
        self._clients = [AsyncGroq(api_key=k, max_retries=0) for k in self._api_keys]
        self._current_index = 0

    async def _execute_with_fallback(self, coro_func):
        """Execute an API call with sticky fallback across all available keys."""
        if not self.available:
            return None
        
        errors = []
        for i in range(len(self._clients)):
            client_idx = (self._current_index + i) % len(self._clients)
            client = self._clients[client_idx]
            try:
                resp = await asyncio.wait_for(coro_func(client), timeout=20.0)
                # Success! Make this the new primary key to avoid unnecessary 429 delays next time
                self._current_index = client_idx
                return resp
            except asyncio.TimeoutError:
                errors.append(f"Timeout on key {client_idx}")
                logger.debug("Groq client %d timed out", client_idx)
            except Exception as e:
                # If it's a 400 Bad Request, it's a prompt issue, NOT a rate limit.
                # Don't try other keys for a 400.
                if hasattr(e, "status_code") and e.status_code == 400:
                    logger.debug("Groq 400 Bad Request on key %d: %s. Not retrying.", client_idx, e)
                    return None
                
                errors.append(str(e))
                logger.debug("Groq client %d failed: %s", client_idx, e)
                
        logger.warning("All Groq API keys failed or timed out. Errors: %s", errors)
        return None

    async def generate_queries(self, keyword: str, location: Optional[str]) -> List[str]:
        """Expand a user keyword into multiple effective search queries."""
        prompt = (
            "You are a lead-generation search strategist. Generate 6-10 diverse, "
            "effective search queries (one per line) to find real businesses/contacts "
            f"for: '{keyword}'"
            + (f" in {location}" if location else " (no specific location)")
            + ".\nInclude varied phrasings (service names, industry terms, plural/singular, "
            "local colloquial terms). Output ONLY the queries, one per line, no numbering."
        )
        
        async def call(client):
            return await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=400,
            )

        resp = await self._execute_with_fallback(call)
        if resp:
            content = resp.choices[0].message.content or ""
            queries = [q.strip() for q in content.splitlines() if q.strip()]
            if queries:
                return queries
                
        return self._fallback_queries(keyword, location)

    def _fallback_queries(self, keyword: str, location: Optional[str]) -> List[str]:
        loc = f" {location}" if location else ""
        base = []
        if location:
            base.append(f"{keyword} {location}")
            base.append(f"{keyword} in {location}")
            base.append(f"{keyword} {location} phone email contact")
            base.append(f"{keyword} company {location}")
            base.append(f"{keyword} business {location}")
        base.append(f"{keyword}")
        for suffix in ("near me", "list", "directory", "contact", "suppliers", "companies", "phone number"):
            if location:
                base.append(f"{keyword} {suffix} {location}")
            else:
                base.append(f"{keyword} {suffix}")
        return list(dict.fromkeys(base))[:12]

    async def qualify_lead(self, name: str, description: str = "", keyword: str = "") -> dict:
        """Score a lead (0-100) for relevance to the search keyword."""
        result = {"score": 50.0, "summary": "", "category": ""}
        if not self.available:
            return result
            
        prompt = (
            "Rate this business lead's relevance to the query on a scale of 0 to 100. "
            "If the business is completely unrelated to the query, OR if the business is clearly located in the WRONG city/location (based on its name or description), you MUST return a score of 0. "
            "Return JSON only:\n"
            '{"score": 0-100, "category": "business type", "summary": "one short line"}'
            f'\n\nQuery: "{keyword}"\nBusiness name: "{name}"\nDescription: "{description[:500]}"'
        )

        async def call(client):
            return await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

        resp = await self._execute_with_fallback(call)
        if resp:
            content = resp.choices[0].message.content or "{}"
            try:
                data = json.loads(content)
                result["score"] = max(0.0, min(100.0, float(data.get("score", 50))))
                result["summary"] = str(data.get("summary", ""))
                result["category"] = str(data.get("category", ""))
            except Exception:
                pass
        else:
            # Fallback to a simple keyword overlap check instead of defaulting to 50
            query_words = set(keyword.lower().split())
            text_lower = name.lower() + " " + description.lower()
            if any(w in text_lower for w in query_words if len(w) > 2):
                result["score"] = 50.0
            else:
                result["score"] = 0.0
                
        return result

    async def extract_structured(self, text: str) -> dict:
        """Extract name/email/phone/address from raw text using Groq (fallback to regex)."""
        if not self.available or not text or len(text.strip()) < 10:
            return {}
            
        prompt = (
            "Extract business contact info from the text below. Return JSON only:\n"
            '{"name": "...", "email": "...", "phone": "...", "address": "...", "website": "..."}\n'
            "Use null for missing fields.\n\nTEXT:\n" + text[:3000]
        )

        async def call(client):
            return await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=250,
                response_format={"type": "json_object"},
            )

        resp = await self._execute_with_fallback(call)
        if resp:
            content = resp.choices[0].message.content or "{}"
            try:
                return json.loads(content)
            except Exception:
                pass
        return {}

    async def clean_phone(self, phone: str) -> str:
        """Use AI to normalize a phone number if regex can't."""
        return phone


groq_engine = GroqEngine()
