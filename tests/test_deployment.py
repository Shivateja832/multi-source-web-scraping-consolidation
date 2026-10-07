import csv
import json
import logging

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

    def fake_get(url, **kwargs):
        assert kwargs["timeout"] > 0
        assert kwargs["headers"]
        calls.append(url)
        return responses.pop(0)

    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", delays.append)
    monkeypatch.setattr(http, "RATE_LIMIT_DELAY_SECONDS", 1)

    result = http.fetch_with_retry("https://example.test")

    assert result.status_code == 200
    assert len(calls) == 3
    assert delays == [1, 2, 1]


def test_fetch_with_retry_logs_transient_network_issue_as_info(monkeypatch, caplog):
    outcomes = [requests.ConnectionError("connection reset"), _http_response(200)]
    delays = []

    def fake_get(url, **kwargs):
        assert url == "https://example.test"
        assert kwargs["timeout"] > 0
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", delays.append)
    monkeypatch.setattr(http, "RATE_LIMIT_DELAY_SECONDS", 0)
    http.reset_request_failures()

    with caplog.at_level(logging.INFO, logger=http.__name__):
        response = http.fetch_with_retry("https://example.test")

    assert response.status_code == 200
    assert delays == [0, 0]
    assert "Temporary network issue (connection reset); retry 2/3" in caplog.text
    assert "Request failed" not in caplog.text
    assert http.get_request_failures() == 0


def test_fetch_with_retry_does_not_retry_permanent_http_error(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        assert kwargs["timeout"] > 0
        calls.append(url)
        return _http_response(404)

    monkeypatch.setattr(
        http.requests,
        "get",
        fake_get,
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
            "execution_time_seconds": 1.0,
            "request_failures": 0,
            "final_record_count": 1,
            "records_rejected_during_validation": 0,
            "duplicate_records_detected": 0,
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
