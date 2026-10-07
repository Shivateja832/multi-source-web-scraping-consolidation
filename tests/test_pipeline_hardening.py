from __future__ import annotations

import csv
import json
import math
from types import SimpleNamespace

import pytest

import healthcheck
import main
from processing.cleaning import normalize_url, to_price
from processing.validation import validate_record
from scrapers import books_scraper, quotes_scraper


def _valid_record(source: str, source_url: str, title: str) -> dict:
    return {
        "source": source,
        "source_url": source_url,
        "name_or_title": title,
        "price": None,
        "rating": None,
        "scraped_at": "2026-10-06T00:00:00+00:00",
    }


@pytest.mark.parametrize("invalid_number", [float("nan"), float("inf"), True])
def test_validation_rejects_non_finite_and_boolean_prices(invalid_number):
    record = _valid_record(
        "Books to Scrape",
        "https://books.toscrape.com/catalogue/book/index.html",
        "A book",
    )
    record["price"] = invalid_number

    valid, errors = validate_record(record)

    assert not valid
    assert "Price must be numeric and non-negative" in errors


def test_validation_rejects_wrong_source_host_and_invalid_timestamp():
    record = _valid_record("Books to Scrape", "https://quotes.toscrape.com/", "A book")
    record["scraped_at"] = "not-a-timestamp"

    valid, errors = validate_record(record)

    assert not valid
    assert "Invalid or missing source_url" in errors
    assert "Missing or invalid scraped_at" in errors


def test_validation_rejects_unknown_source():
    record = _valid_record("Unknown", "https://books.toscrape.com/", "A record")

    valid, errors = validate_record(record)

    assert not valid
    assert "Unrecognized or missing source" in errors


def test_url_normalization_uses_the_record_source():
    assert normalize_url("/catalogue/book/index.html", "Books to Scrape") == (
        "https://books.toscrape.com/catalogue/book/index.html"
    )
    assert normalize_url("/author/alice/", "Quotes to Scrape") == (
        "https://quotes.toscrape.com/author/alice/"
    )


def test_to_price_rejects_non_finite_and_boolean_values():
    assert to_price(float("nan")) is None
    assert to_price(float("inf")) is None
    assert to_price(True) is None
    assert to_price("-£12.50") is None


def test_books_pagination_resolves_listing_relative_urls(monkeypatch):
    base_url = "https://books.example.test/"
    page_two = "https://books.example.test/catalogue/page-2.html"
    book_one = "https://books.example.test/catalogue/book-one/index.html"
    book_two = "https://books.example.test/catalogue/book-two/index.html"
    pages = {
        base_url: (
            '<article class="product_pod"><h3><a href="catalogue/book-one/index.html">'
            'Book</a></h3></article><li class="next"><a href="catalogue/page-2.html">'
            "next</a></li>"
        ),
        page_two: (
            '<article class="product_pod"><h3><a href="book-two/index.html">'
            'Book</a></h3></article>'
        ),
        book_one: "<h1>Book one</h1>",
        book_two: "<h1>Book two</h1>",
    }
    requested: list[str] = []

    def fake_fetch(url: str):
        requested.append(url)
        return SimpleNamespace(text=pages[url])

    monkeypatch.setattr(books_scraper, "BASE_URL", base_url)
    monkeypatch.setattr(books_scraper, "fetch_with_retry", fake_fetch)

    records = books_scraper.scrape_books()

    assert [record["name_or_title"] for record in records] == ["Book one", "Book two"]
    assert book_one in requested
    assert book_two in requested


def test_quote_scraper_fetches_each_author_profile_once(monkeypatch):
    listing_url = quotes_scraper.BASE_URL
    author_url = "https://quotes.toscrape.com/author/alice/"
    listing_html = """
    <div class="quote">
      <span class="text">First quote</span><small class="author">Alice</small>
      <a href="/author/alice/">about</a>
    </div>
    <div class="quote">
      <span class="text">Second quote</span><small class="author">Alice</small>
      <a href="/author/alice/">about</a>
    </div>
    """
    profile_html = '<div class="author-description">Alice profile.</div>'
    requested: list[str] = []

    def fake_fetch(url: str):
        requested.append(url)
        return SimpleNamespace(text=listing_html if url == listing_url else profile_html)

    monkeypatch.setattr(quotes_scraper, "fetch_with_retry", fake_fetch)

    records = quotes_scraper.scrape_quotes(limit_pages=1)

    assert len(records) == 2
    assert records[0]["description"] == records[1]["description"] == "Alice profile."
    assert records[0]["description"] != records[0]["name_or_title"]
    assert requested.count(author_url) == 1


def test_pipeline_smoke_writes_validated_outputs(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"
    books = [
        _valid_record(
            "Books to Scrape",
            "https://books.toscrape.com/catalogue/book/index.html",
            "A book",
        )
    ]
    quotes = [
        _valid_record(
            "Quotes to Scrape",
            "https://quotes.toscrape.com/author/alice/",
            "A quote",
        )
    ]
    monkeypatch.setattr(main, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(main, "LOG_DIR", log_dir)
    monkeypatch.setattr(main, "configure_logging", lambda: None)
    monkeypatch.setattr(main, "reset_request_failures", lambda: None)
    monkeypatch.setattr(main, "get_request_failures", lambda: 0)
    def fake_books(**kwargs):
        assert kwargs == {"limit_pages": None}
        return books

    def fake_quotes(**kwargs):
        assert kwargs == {"limit_pages": None}
        return quotes

    monkeypatch.setattr(main, "scrape_books", fake_books)
    monkeypatch.setattr(main, "scrape_quotes", fake_quotes)
    monkeypatch.setattr(healthcheck, "OUTPUT_DIR", output_dir)

    summary = main.run_pipeline()

    assert summary["status"] == "success"
    assert summary["final_record_count"] == 2
    with (output_dir / "final_dataset.csv").open(encoding="utf-8", newline="") as file:
        assert len(list(csv.DictReader(file))) == 2
    saved_summary = json.loads((output_dir / "summary_report.json").read_text(encoding="utf-8"))
    assert saved_summary["status"] == "success"
    assert math.isfinite(saved_summary["execution_time_seconds"])


def test_pipeline_fails_quality_status_when_source_returns_no_records(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda: None)
    monkeypatch.setattr(main, "reset_request_failures", lambda: None)
    monkeypatch.setattr(main, "get_request_failures", lambda: 0)
    def fake_books(**kwargs):
        assert kwargs == {"limit_pages": None}
        return [
            _valid_record(
                "Books to Scrape",
                "https://books.toscrape.com/catalogue/book/index.html",
                "A book",
            )
        ]

    def fake_quotes(**kwargs):
        assert kwargs == {"limit_pages": None}
        return []

    monkeypatch.setattr(main, "scrape_books", fake_books)
    monkeypatch.setattr(main, "scrape_quotes", fake_quotes)

    summary = main.run_pipeline()

    assert summary["status"] == "partial_failure"
    assert summary["sources_without_records"] == ["Quotes to Scrape"]
