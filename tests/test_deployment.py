import csv
import json

import pytest
import requests

import healthcheck
import publish_site
from scrapers import http


def _http_response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://example.test"
    response._content = b"ok"
    return response


def test_fetch_with_retry_retries_transient_status(monkeypatch):
    responses = [_http_response(503), _http_response(503), _http_response(200)]
    calls = []
    delays = []
    monkeypatch.setattr(http.requests, "get", lambda *args, **kwargs: calls.append(args[0]) or responses.pop(0))
    monkeypatch.setattr(http.time, "sleep", delays.append)
    monkeypatch.setattr(http, "RATE_LIMIT_DELAY_SECONDS", 1)

    result = http.fetch_with_retry("https://example.test")

    assert result.status_code == 200
    assert len(calls) == 3
    assert delays == [1, 2, 1]


def test_fetch_with_retry_does_not_retry_permanent_http_error(monkeypatch):
    calls = []
    monkeypatch.setattr(
        http.requests,
        "get",
        lambda *args, **kwargs: calls.append(args[0]) or _http_response(404),
    )

    with pytest.raises(requests.HTTPError):
        http.fetch_with_retry("https://example.test")

    assert len(calls) == 1


def test_healthcheck_rejects_dataset_summary_count_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(healthcheck, "OUTPUT_DIR", tmp_path)
    csv_path = tmp_path / "final_dataset.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["source", "source_url", "name_or_title", "scraped_at"])
        writer.writeheader()
        writer.writerow({
            "source": "Books to Scrape",
            "source_url": "https://books.toscrape.com/book/",
            "name_or_title": "Book",
            "scraped_at": "2026-10-06T00:00:00+00:00",
        })
    (tmp_path / "summary_report.json").write_text(
        json.dumps({"final_record_count": 2}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="row count"):
        healthcheck.validate_outputs()


def test_build_site_copies_validated_public_outputs(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    site_dir = tmp_path / "site"
    output_dir.mkdir()
    (output_dir / "final_dataset.csv").write_text(
        "source,source_url,name_or_title,scraped_at\n"
        "Books to Scrape,https://books.toscrape.com/book/,Book,2026-10-06T00:00:00+00:00\n",
        encoding="utf-8",
    )
    (output_dir / "summary_report.json").write_text(
        json.dumps({
            "generated_at": "2026-10-06T00:00:00+00:00",
            "status": "success",
            "final_record_count": 1,
            "records_rejected_during_validation": 0,
            "sites": {
                "Books to Scrape": {"records_collected": 1},
                "Quotes to Scrape": {"records_collected": 1},
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(healthcheck, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(publish_site, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(publish_site, "SITE_DIR", site_dir)

    result = publish_site.build_site()

    assert result == site_dir
    assert (site_dir / "summary_report.json").is_file()
    assert not (site_dir / "final_dataset.csv").exists()
    assert "Latest scheduled run completed" in (site_dir / "index.html").read_text(encoding="utf-8")
