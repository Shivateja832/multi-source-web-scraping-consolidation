from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import QUOTES_BASE_URL
from scrapers.http import fetch_with_retry

BASE_URL = QUOTES_BASE_URL
logger = logging.getLogger(__name__)


def _safe_text(tag) -> str:
    if tag is None:
        return ""
    return tag.get_text(" ", strip=True)


def _fetch_author_details(author_url: str) -> dict:
    response = fetch_with_retry(author_url)
    soup = BeautifulSoup(response.text, "html.parser")
    details = {
        "author": _safe_text(soup.select_one("h3.author-title")),
        "born": _safe_text(soup.select_one("span.author-born-date")),
        "location": _safe_text(soup.select_one("span.author-born-location")),
        "description": _safe_text(soup.select_one("div.author-description")),
    }
    return details


def scrape_quotes(limit_pages: int | None = None) -> list[dict]:
    records: list[dict] = []
    author_details_cache: dict[str, dict] = {}
    page_url = BASE_URL
    page_count = 0
    seen_urls = set()

    while page_url and page_url not in seen_urls:
        seen_urls.add(page_url)
        page_count += 1
        if limit_pages is not None and page_count > limit_pages:
            break
        try:
            response = fetch_with_retry(page_url)
        except requests.RequestException as exc:
            logger.warning("Failed to fetch Quotes to Scrape page %s: %s", page_url, exc)
            break
        soup = BeautifulSoup(response.text, "html.parser")
        for quote_block in soup.select("div.quote"):
            quote_text = _safe_text(quote_block.select_one("span.text"))
            author_name = _safe_text(quote_block.select_one("small.author"))
            tags = [tag.get_text(strip=True) for tag in quote_block.select("a.tag")]
            author_link = quote_block.select_one("a[href*='/author/']")
            author_url = ""
            if author_link:
                author_url = urljoin(BASE_URL, author_link["href"])

            author_details = {}
            if author_url:
                if author_url not in author_details_cache:
                    try:
                        author_details_cache[author_url] = _fetch_author_details(author_url)
                    except requests.RequestException as exc:
                        logger.warning("Failed to fetch author details for %s: %s", author_name, exc)
                        author_details_cache[author_url] = {}
                author_details = author_details_cache[author_url]

            source_url = author_url or page_url
            record = {
                "source": "Quotes to Scrape",
                "source_url": source_url,
                "name_or_title": quote_text,
                "category": "",
                "price": None,
                "rating": None,
                "author": author_name,
                "tags": tags,
                "description": author_details.get("description", ""),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            records.append(record)

        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href"):
            page_url = urljoin(BASE_URL, next_link["href"])
        else:
            page_url = None

    return records
