from __future__ import annotations

import re
from collections import OrderedDict


def _match_key(value: str | None) -> str:
    if value is None:
        return ""
    clean = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", clean)


def make_duplicate_key(record: dict) -> tuple[str, str, str, str]:
    source = record.get("source", "")
    name = _match_key(record.get("name_or_title"))
    author = _match_key(record.get("author"))
    category = _match_key(record.get("category"))
    if not source and not name:
        return ("", "", "", "")
    return (source, name, author, category)


def deduplicate_records(records: list[dict]) -> tuple[list[dict], int]:
    unique_by_key: OrderedDict[tuple[str, str, str, str], dict] = OrderedDict()
    duplicates = 0

    for record in records:
        key = make_duplicate_key(record)
        if key in unique_by_key:
            duplicates += 1
            continue
        unique_by_key[key] = record

    return list(unique_by_key.values()), duplicates
