from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from config import BOOKS_BASE_URL, QUOTES_BASE_URL

SOURCE_BASE_URLS = {
    "Books to Scrape": BOOKS_BASE_URL,
    "Quotes to Scrape": QUOTES_BASE_URL,
}


def normalize_whitespace(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", text)


def normalize_url(value: Any, source: str = "") -> str:
    if value is None:
        return ""
    text = normalize_whitespace(value)
    if not text:
        return ""
    if text.startswith("//"):
        return "https:" + text
    if urlparse(text).scheme:
        return text
    base_url = SOURCE_BASE_URLS.get(source, "")
    return urljoin(base_url, text) if base_url else text


def to_price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        value = float(value)
        return value if math.isfinite(value) and value >= 0 else None
    text = normalize_whitespace(value)
    first_digit = re.search(r"\d", text)
    if first_digit and "-" in text[:first_digit.start()]:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    amount = float(match.group(0))
    return amount if math.isfinite(amount) and amount >= 0 else None


def normalize_rating(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
    else:
        text = normalize_whitespace(value).lower()
        mapping = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
        }
        for word, number in mapping.items():
            if word in text:
                numeric = float(number)
                break
        else:
            match = re.search(r"\d+(?:\.\d+)?", text)
            if not match:
                return None
            numeric = float(match.group(0))
    if math.isfinite(numeric) and 0 <= numeric <= 5:
        return round(numeric, 2)
    return None


def normalize_tags(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        cleaned = [normalize_whitespace(item) for item in value if normalize_whitespace(item)]
        return "; ".join(cleaned)
    return normalize_whitespace(value)


def normalize_record(raw_record: dict) -> dict:
    record = {
        "source": normalize_whitespace(raw_record.get("source", "")),
        "source_url": normalize_url(raw_record.get("source_url", ""), raw_record.get("source", "")),
        "name_or_title": normalize_whitespace(raw_record.get("name_or_title", "")),
        "category": normalize_whitespace(raw_record.get("category", "")),
        "price": to_price(raw_record.get("price")),
        "rating": normalize_rating(raw_record.get("rating")),
        "author": normalize_whitespace(raw_record.get("author", "")),
        "tags": normalize_tags(raw_record.get("tags", "")),
        "description": normalize_whitespace(raw_record.get("description", "")),
        "scraped_at": raw_record.get("scraped_at") or datetime.now(timezone.utc).isoformat(),
    }
    return record


def is_valid_url(value: str, source: str | None = None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return False
    expected_base = SOURCE_BASE_URLS.get(source) if source else None
    return expected_base is None or parsed.hostname.casefold() == urlparse(expected_base).hostname.casefold()
