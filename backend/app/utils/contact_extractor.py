import re
from typing import List, Optional, Set
from urllib.parse import unquote


EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
PHONE_RE = re.compile(
    r"(?<![\d])(?:"
    # US: +1 (555) 123-4567 or (555) 123-4567
    r"(?:\+?1[\s.\-]?)?\(\d{2,5}\)[\s.\-]?\d{3,4}[\s.\-]?\d{4}"
    r"|"
    # US: 555-123-4567 / 555.123.4567 / 555 123 4567
    r"(?:\+?1[\s.\-]?)?\d{3}[\s.\-]?\d{3}[\s.\-]?\d{4}"
    r"|"
    # International: +91 98765 43210, +44 20 7946 0958, +61 2 1234 5678
    r"(?:\+\d{1,3}[\s.\-]?)\d{2,5}[\s.\-]?\d{3,5}[\s.\-]?\d{3,5}"
    r")(?![\d])",
)
OBFUSCATED_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+\s?\[?at\]?\s?[a-zA-Z0-9.\-]+\s?\[?dot\]?\s?[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Domains we should never treat as a lead's contact email
BANNED_EMAIL_DOMAINS = {
    "example.com", "example.org", "example.net", "sentry.io", "wixpress.com",
    "squarespace.com", "godaddy.com", "domain.com", "gmail.com" if False else "localhost",
    "jpg", "png", "gif", "svg", "webp", "css", "js", "mozilla.org", "schema.org",
    "w3.org", "apache.org", "jquery.com", "googleapis.com", "cloudflare.com",
}


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return raw.strip()
    # International prefix handling
    if len(digits) == 11 and digits.startswith("1"):
        return "+1" + digits[1:]
    if len(digits) == 12 and digits.startswith("1"):
        return "+" + digits
    if len(digits) == 13 and digits.startswith("91"):
        return "+" + digits
    if len(digits) == 10:
        return raw.strip()
    if len(digits) > 13:
        # Could be multiple concatenated numbers; take first 10 meaningful
        return raw.strip()
    if raw.strip().startswith("+"):
        return raw.strip()
    return raw.strip()


def is_valid_email(email: str) -> bool:
    email = email.strip().rstrip(".,;:)").lower()
    if not EMAIL_RE.fullmatch(email):
        return False
    domain = email.split("@")[-1]
    if domain in BANNED_EMAIL_DOMAINS:
        return False
    if len(domain) < 4 or "." not in domain:
        return False
    local = email.split("@")[0]
    # Reject edge cases from obfuscated/partial scraping
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if " " in email:
        return False
    # Reject obvious placeholder / tracking emails
    for junk in ("no-reply", "noreply", "donotreply", "do-not-reply", "unsubscribe", "mailer", "bounce"):
        if email.startswith(junk) or junk in email:
            return False
    return True


def is_valid_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return 7 <= len(digits) <= 15


def extract_emails(text: str) -> List[str]:
    if not text:
        return []
    text = unquote(text)
    found: Set[str] = set()
    for m in EMAIL_RE.finditer(text):
        email = m.group(0).strip().rstrip(".,;:)]}>\"'")
        if is_valid_email(email):
            found.add(email)
    return sorted(found)


def extract_phones(text: str) -> List[str]:
    if not text:
        return []
    found: Set[str] = set()
    for m in PHONE_RE.finditer(text):
        phone = m.group(0).strip()
        if is_valid_phone(phone):
            found.add(normalize_phone(phone))
    return sorted(found)


def extract_contacts_from_text(text: str) -> dict:
    return {
        "emails": extract_emails(text),
        "phones": extract_phones(text),
    }


def deobfuscate(text: str) -> str:
    """Recover 'name at domain dot com' style obfuscated emails."""
    if not text:
        return text
    result = re.sub(r"\s*\[?dot\]?\s*", ".", text, flags=re.IGNORECASE)
    result = re.sub(r"\s*\[?at\]?\s*", "@", result, flags=re.IGNORECASE)
    return result


if __name__ == "__main__":
    sample = (
        "Contact john.doe@example.com or call +1 (555) 123-4567, "
        "also info [at] company dot com and 555-987-6543."
    )
    print(extract_emails(sample))
    print(extract_phones(sample))
