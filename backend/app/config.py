from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Gemini API (Primary)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # Groq Cloud API (Fallback)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # NVIDIA NIM API (OpenAI-compatible)
    NIM_API_KEY: str = ""
    NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NIM_EMBED_MODEL: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
    NIM_CHAT_MODEL: str = "meta/llama-3.3-70b-instruct"

    # Search engines
    SERPAPI_KEY: str = ""  # optional: for Google Maps via SerpAPI

    # ---- Tier 1: Official APIs ----
    GOOGLE_PLACES_API_KEY: str = ""   # Google Places API (Text Search + Details)
    YELP_FUSION_API_KEY: str = ""     # Yelp Fusion API (free tier)
    OPENCORPORATES_API_KEY: str = ""  # OpenCorporates (free tier, some limits)
    HUNTER_API_KEY: str = ""          # Hunter.io domain search (email finder)

    # ---- Tier 1: India company registry ----
    # MCA public search works without a key (limited), or via OpenCorporates IN jurisdiction.

    # ---- Crawler settings ----
    USER_AGENT: str = "SpresyBot/1.0 (+legal lead research; respecting robots.txt)"
    MAX_CONCURRENCY: int = 5
    REQUEST_TIMEOUT: float = 20.0
    DEFAULT_DELAY_SECONDS: float = 1.5
    MAX_PAGES_PER_SITE: int = 8
    MAX_TOTAL_LEADS: int = 250
    RESULTS_PER_SOURCE: int = 20

    # Playwright (optional) for JS-heavy / anti-bot sources like JustDial & Sulekha.
    # Install with: pip install playwright && playwright install chromium
    USE_PLAYWRIGHT: bool = False

    # Storage
    OUTPUT_DIR: str = "output"

    # Deployment
    FRONTEND_URL: str = ""  # e.g. https://spresy.vercel.app — used for CORS
    SERVE_FRONTEND: bool = False  # Set true in Docker to serve built frontend from backend

    # Database Config
    DATABASE_URL: str = ""
    ENV: str = "local"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def groq_api_keys(self) -> list[str]:
        return self._collect_keys("GROQ_API_KEY")

    @property
    def gemini_api_keys(self) -> list[str]:
        return self._collect_keys("GEMINI_API_KEY")

    @property
    def serpapi_keys(self) -> list[str]:
        return self._collect_keys("SERPAPI_KEY")

    def _collect_keys(self, prefix: str) -> list[str]:
        """Collect all API keys matching a prefix: PREFIX, PREFIX1, PREFIX2, ..."""
        import os
        from dotenv import dotenv_values
        env_vars = dotenv_values(self.Config.env_file)
        keys = []
        # The base key (e.g. GROQ_API_KEY)
        base_val = getattr(self, prefix, "") or os.environ.get(prefix, "")
        if base_val:
            keys.append(base_val)
        # Numbered keys (e.g. GROQ_API_KEY1, GROQ_API_KEY2, ...)
        for i in range(1, 100):
            val = env_vars.get(f"{prefix}{i}") or os.environ.get(f"{prefix}{i}")
            if val:
                keys.append(val)
        return list(dict.fromkeys(keys))


settings = Settings()

if settings.ENV == "production" and not settings.DATABASE_URL:
    raise ValueError("CRITICAL: DATABASE_URL is not set but ENV is production. Server cannot start.")
if not settings.DATABASE_URL:
    import os
    if os.environ.get("VERCEL") == "1":
        # Vercel has a read-only filesystem except for /tmp
        db_path = "/tmp/spresy.db"
    else:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spresy.db")
    settings.DATABASE_URL = f"sqlite:///{db_path}"
