"""
email_sender.py — Async SMTP email sending with CAN-SPAM compliance.

Features:
  - aiosmtplib for non-blocking sends
  - HTML body with CAN-SPAM footer (physical address + unsubscribe link)
  - Hard bounce detection: SMTP 5xx → return bounce=True for suppression
  - Transient failures (network, auth) → return bounce=False (retryable)
  - Per-credential daily limit via SendLogRecord (single source of truth)
"""
import logging
import datetime
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("spresy.email_sender")

# SMTP reply codes that indicate permanent failure (hard bounce → suppress)
HARD_BOUNCE_CODES = {
    500, 501, 503, 521, 550, 551, 552, 553, 554, 555,
}


@dataclass
class SmtpConfig:
    host: str
    port: int
    email: str
    password: str          # plaintext (decrypted before passing here)
    sender_name: str = ""
    use_tls: bool = True   # STARTTLS on 587; SSL on 465


def _decrypt_password(encrypted: str) -> str:
    from ..config import settings
    if not settings.ENCRYPTION_KEY:
        # No encryption key set — return as-is (dev mode)
        return encrypted
    from cryptography.fernet import Fernet
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted.encode()).decode()


def encrypt_password(plaintext: str) -> str:
    from ..config import settings
    if not settings.ENCRYPTION_KEY:
        return plaintext
    from cryptography.fernet import Fernet
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(plaintext.encode()).decode()


def get_daily_sends(credential_id: str) -> int:
    """Get today's send count for a credential."""
    from ..database import SessionLocal
    from ..db_models import SendLogRecord
    today = datetime.date.today().isoformat()
    db = SessionLocal()
    try:
        rec = db.query(SendLogRecord).filter(
            SendLogRecord.credential_id == credential_id,
            SendLogRecord.date == today,
        ).first()
        return rec.count if rec else 0
    finally:
        db.close()


def increment_daily_sends(credential_id: str) -> int:
    """Atomically increment send count. Returns new count."""
    from ..database import SessionLocal
    from ..db_models import SendLogRecord
    today = datetime.date.today().isoformat()
    db = SessionLocal()
    try:
        rec = db.query(SendLogRecord).filter(
            SendLogRecord.credential_id == credential_id,
            SendLogRecord.date == today,
        ).first()
        if rec:
            rec.count += 1
        else:
            rec = SendLogRecord(credential_id=credential_id, date=today, count=1)
            db.add(rec)
        db.commit()
        return rec.count
    finally:
        db.close()


def _html_body(message: str, physical_address: str, unsubscribe_url: str) -> str:
    """Wrap plain message in minimal HTML with CAN-SPAM footer."""
    escaped = message.replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <div style="line-height: 1.6;">
    {escaped}
  </div>
  <hr style="margin: 32px 0; border: none; border-top: 1px solid #eee;">
  <div style="font-size: 11px; color: #999; line-height: 1.5;">
    <p>You are receiving this email because your business was identified as a potential match.</p>
    <p>
      <a href="{unsubscribe_url}" style="color: #999;">Unsubscribe</a> &nbsp;|&nbsp;
      {physical_address}
    </p>
  </div>
</body>
</html>"""


async def send_email(
    smtp_cfg: SmtpConfig,
    to_email: str,
    subject: str,
    body: str,
    physical_address: str,
    unsubscribe_url: str,
) -> Tuple[bool, bool, str]:
    """
    Send one email.

    Returns:
        (success: bool, is_hard_bounce: bool, error_message: str)

    Caller rules:
        success=True                        → mark sent
        success=False, is_hard_bounce=True  → mark bounced + suppress
        success=False, is_hard_bounce=False → mark failed (retryable)
    """
    import email as email_lib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        import aiosmtplib
    except ImportError:
        logger.error("aiosmtplib not installed")
        return False, False, "aiosmtplib not installed"

    from_name = smtp_cfg.sender_name or smtp_cfg.email
    html = _html_body(body, physical_address, unsubscribe_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{smtp_cfg.email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        if smtp_cfg.port == 465:
            # SSL
            await aiosmtplib.send(
                msg,
                hostname=smtp_cfg.host,
                port=smtp_cfg.port,
                username=smtp_cfg.email,
                password=smtp_cfg.password,
                use_tls=True,
                timeout=30,
            )
        else:
            # STARTTLS (587)
            await aiosmtplib.send(
                msg,
                hostname=smtp_cfg.host,
                port=smtp_cfg.port,
                username=smtp_cfg.email,
                password=smtp_cfg.password,
                start_tls=True,
                timeout=30,
            )
        logger.info("Email sent to %s via %s", to_email, smtp_cfg.host)
        return True, False, ""

    except aiosmtplib.SMTPRecipientsRefused as e:
        # Permanent rejection → hard bounce
        logger.warning("SMTP recipients refused for %s: %s", to_email, e)
        return False, True, str(e)

    except aiosmtplib.SMTPException as e:
        # Check if it's a 5xx (hard bounce) or something else
        error_str = str(e)
        code = getattr(e, "code", 0)
        if code in HARD_BOUNCE_CODES:
            logger.warning("Hard bounce (%s) for %s: %s", code, to_email, e)
            return False, True, error_str
        # Transient (auth failure, timeout, etc.)
        logger.warning("Transient SMTP error for %s: %s", to_email, e)
        return False, False, error_str

    except Exception as e:
        logger.warning("Unexpected send error for %s: %s", to_email, e)
        return False, False, str(e)
