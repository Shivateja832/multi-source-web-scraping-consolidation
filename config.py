from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def _get_url(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name} must be an absolute HTTP(S) URL")
    return value.rstrip("/") + "/"


DEFAULT_HEADERS = {
    "User-Agent": os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    )
}

REQUEST_TIMEOUT = _get_int("REQUEST_TIMEOUT", 20)
MAX_RETRIES = _get_int("MAX_RETRIES", 3)
RATE_LIMIT_DELAY_SECONDS = _get_float("RATE_LIMIT_DELAY_SECONDS", 0.5)
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(ROOT_DIR / "output")))
LOG_DIR = Path(os.getenv("LOG_DIR", str(ROOT_DIR / "logs")))
DEFAULT_PAGE_LIMIT = _get_int("DEFAULT_PAGE_LIMIT", 3)
BOOKS_BASE_URL = _get_url("BOOKS_BASE_URL", "https://books.toscrape.com")
QUOTES_BASE_URL = _get_url("QUOTES_BASE_URL", "https://quotes.toscrape.com")

if REQUEST_TIMEOUT <= 0:
    raise ValueError("REQUEST_TIMEOUT must be greater than zero")
if MAX_RETRIES < 1:
    raise ValueError("MAX_RETRIES must be at least one")
if RATE_LIMIT_DELAY_SECONDS < 0:
    raise ValueError("RATE_LIMIT_DELAY_SECONDS cannot be negative")
if DEFAULT_PAGE_LIMIT < 1:
    raise ValueError("DEFAULT_PAGE_LIMIT must be at least one")
