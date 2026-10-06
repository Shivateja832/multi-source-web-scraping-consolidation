# AI Usage

## Tools used
- Claude (Testing and review)

## What the AI was used for
- Designing the project structure and module layout
- Drafting the source-specific scraper logic for both websites
- Improving the normalization and validation code
- Suggesting a practical duplicate-detection strategy
- Setting up scheduled GitHub Actions execution, output validation, and static results publishing
- Reviewing the README and project documentation

## Representative prompts
- "Create a Python scraper for Books to Scrape with pagination and error handling"
- "Design a common data model for both books and quotes and clean the scraped values"
- "Write validation and deduplication logic with clear logging"
- "Explain how to structure a final dataset and summary report"

## Which parts were AI-assisted
- Initial crawler skeletons
- Data cleaning helpers
- Validation rules
- Duplicate-detection method
- Retry/backoff and deployment workflow
- Documentation layout and wording

## Important corrections after review
- The Books to Scrape site needed a browser-like User-Agent to avoid 403 responses.
- The initial pagination URL needed to start from the root listing page rather than `/catalogue/`.
- Some book detail links were missing the `/catalogue/` prefix, so relative URL resolution had to be corrected.
- Rating values recorded as words (for example `Three`) were normalized to numeric values.

## Verification
The final solution was checked by:
- running the full scraper pipeline
- validating the generated dataset and summary files
- executing unit tests for cleaning, validation, deduplication, retries, and deployment output checks
- running Ruff lint checks

## Final note
The AI-generated code was reviewed and adjusted to ensure it met the project requirements and produced reproducible output.
