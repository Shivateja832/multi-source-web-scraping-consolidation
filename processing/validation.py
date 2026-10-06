from __future__ import annotations

from processing.cleaning import is_valid_url


def validate_record(record: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not record.get("source"):
        errors.append("Missing source")
    if not record.get("source_url") or not is_valid_url(record["source_url"]):
        errors.append("Invalid or missing source_url")
    if not record.get("name_or_title"):
        errors.append("Missing name_or_title")

    price = record.get("price")
    if price is not None and (not isinstance(price, (int, float)) or price < 0):
        errors.append("Price must be numeric and non-negative")

    rating = record.get("rating")
    if rating is not None and (not isinstance(rating, (int, float)) or rating < 0 or rating > 5):
        errors.append("Rating must be between 0 and 5")

    if record.get("source") and not record["source"].strip():
        errors.append("Source is blank")

    return len(errors) == 0, errors
