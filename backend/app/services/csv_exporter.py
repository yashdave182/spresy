import csv
import os
import re
from datetime import datetime
from typing import List, Optional

from ..models import Lead

CSV_FIELDS = [
    "name", "website", "email", "phone", "address", "city", "state",
    "country", "category", "description", "source", "ai_score",
    "ai_summary", "rating", "verified", "cin",
]


def _sanitize(value) -> str:
    if value is None:
        return ""
    value = str(value)
    value = re.sub(r"[\r\n]+", " ", value)
    return value


def safe_filename(keyword: str) -> str:
    keyword = re.sub(r"[^\w\s-]", "", keyword).strip().lower()
    keyword = re.sub(r"[\s]+", "_", keyword)[:40]
    return keyword or "leads"


def write_leads_csv(leads: List[Lead], output_dir: str, keyword: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"leads_{safe_filename(keyword)}_{ts}.csv"
    path = os.path.join(output_dir, filename)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for lead in leads:
            row = {field: _sanitize(getattr(lead, field, "")) for field in CSV_FIELDS}
            writer.writerow(row)
    return path
