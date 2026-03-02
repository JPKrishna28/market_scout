import re
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup
from dateutil import parser
from llm.nvidia_client import invoke_llm

DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b",
]


def from_meta(soup: BeautifulSoup) -> Optional[datetime]:
    for meta in soup.find_all("meta"):
        if meta.get("content"):
            try:
                return parser.parse(meta["content"])
            except Exception:
                pass
    return None


def from_text(text: str) -> Optional[datetime]:
    for p in DATE_PATTERNS:
        m = re.search(p, text)
        if m:
            try:
                return parser.parse(m.group())
            except Exception:
                pass
    return None


def llm_fallback(text: str) -> Optional[str]:
    prompt = f"""
Extract publish date from text.
Return YYYY-MM-DD or null.

{text[:1200]}
"""
    resp = invoke_llm([{"role": "user", "content": prompt}], temperature=0)
    return resp if resp != "null" else None