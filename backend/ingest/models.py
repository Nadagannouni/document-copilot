from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class FilingInput:
    ticker: str
    fiscal_year: int
    accession_number: str
    filing_type: str
    filing_date: str
    report_date: str | None
    source_url: str
    html_path: Path
    markdown_path: Path
    html_local_path: str
    markdown_local_path: str


@dataclass(frozen=True)
class SourceDocumentRef:
    id: UUID
    accession_number: str


@dataclass(frozen=True)
class PreparedChunk:
    source_document_id: UUID
    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any]
