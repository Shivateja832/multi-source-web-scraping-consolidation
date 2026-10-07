from __future__ import annotations

import math
from datetime import datetime

from processing.cleaning import SOURCE_BASE_URLS, is_valid_url


def validate_record(record: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []

    source = record.get("source")
    known_source = isinstance(source, str) and source in SOURCE_BASE_URLS
    if not known_source:
        errors.append("Unrecognized or missing source")
    source_url = record.get("source_url")
    if not isinstance(source_url, str) or not is_valid_url(
        source_url, source if known_source else None
    ):
        errors.append("Invalid or missing source_url")
    if not record.get("name_or_title"):
        errors.append("Missing name_or_title")

    price = record.get("price")
    if price is not None and (
        isinstance(price, bool)
        or not isinstance(price, (int, float))
        or not math.isfinite(price)
        or price < 0
    ):
        errors.append("Price must be numeric and non-negative")

    rating = record.get("rating")
    if rating is not None and (
        isinstance(rating, bool)
        or not isinstance(rating, (int, float))
        or not math.isfinite(rating)
        or rating < 0
        or rating > 5
    ):
        errors.append("Rating must be between 0 and 5")

    scraped_at = record.get("scraped_at")
    if not isinstance(scraped_at, str):
        errors.append("Missing or invalid scraped_at")
    else:
        try:
            datetime.fromisoformat(scraped_at)
        except ValueError:
            errors.append("Missing or invalid scraped_at")

    return len(errors) == 0, errors
