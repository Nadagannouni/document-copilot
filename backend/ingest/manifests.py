from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ingest.models import FilingInput


def load_filing_inputs(downloads_dir: Path, markdown_dir: Path) -> list[FilingInput]:
    downloads_dir = downloads_dir.resolve()
    markdown_dir = markdown_dir.resolve()
    downloads_manifest = read_manifest(downloads_dir / "manifest.json")
    markdown_manifest = read_manifest(markdown_dir / "manifest.json")
    markdown_by_accession = {
        filing["accession_number"]: filing for filing in markdown_manifest.get("filings", [])
    }

    filings = []
    for filing in downloads_manifest.get("filings", []):
        accession_number = filing["accession_number"]
        markdown_filing = markdown_by_accession.get(accession_number)
        if markdown_filing is None:
            raise ValueError(f"Missing Markdown manifest entry for {accession_number}")

        html_local_path = filing["local_path"]
        markdown_local_path = markdown_filing["local_path"]
        html_path = downloads_dir / html_local_path
        markdown_path = markdown_dir / markdown_local_path
        if not html_path.exists():
            raise FileNotFoundError(f"Missing HTML filing: {html_path}")
        if not markdown_path.exists():
            raise FileNotFoundError(f"Missing Markdown filing: {markdown_path}")

        report_date = filing.get("report_date")
        filings.append(
            FilingInput(
                ticker=filing["ticker"],
                fiscal_year=int((report_date or filing["filing_date"])[:4]),
                accession_number=accession_number,
                filing_type=filing["form"],
                filing_date=filing["filing_date"],
                report_date=report_date,
                source_url=filing["source_url"],
                html_path=html_path,
                markdown_path=markdown_path,
                html_local_path=html_local_path,
                markdown_local_path=markdown_local_path,
            )
        )

    return filings


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def select_filings(
    filings: Sequence[FilingInput],
    *,
    accession_number: str | None,
    limit_documents: int | None,
) -> list[FilingInput]:
    selected = [
        filing
        for filing in filings
        if accession_number is None or filing.accession_number == accession_number
    ]
    if limit_documents is not None:
        if limit_documents < 1:
            raise ValueError("--limit-documents must be greater than 0")
        selected = selected[:limit_documents]
    return selected
