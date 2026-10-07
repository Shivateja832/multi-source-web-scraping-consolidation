from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from config import (
    DEFAULT_PAGE_LIMIT,
    LOG_DIR,
    MAX_RETRIES,
    OUTPUT_DIR,
    RATE_LIMIT_DELAY_SECONDS,
    REQUEST_TIMEOUT,
)
from processing.cleaning import normalize_record
from processing.deduplication import deduplicate_records
from processing.validation import validate_record
from scrapers.books_scraper import scrape_books
from scrapers.http import get_request_failures, reset_request_failures
from scrapers.quotes_scraper import scrape_quotes

ROOT_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


def _positive_page_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("page limit must be a positive integer") from exc
    if limit < 1:
        raise argparse.ArgumentTypeError("page limit must be a positive integer")
    return limit


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_DIR / "pipeline.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    logging.getLogger().addHandler(logging.StreamHandler())


def write_csv(path: Path, records: list[dict]) -> None:
    fieldnames = [
        "source",
        "source_url",
        "name_or_title",
        "category",
        "price",
        "rating",
        "author",
        "tags",
        "description",
        "scraped_at",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {field: record.get(field, "") for field in fieldnames}
            writer.writerow(row)


def run_pipeline(limit_pages: int | None = None, dry_run: bool = False) -> dict:
    if dry_run:
        from healthcheck import validate_directories

        validate_directories()
        summary = {
            "status": "dry_run",
            "output_dir": str(OUTPUT_DIR),
            "log_dir": str(LOG_DIR),
            "request_timeout_seconds": REQUEST_TIMEOUT,
            "rate_limit_delay_seconds": RATE_LIMIT_DELAY_SECONDS,
            "default_page_limit": DEFAULT_PAGE_LIMIT,
        }
        print(json.dumps(summary, indent=2))
        return summary

    start = time.perf_counter()
    configure_logging()
    reset_request_failures()
    logger.info("Starting data collection pipeline")
    logger.info(
        "Config: timeout=%s retries=%s rate_limit=%s",
        REQUEST_TIMEOUT,
        MAX_RETRIES,
        RATE_LIMIT_DELAY_SECONDS,
    )

    source_a_raw = scrape_books(limit_pages=limit_pages)
    source_b_raw = scrape_quotes(limit_pages=limit_pages)

    all_raw = source_a_raw + source_b_raw
    cleaned_records = [normalize_record(record) for record in all_raw]

    valid_records = []
    rejected_records = []
    for record in cleaned_records:
        is_valid, errors = validate_record(record)
        if is_valid:
            valid_records.append(record)
        else:
            rejected_records.append({"record": record, "errors": errors})

    final_records, duplicate_count = deduplicate_records(valid_records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "final_dataset.csv", final_records)

    request_failures = get_request_failures()
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "success" if request_failures == 0 else "partial_failure",
        "execution_time_seconds": round(time.perf_counter() - start, 3),
        "request_failures": request_failures,
        "sites": {
            "Books to Scrape": {
                "records_collected": len(source_a_raw),
                "records_after_cleaning": sum(1 for record in cleaned_records if record.get("source") == "Books to Scrape"),
                "records_rejected_during_validation": sum(1 for item in rejected_records if item["record"].get("source") == "Books to Scrape"),
            },
            "Quotes to Scrape": {
                "records_collected": len(source_b_raw),
                "records_after_cleaning": sum(1 for record in cleaned_records if record.get("source") == "Quotes to Scrape"),
                "records_rejected_during_validation": sum(1 for item in rejected_records if item["record"].get("source") == "Quotes to Scrape"),
            },
        },
        "sources_without_records": [
            source
            for source, records in (
                ("Books to Scrape", source_a_raw),
                ("Quotes to Scrape", source_b_raw),
            )
            if not records
        ],
        "total_records_collected": len(all_raw),
        "total_records_after_cleaning": len(cleaned_records),
        "records_rejected_during_validation": len(rejected_records),
        "duplicate_records_detected": duplicate_count,
        "final_record_count": len(final_records),
    }
    if request_failures or summary["sources_without_records"] or not final_records:
        summary["status"] = "partial_failure"

    with (OUTPUT_DIR / "summary_report.json").open("w", encoding="utf-8") as outfile:
        json.dump(summary, outfile, indent=2)

    logger.info("Pipeline complete. Final records: %s", len(final_records))
    if summary["status"] == "success":
        from healthcheck import validate_outputs

        validate_outputs()
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the multi-source scraper pipeline.")
    parser.add_argument(
        "--limit-pages",
        type=_positive_page_limit,
        default=DEFAULT_PAGE_LIMIT,
        help="Optional page cap per source; omit to follow pagination to the final page.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate the app configuration and output directories without scraping.")
    parser.add_argument("--health-check", action="store_true", help="Alias for dry-run validation.")
    args = parser.parse_args()
    result = run_pipeline(limit_pages=args.limit_pages, dry_run=args.dry_run or args.health_check)
    if result.get("status") == "partial_failure":
        raise SystemExit(
            "Pipeline completed with request or data-quality failures; see the summary report and log."
        )
