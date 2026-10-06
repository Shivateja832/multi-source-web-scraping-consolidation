from __future__ import annotations

import logging
import time

import requests

from config import (
    DEFAULT_HEADERS,
    MAX_RETRIES,
    RATE_LIMIT_DELAY_SECONDS,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
REQUEST_FAILURE_COUNT = 0


def reset_request_failures() -> None:
    global REQUEST_FAILURE_COUNT
    REQUEST_FAILURE_COUNT = 0


def get_request_failures() -> int:
    return REQUEST_FAILURE_COUNT


def _backoff_seconds(attempt: int, response: requests.Response | None = None) -> float:
    delay = RATE_LIMIT_DELAY_SECONDS * (2 ** (attempt - 1))
    if response is not None:
        try:
            retry_after = float(response.headers.get("Retry-After", "0"))
        except ValueError:
            retry_after = 0
        delay = max(delay, retry_after)
    return delay


def fetch_with_retry(url: str) -> requests.Response:
    global REQUEST_FAILURE_COUNT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=DEFAULT_HEADERS)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                REQUEST_FAILURE_COUNT += 1
                raise
            delay = _backoff_seconds(attempt)
            logger.info(
                "Temporary network issue (%s); retry %s/%s in %.2fs: %s",
                exc,
                attempt + 1,
                MAX_RETRIES,
                delay,
                url,
            )
            time.sleep(delay)
            continue

        if response.status_code in RETRYABLE_STATUS_CODES:
            if attempt == MAX_RETRIES:
                REQUEST_FAILURE_COUNT += 1
                response.raise_for_status()
            delay = _backoff_seconds(attempt, response)
            logger.info(
                "Temporary HTTP %s response; retry %s/%s in %.2fs: %s",
                response.status_code,
                attempt + 1,
                MAX_RETRIES,
                delay,
                url,
            )
            time.sleep(delay)
            continue

        try:
            response.raise_for_status()
        except requests.HTTPError:
            REQUEST_FAILURE_COUNT += 1
            raise
        time.sleep(RATE_LIMIT_DELAY_SECONDS)
        return response

    raise requests.RequestException(f"Unable to fetch {url}")
