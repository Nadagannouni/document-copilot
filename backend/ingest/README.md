# Ingestion Notes

This folder contains one-off ingestion utilities for preparing SEC filings for retrieval.

## Current Default

The active pipeline is:

1. Read filing metadata from `data/downloads/manifest.json` and `data/markdown/manifest.json`.
2. Parse the local SEC `.htm` filing into a Docling document.
3. Export that Docling document back to Markdown.
4. Split the exported Markdown into heading-aware chunks.
5. Embed those chunks and upsert them into `document_chunks`.

This keeps the HTM file as the structural source while embedding cleaner Markdown text,
especially for tables.

## Why This Changed

The first ingestion attempt used Docling's `HybridChunker` directly on the HTM-derived
Docling document. That preserved Docling hierarchy, but SEC inline-XBRL HTML leaked
internal anchors and code-like fragments such as `#i719...` into chunks, and table text
was not as clean as the Markdown export.

The older implementation is preserved in `old_chunking.py` as a reference for that path.
The active implementation lives in `chunking.py`.

## Oversized Tables

While testing NVIDIA 2025 (`0001045810-25-000023`), ingestion failed with:

```text
ValueError: 0001045810-25-000023 chunk 2 has 1515 tokens, above limit 1200.
```

The cause was one large Markdown table exported from Docling. We do not want to split
tables like normal prose because that can separate headers from rows and lose context.
The fix in `chunking.py` detects oversized Markdown tables and splits them into smaller
Markdown tables with the original header and separator repeated in each chunk. If a
single table row is still too large, ingestion fails clearly.

## Commands

Dry-run one filing without embeddings or DB writes:

```powershell
uv run --project backend backend/ingest/ingest_document_chunks.py --accession-number 0000320193-25-000079 --dry-run --no-embed
```

Embed and upsert one filing:

```powershell
uv run --project backend backend/ingest/ingest_document_chunks.py --accession-number 0000320193-25-000079
```

Embed and upsert all filings:

```powershell
uv run --project backend backend/ingest/ingest_document_chunks.py
```
