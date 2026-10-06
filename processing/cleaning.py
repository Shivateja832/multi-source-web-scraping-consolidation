from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def normalize_whitespace(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", text)


def normalize_url(value: Any) -> str:
    if value is None:
        return ""
    text = normalize_whitespace(value)
    if not text:
        return ""
    if text.startswith("//"):
        text = "https:" + text
    if "http://" in text or "https://" in text:
        return text
    if text.startswith("/"):
        return "https://books.toscrape.com" + text
    return text


def to_price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        value = float(value)
        return value if value >= 0 else None
    text = normalize_whitespace(value)
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    amount = float(match.group(0))
    return amount if amount >= 0 else None


def normalize_rating(value: Any) -> float | None:
    if value is None or value == "":
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
    if 0 <= numeric <= 5:
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
        "source_url": normalize_url(raw_record.get("source_url", "")),
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


def is_valid_url(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
