import sys
import os
import traceback

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.main import app
except Exception as _startup_error:
    # Surface the real error in the HTTP response body for diagnosis
    _error_body = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def _error_handler(path: str = ""):
        return PlainTextResponse(
            f"Startup Error:\n\n{_error_body}",
            status_code=500,
        )
