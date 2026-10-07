from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlparse

from config import BOOKS_BASE_URL, LOG_DIR, OUTPUT_DIR, QUOTES_BASE_URL


def validate_outputs() -> dict:
    csv_path = OUTPUT_DIR / "final_dataset.csv"
    summary_path = OUTPUT_DIR / "summary_report.json"
    if not csv_path.is_file() or not summary_path.is_file():
        raise RuntimeError("Expected dataset and summary report are missing")

    with summary_path.open(encoding="utf-8") as file:
        summary = json.load(file)
    with csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        required_fields = {"source", "source_url", "name_or_title", "scraped_at"}
        if not required_fields.issubset(reader.fieldnames or []):
            raise RuntimeError("Dataset is missing required columns")
        rows = list(reader)

    if not rows:
        raise RuntimeError("Dataset contains no records")
    if len(rows) != summary.get("final_record_count"):
        raise RuntimeError("Dataset row count does not match the summary report")
    if summary.get("status") != "success":
        raise RuntimeError("Scrape summary does not report a successful run")
    if summary.get("request_failures", 0):
        raise RuntimeError("Scrape summary reports failed HTTP requests")
    expected_sources = {"Books to Scrape", "Quotes to Scrape"}
    sites = summary.get("sites", {})
    if not expected_sources.issubset(sites):
        raise RuntimeError("Summary report is missing a required source")
    if any(sites[source].get("records_collected", 0) < 1 for source in expected_sources):
        raise RuntimeError("At least one required source produced no records")

    expected_hosts = {
        "Books to Scrape": urlparse(BOOKS_BASE_URL).netloc.casefold(),
        "Quotes to Scrape": urlparse(QUOTES_BASE_URL).netloc.casefold(),
    }
    for row_number, row in enumerate(rows, start=2):
        if row["source"] not in expected_hosts:
            raise RuntimeError(f"Unrecognized source on CSV row {row_number}")
        parsed_url = urlparse(row["source_url"])
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise RuntimeError(f"Invalid source URL on CSV row {row_number}")
        if parsed_url.netloc.casefold() != expected_hosts[row["source"]]:
            raise RuntimeError(f"Source URL host does not match its source on CSV row {row_number}")
        if not row["name_or_title"].strip():
            raise RuntimeError(f"Missing title on CSV row {row_number}")

    return {
        "dataset_rows": len(rows),
        "summary_final_record_count": summary["final_record_count"],
        "dataset": str(csv_path),
        "summary": str(summary_path),
    }


def validate_directories() -> list[str]:
    directories = [OUTPUT_DIR, LOG_DIR]
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise RuntimeError(f"Invalid directory: {path}")
        probe = path / ".healthcheck-write-test"
        try:
            probe.write_text("ok", encoding="utf-8")
        finally:
            probe.unlink(missing_ok=True)
    return [str(path) for path in directories]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check application directories and generated outputs.")
    parser.add_argument("--require-output", action="store_true", help="Validate the latest CSV and JSON output files.")
    args = parser.parse_args()

    directories = validate_directories()
    result = {"status": "healthy", "directories": directories}
    if args.require_output:
        result["outputs"] = validate_outputs()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
