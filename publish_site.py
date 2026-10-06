from __future__ import annotations

import html
import json
from pathlib import Path

from config import OUTPUT_DIR
from healthcheck import validate_outputs

ROOT_DIR = Path(__file__).resolve().parent
SITE_DIR = ROOT_DIR / "site"


def build_site() -> Path:
    validate_outputs()
    summary_path = OUTPUT_DIR / "summary_report.json"
    with summary_path.open(encoding="utf-8") as file:
        summary = json.load(file)

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "summary_report.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    generated_at = html.escape(str(summary["generated_at"]))
    total = int(summary["final_record_count"])
    failed = int(summary["records_rejected_during_validation"])
    duplicates = int(summary["duplicate_records_detected"])
    duration = float(summary["execution_time_seconds"])
    request_failures = int(summary["request_failures"])
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Scraper results</title>
  <style>
    body {{ font: 16px/1.5 system-ui, sans-serif; max-width: 48rem; margin: 3rem auto; padding: 0 1rem; }}
    a {{ margin-right: 1rem; }}
    .status {{ color: #176b35; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Multi-source scraper results</h1>
  <p class="status">Latest scheduled run completed and passed output validation.</p>
  <p>Generated at: <time>{generated_at}</time></p>
  <p>Records: {total}; validation rejects: {failed}; duplicates removed: {duplicates}</p>
  <p>Request failures: {request_failures}; run duration: {duration:.1f} seconds</p>
  <p><a href="summary_report.json">View summary report</a></p>
</body>
</html>
"""
    (SITE_DIR / "index.html").write_text(page, encoding="utf-8")
    return SITE_DIR


if __name__ == "__main__":
    print(f"Prepared GitHub Pages files in {build_site()}")
