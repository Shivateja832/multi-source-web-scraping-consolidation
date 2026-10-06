from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import BOOKS_BASE_URL
from scrapers.http import fetch_with_retry

BASE_URL = BOOKS_BASE_URL
logger = logging.getLogger(__name__)


def _safe_text(tag) -> str:
    if tag is None:
        return ""
    return tag.get_text(" ", strip=True)


def _parse_rating(rating_element) -> float | None:
    if rating_element is None:
        return None
    classes = rating_element.get("class", [])
    mapping = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
    }
    for name in classes:
        if name.lower() in mapping:
            return mapping[name.lower()]
    return None


def _scrape_book_detail(url: str) -> dict:
    response = fetch_with_retry(url)
    soup = BeautifulSoup(response.text, "html.parser")

    title = _safe_text(soup.select_one("h1"))
    category_items = [link.get_text(strip=True) for link in soup.select("ul.breadcrumb li a")]
    category = category_items[-1] if category_items else ""
    price = _safe_text(soup.select_one("p.price_color"))
    rating = _parse_rating(soup.select_one("p.star-rating"))
    description = ""
    desc_tag = soup.select_one("#product_description + p")
    if desc_tag:
        description = _safe_text(desc_tag)
    author = ""
    if soup.select_one("table.table.table-striped"):
        rows = soup.select("table.table.table-striped tr")
        for row in rows:
            cells = row.select("th, td")
            if len(cells) == 2 and cells[0].get_text(strip=True).lower() == "author":
                author = cells[1].get_text(strip=True)
                break

    return {
        "source": "Books to Scrape",
        "source_url": url,
        "name_or_title": title,
        "category": category,
        "price": price,
        "rating": rating,
        "author": author,
        "tags": "",
        "description": description,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def scrape_books(limit_pages: int | None = None) -> list[dict]:
    records: list[dict] = []
    page_url = BASE_URL
    page_count = 0
    seen_urls = set()

    while page_url and page_url not in seen_urls:
        seen_urls.add(page_url)
        page_count += 1
        if limit_pages and page_count > limit_pages:
            break
        try:
            response = fetch_with_retry(page_url)
        except requests.RequestException as exc:
            logger.warning("Failed to fetch Books to Scrape page %s: %s", page_url, exc)
            break
        soup = BeautifulSoup(response.text, "html.parser")
        product_links = []
        for link in soup.select("article.product_pod h3 a"):
            href = link.get("href")
            if not href:
                continue
            if href.startswith(("catalogue/", "/catalogue/")):
                full_url = urljoin(BASE_URL, href)
            else:
                full_url = urljoin("https://books.toscrape.com/catalogue/", href)
            product_links.append(full_url)

        for product_url in product_links:
            try:
                records.append(_scrape_book_detail(product_url))
            except requests.RequestException as exc:
                logger.warning("Failed to scrape book detail page %s: %s", product_url, exc)

        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href"):
            if page_url.startswith("https://books.toscrape.com/catalogue/"):
                page_url = urljoin("https://books.toscrape.com/catalogue/", next_link["href"])
            else:
                page_url = urljoin(BASE_URL, next_link["href"])
        else:
            page_url = None

    return records
