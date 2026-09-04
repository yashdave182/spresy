"""
email_validator.py — Validate email addresses before wasting a Gemini call or send attempt.

Three checks in order:
  1. Syntax — basic regex
  2. MX record — does the domain have mail servers?
  3. Suppression — is this email on the global suppression list?

Returns a (valid: bool, reason: str) tuple.
"""
import logging
import re
from typing import Tuple

logger = logging.getLogger("spresy.email_validator")

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


def check_syntax(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


async def check_mx(domain: str) -> bool:
    """Return True if the domain has at least one MX record."""
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return len(answers) > 0
    except ImportError:
        logger.debug("dnspython not installed; skipping MX check")
        return True   # assume valid if we can't check
    except Exception:
        return False  # no MX → likely undeliverable


def check_suppression(email: str, user_id: str = "default") -> Tuple[bool, str]:
    """Return (is_suppressed, reason). Queries DB synchronously."""
    try:
        from ..database import SessionLocal
        from ..db_models import SuppressionRecord
        db = SessionLocal()
        try:
            rec = db.query(SuppressionRecord).filter(
                SuppressionRecord.user_id == user_id,
                SuppressionRecord.email == email.lower().strip(),
            ).first()
            if rec:
                return True, rec.reason
            return False, ""
        finally:
            db.close()
    except Exception as e:
        logger.warning("Suppression check failed: %s", e)
        return False, ""


async def validate(email: str, user_id: str = "default") -> Tuple[bool, str]:
    """
    Full validation pipeline.
    Returns (is_valid, reason_if_invalid).
    """
    email = email.strip().lower()

    if not email:
        return False, "no_email"

    if not check_syntax(email):
        return False, "invalid_syntax"

    domain = email.split("@")[1]
    if not await check_mx(domain):
        return False, "no_mx_record"

    suppressed, reason = check_suppression(email, user_id)
    if suppressed:
        return False, f"suppressed:{reason}"

    return True, ""


def add_to_suppression(email: str, reason: str, user_id: str = "default") -> bool:
    """Add an email to the suppression list. Returns True if added, False if already exists."""
    try:
        from ..database import SessionLocal
        from ..db_models import SuppressionRecord
        db = SessionLocal()
        try:
            existing = db.query(SuppressionRecord).filter(
                SuppressionRecord.user_id == user_id,
                SuppressionRecord.email == email.lower().strip(),
            ).first()
            if existing:
                return False
            rec = SuppressionRecord(
                user_id=user_id,
                email=email.lower().strip(),
                reason=reason,
            )
            db.add(rec)
            db.commit()
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error("Failed to add suppression for %s: %s", email, e)
        return False
