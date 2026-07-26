# Data

Local data artifacts for development live here.

- `downloads/` holds raw source files fetched from SEC EDGAR, grouped by year.
- `markdown/` holds Docling-converted Markdown files with the same year folders.
- Downloaded payloads are gitignored because the corpus can get large.
- Fetch a sample corpus with `uv run data/download.py`
- Convert downloaded HTML to Markdown with `uv run --project backend data/convert_html_to_markdown.py`
- Resume an interrupted conversion with `uv run --project backend data/convert_html_to_markdown.py --keep-existing`
- Load Markdown filings into `source_documents` with `uv run --project backend data/load_markdown_source_documents.py`
