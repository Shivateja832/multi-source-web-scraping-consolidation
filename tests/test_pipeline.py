from processing.cleaning import normalize_rating, normalize_whitespace
from processing.deduplication import deduplicate_records
from processing.validation import validate_record


def test_normalize_rating_handles_text():
    assert normalize_rating("Three") == 3.0
    assert normalize_rating("4.5") == 4.5


def test_validate_record_rejects_invalid_values():
    record = {
        "source": "Books to Scrape",
        "source_url": "not-a-url",
        "name_or_title": "A book title",
        "price": -10,
        "rating": 6,
        "scraped_at": "2026-10-06T00:00:00+00:00",
    }
    is_valid, errors = validate_record(record)
    assert is_valid is False
    assert any("Invalid or missing source_url" in message for message in errors)
    assert any("Price must be numeric and non-negative" in message for message in errors)
    assert any("Rating must be between 0 and 5" in message for message in errors)


def test_deduplicate_records_flags_equivalent_entries():
    records = [
        {"source": "Quotes to Scrape", "name_or_title": "Life is short", "author": "A. Author", "category": ""},
        {"source": "Quotes to Scrape", "name_or_title": "  life is short  ", "author": "A. Author", "category": ""},
    ]
    deduped, duplicate_count = deduplicate_records(records)
    assert duplicate_count == 1
    assert len(deduped) == 1


def test_normalize_whitespace_removes_excess_spaces():
    assert normalize_whitespace("  Hello   world  ") == "Hello world"
