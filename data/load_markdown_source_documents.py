from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


DATA_DIR = Path(__file__).resolve().parent
REPO_DIR = DATA_DIR.parent
BACKEND_DIR = REPO_DIR / "backend"
DEFAULT_MARKDOWN_DIR = DATA_DIR / "markdown"

sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database.models.source_document import SourceDocument  # noqa: E402


TICKER_COMPANIES = {
    "AAPL": "Apple Inc.",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load converted Markdown filings into source_documents."
    )
    parser.add_argument(
        "--markdown-dir",
        type=Path,
        default=DEFAULT_MARKDOWN_DIR,
        help=f"Directory containing Markdown files and manifest.json. Default: {DEFAULT_MARKDOWN_DIR}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the manifest and print what would be loaded without writing.",
    )
    return parser.parse_args()


def load_source_documents(markdown_dir: Path, *, dry_run: bool) -> dict[str, int]:
    markdown_dir = markdown_dir.resolve()
    manifest = read_manifest(markdown_dir)
    filings = manifest.get("filings", [])
    if not filings:
        raise ValueError(f"No filings found in {markdown_dir / 'manifest.json'}")

    rows = [build_source_document_row(markdown_dir, manifest, filing) for filing in filings]
    if dry_run:
        for row in rows:
            print(
                f"Would load {row['ticker']} {row['fiscal_year']} "
                f"{row['accession_number']}"
            )
        return {"loaded": 0, "validated": len(rows)}

    engine = create_engine(database_url())
    with Session(engine) as session:
        existing_accessions = set(
            session.scalars(
                select(SourceDocument.accession_number).where(
                    SourceDocument.accession_number.in_(
                        row["accession_number"] for row in rows
                    )
                )
            )
        )

        for row in rows:
            statement = insert(SourceDocument).values(row)
            update_values = {
                column.name: statement.excluded[column.name]
                for column in SourceDocument.__table__.columns
                if column.name not in {"id", "created_at"}
            }
            update_values["updated_at"] = func.now()
            session.execute(
                statement.on_conflict_do_update(
                    constraint="uq_source_documents_accession_number",
                    set_=update_values,
                )
            )
        session.commit()

    inserted = sum(1 for row in rows if row["accession_number"] not in existing_accessions)
    return {"loaded": len(rows), "inserted": inserted, "updated": len(rows) - inserted}


def read_manifest(markdown_dir: Path) -> dict[str, Any]:
    manifest_path = markdown_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def build_source_document_row(
    markdown_dir: Path,
    manifest: dict[str, Any],
    filing: dict[str, Any],
) -> dict[str, Any]:
    local_path = Path(filing["local_path"])
    markdown_path = markdown_dir / local_path
    if not markdown_path.exists():
        raise FileNotFoundError(f"Missing Markdown file: {markdown_path}")

    ticker = filing["ticker"]
    report_date = filing.get("report_date") or filing["filing_date"]
    return {
        "company": TICKER_COMPANIES.get(ticker, ticker),
        "ticker": ticker,
        "filing_type": filing["form"],
        "filing_date": date.fromisoformat(filing["filing_date"]),
        "fiscal_year": int(report_date[:4]),
        "accession_number": filing["accession_number"],
        "source_url": filing["source_url"],
        "content_markdown": markdown_path.read_text(encoding="utf-8"),
        "metadata_json": {
            "primary_document": filing.get("primary_document"),
            "report_date": filing.get("report_date"),
            "source_local_path": filing.get("source_local_path"),
            "markdown_local_path": filing["local_path"],
            "markdown_manifest_generated_at_utc": manifest.get("generated_at_utc"),
            "converter": manifest.get("converter"),
        },
    }


def database_url() -> str:
    url = make_url(str(settings.database_url))
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url.render_as_string(hide_password=False)


if __name__ == "__main__":
    args = parse_args()
    result = load_source_documents(args.markdown_dir, dry_run=args.dry_run)
    if args.dry_run:
        print(f"Validated {result['validated']} source document(s).")
    else:
        print(
            f"Loaded {result['loaded']} source document(s): "
            f"{result['inserted']} inserted, {result['updated']} updated."
        )
