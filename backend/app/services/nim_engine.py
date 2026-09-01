import asyncio
import json
import logging
from typing import List, Optional

from openai import AsyncOpenAI

from ..config import settings

logger = logging.getLogger("spresy.nim")


class NIMEngine:
    """NVIDIA NIM API engine (OpenAI-compatible) for embeddings & classification."""

    def __init__(self, api_key: str = None, base_url: str = None):
        self._api_key = api_key or settings.NIM_API_KEY
        self._base_url = base_url or settings.NIM_BASE_URL
        self._client: Optional[AsyncOpenAI] = None
        self.available = bool(self._api_key)

    def _get_client(self) -> Optional[AsyncOpenAI]:
        if not self.available:
            return None
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                max_retries=0,
            )
        return self._client

    async def embed_texts(self, texts: List[str], max_chars: int = 1500) -> List[List[float]]:
        """Compute embeddings for a list of short texts (up to 96 inputs)."""
        client = self._get_client()
        if not client or not texts:
            return []
        truncated = [t[:max_chars] for t in texts[:96]]
        try:
            resp = await client.embeddings.create(
                model=settings.NIM_EMBED_MODEL,
                input=truncated,
                encoding_format="float",
            )
            return [item.embedding for item in resp.data]
        except Exception as e:
            logger.warning("NIM embed failed: %s", e)
            return []

    async def classify_lead(self, name: str, description: str) -> dict:
        """Classify a lead using NIM chat model (cheap semantic classification)."""
        client = self._get_client()
        if not client:
            return {"category": "", "relevant": True, "summary": ""}
        prompt = (
            "Classify this business. Return JSON only:\n"
            '{"category": "industry/business type", "relevant": true/false, '
            '"summary": "one short sentence"}\n\n'
            f'Business: "{name}"\nDetails: "{description[:800]}"'
        )
        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.NIM_CHAT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=150,
                    response_format={"type": "json_object"},
                ),
                timeout=15.0,
            )
            content = resp.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            err_str = str(e)
            # 410 Gone = model endpoint permanently deleted; disable to stop wasting time
            if "410" in err_str or "404" in err_str or "Gone" in err_str:
                logger.warning("NIM endpoint gone (410/404) — disabling NIM for this session: %s", e)
                self.available = False
            else:
                logger.debug("NIM classify failed: %s", e)
            return {"category": "", "relevant": True, "summary": ""}

    async def dedupe_candidates(self, candidates: List[str]) -> List[int]:
        """Use embeddings to find near-duplicate names; returns indices to keep."""
        if not candidates:
            return []
        embeddings = await self.embed_texts(candidates)
        if not embeddings or len(embeddings) != len(candidates):
            return list(range(len(candidates)))
        keep: List[int] = []
        for i, emb in enumerate(embeddings):
            dup = False
            for j in keep:
                sim = cosine_similarity(emb, embeddings[j])
                if sim > 0.95:
                    dup = True
                    break
            if not dup:
                keep.append(i)
        return keep


def cosine_similarity(a: List[float], b: List[float]) -> float:
    import math
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


nim_engine = NIMEngine()
