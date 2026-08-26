import sys
import os
import traceback

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Must be assigned unconditionally at top level for Vercel's Python runtime static scanner
app = None
_startup_error_body = None

try:
    from app.main import app
except Exception:
    _startup_error_body = traceback.format_exc()

if app is None:
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    app = FastAPI()
    _err = _startup_error_body

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def _error_handler(path: str = ""):
        return PlainTextResponse(f"Startup Error:\n\n{_err}", status_code=500)
