# Multi-Source Web Scraping & Data Consolidation

## Overview
This project scrapes public data from Books to Scrape and Quotes to Scrape, cleans and validates the records, removes duplicates, and writes a final consolidated dataset to the `output/` directory.

Live results page: https://shivateja832.github.io/multi-source-web-scraping-consolidation/

## Python version
Python 3.11+

## Setup
1. Clone or download the project.
2. Create and activate a virtual environment if desired.
3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

For tests and lint checks, also install the development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

## How to run
From the project root:

```bash
python main.py
```

By default, the pipeline follows each source's pagination through its final page. Use a cap for a quick test:

```bash
python main.py --limit-pages 2
```

## Production-ready configuration
The app supports environment-based configuration through `.env` values or OS environment variables. Use the sample file:

```bash
copy .env.example .env
```

Supported settings include:
- `REQUEST_TIMEOUT`
- `MAX_RETRIES`
- `RATE_LIMIT_DELAY_SECONDS`
- `DEFAULT_PAGE_LIMIT` (`0` means follow all pages; a positive number caps pages per source)
- `OUTPUT_DIR`
- `LOG_DIR`
- `BOOKS_BASE_URL`
- `QUOTES_BASE_URL`
- `USER_AGENT`

A dry-run health validation is available:

```bash
python main.py --dry-run
python healthcheck.py
```
The dry run creates the configured output/log directories and verifies that both are writable.

To run the test and lint checks locally:

```bash
python -m pytest tests -q
python -m ruff check config.py healthcheck.py main.py publish_site.py processing scrapers tests
```

## Docker and CI
The project includes:
- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/scheduled-scrape.yml`

Docker run:

```bash
docker build -t multi-source-scraper .
docker run --rm multi-source-scraper
```

Or with Docker Compose:

```bash
docker compose up --build
```
The container runs as a non-root user and uses separate named volumes for output and logs. Compose applies memory/CPU limits and a failure restart limit. The scraper is a finite batch job and exits after the run; it is not an always-on API process.

## Free scheduled cloud run and public results
The GitHub Actions workflow runs on pushes to `main`, daily at 06:00 UTC, and can also be started manually from the repository's **Actions** tab. It runs tests, builds the production Docker image, executes the full scraper in a restricted container on a GitHub-hosted Docker-capable runner, validates the output CSV/JSON and source URLs, uploads the summary and logs as a 30-day artifact, and deploys a static public status/results page.

To activate it:
1. Create a GitHub repository and push this project to its default branch (`main` or `master`).
2. In the repository, open **Settings → Actions → General** and allow GitHub Actions.
3. GitHub Pages is configured for this repository to deploy with Actions. For a different repository, open **Settings → Pages**, select **GitHub Actions** as the build and deployment source, and save. Ensure the workflow permission `pages: write` is permitted.
4. Open **Actions → Scheduled scraper and public results → Run workflow** for the first run. The daily schedule then runs automatically.
5. Open **Settings → Pages** or the successful workflow's `github-pages` environment to find the public site URL.
6. In **Settings → Notifications** / your GitHub notification preferences, enable notifications for failed workflow runs. Each failed scrape or publish run will also appear as failed in Actions; inspect its logs and downloadable artifacts.

The public site exposes only aggregate run metrics and summary JSON, not the scraped CSV/text. The full CSV is generated and validated on the Actions runner but is not committed or published, avoiding public redistribution of scraped source text. This is a static publication of the latest validated results, not an always-on application server or API. The Docker container runs as a finite batch job on an ephemeral GitHub-hosted runner; it is not a dedicated, continuously running Docker host. Summary and logs are available as per-run artifacts for 30 days. A failed scrape, output validation, or Pages deployment marks the workflow failed and opens or updates a single GitHub alert issue; the next successful run comments on and closes that issue. Enable repository issue and Actions notifications to receive alerts. Free usage is subject to GitHub's current limits and repository plan.

## Pagination behavior
- Books to Scrape: the scraper starts on the root listing page and follows the `next` link until no more pages are present.
- Quotes to Scrape: the scraper follows the quote listing pagination in the same way.
- The pagination loop follows `next` links until the final page by default. `--limit-pages N` or `DEFAULT_PAGE_LIMIT=N` can cap pages when a shorter run is needed. Failed requests are counted and make the run exit unsuccessfully rather than being reported as a clean success.

## Data model
Each record is normalized to a common schema:

- `source`
- `source_url`
- `name_or_title`
- `category`
- `price`
- `rating`
- `author`
- `tags`
- `description`
- `scraped_at`

Missing fields are stored as empty strings or `None` where appropriate. Numeric values such as price and rating are standardized in a numeric format.

## Cleaning approach
The cleaning layer performs:
- whitespace normalization
- rating conversion from star text such as `Three` to `3.0`
- price conversion from strings such as `£51.77` to numeric values
- URL normalization
- missing-value handling
- lowercasing and punctuation cleanup for duplicate detection

## Validation approach
Before writing the final dataset, each record is checked for:
- required source and title values
- valid-looking source URLs
- numeric and non-negative prices
- ratings within the expected range of 0 to 5
- recognizable source names

Records that fail validation are counted in the summary report instead of being written to the final CSV.

## Deduplication approach
The duplicate strategy uses a normalized key built from:
- source
- title/name
- author
- category

This reduces false positives from simple formatting differences such as whitespace and capitalization without over-aggressively collapsing unrelated records across sources.

## Error handling
The shared HTTP client applies a timeout, exponential backoff, and retries for connection failures and HTTP 429/500/502/503/504 responses. It respects numeric `Retry-After` headers and spaces successful requests. Permanent request failures are logged and counted; the pipeline still processes available pages and the other source, writes a summary, then exits unsuccessfully so scheduled monitoring can alert. Before publication, output validation checks both required sources, their URL hosts, and that the CSV row count matches the summary.

## Output description
The pipeline writes the following outputs to `output/`:
- `final_dataset.csv`: consolidated cleaned records
- `summary_report.json`: counts for collection, cleaning, validation, deduplication, and final totals

Execution logs are written separately to `logs/pipeline.log` (or the configured `LOG_DIR`).

## Assumptions
- The public demo sites remain accessible and do not require special access tokens.
- The scraper is designed for educational and testing use only.
- Some fields are optional depending on the source.

## Known limitations
- The assignment sites are intentionally public and static; no dynamic JavaScript-heavy scraping is required.
- Quote records do not have unique per-item URLs, so the original source URL is the page or author profile URL when available.
- Duplicate detection is conservative and designed for practical quality checks rather than production-scale entity resolution.

## AI usage summary
GitHub Copilot in VS Code assisted with implementation, documentation, tests, and validation. See [AI_USAGE.md](./AI_USAGE.md) for details.
