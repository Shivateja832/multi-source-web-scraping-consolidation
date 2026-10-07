from __future__ import annotations

import math
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


def _get_page_limit(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    try:
        limit = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer or 0 for unlimited pagination") from exc
    if limit < 0:
        raise ValueError(f"{name} cannot be negative")
    return limit or None


def _get_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    path = Path(value).expanduser() if value else default
    return path if path.is_absolute() else ROOT_DIR / path


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
OUTPUT_DIR = _get_path("OUTPUT_DIR", ROOT_DIR / "output")
LOG_DIR = _get_path("LOG_DIR", ROOT_DIR / "logs")
DEFAULT_PAGE_LIMIT = _get_page_limit("DEFAULT_PAGE_LIMIT")
BOOKS_BASE_URL = _get_url("BOOKS_BASE_URL", "https://books.toscrape.com")
QUOTES_BASE_URL = _get_url("QUOTES_BASE_URL", "https://quotes.toscrape.com")

if REQUEST_TIMEOUT <= 0:
    raise ValueError("REQUEST_TIMEOUT must be greater than zero")
if MAX_RETRIES < 1:
    raise ValueError("MAX_RETRIES must be at least one")
if not math.isfinite(RATE_LIMIT_DELAY_SECONDS) or RATE_LIMIT_DELAY_SECONDS < 0:
    raise ValueError("RATE_LIMIT_DELAY_SECONDS must be finite and cannot be negative")
