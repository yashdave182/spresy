"""
doc_parser.py — Extract text from uploaded documents for AI context.

Supported formats:
  - PDF    → PyPDF2
  - DOCX   → python-docx
  - Images → Gemini Vision (multimodal)
  - TXT/MD → direct read
"""
import logging
import mimetypes
from pathlib import Path

logger = logging.getLogger("spresy.doc_parser")

MAX_CHARS = 6000  # Max context chars fed to AI


async def extract_text(file_path: str, filename: str) -> str:
    """Extract text from a file. Returns cleaned string, capped at MAX_CHARS."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    mime, _ = mimetypes.guess_type(filename)

    try:
        if suffix == ".pdf":
            return _extract_pdf(path)
        elif suffix in (".docx", ".doc"):
            return _extract_docx(path)
        elif suffix in (".txt", ".md", ".rst", ".text"):
            return _extract_text(path)
        elif mime and mime.startswith("image/"):
            return await _extract_image_gemini(path)
        else:
            # Try plain text fallback
            return _extract_text(path)
    except Exception as e:
        logger.warning("Failed to extract text from %s: %s", filename, e)
        return ""


def _extract_pdf(path: Path) -> str:
    try:
        import PyPDF2
        text_parts = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text.strip())
        return _clean("\n\n".join(text_parts))
    except ImportError:
        logger.warning("PyPDF2 not installed; cannot parse PDF")
        return ""


def _extract_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return _clean("\n".join(paragraphs))
    except ImportError:
        logger.warning("python-docx not installed; cannot parse DOCX")
        return ""


def _extract_text(path: Path) -> str:
    try:
        return _clean(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        logger.warning("Failed to read text file %s: %s", path, e)
        return ""


async def _extract_image_gemini(path: Path) -> str:
    """Use Gemini Vision to OCR an image."""
    try:
        from ..services.gemini_engine import gemini_engine
        from google.genai import types

        if not gemini_engine.available:
            return ""

        image_bytes = path.read_bytes()
        mime_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"

        async def call(client):
            return await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    "Extract all text from this document image. Return the raw text only, no commentary.",
                ],
            )

        resp = await gemini_engine._execute_with_fallback(call)
        return _clean(resp.text if resp and resp.text else "")
    except Exception as e:
        logger.warning("Gemini vision extraction failed: %s", e)
        return ""


def _clean(text: str) -> str:
    """Normalize whitespace and cap length."""
    import re
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()[:MAX_CHARS]
