from __future__ import annotations

import argparse
import sys
from pathlib import Path

import tiktoken


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = REPO_DIR / "data"
DEFAULT_DOWNLOADS_DIR = DATA_DIR / "downloads"
DEFAULT_MARKDOWN_DIR = DATA_DIR / "markdown"
DEFAULT_MAX_CHUNK_TOKENS = 1200
DEFAULT_BATCH_SIZE = 32

sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from ingest.chunking import prepare_chunks  # noqa: E402
from ingest.document_chunks import (  # noqa: E402
    cleanup_stale_chunks,
    fetch_source_documents,
    upsert_chunks,
)
from ingest.embeddings import create_embedding_client, embed_chunks  # noqa: E402
from ingest.manifests import load_filing_inputs, select_filings  # noqa: E402
from ingest.models import FilingInput, PreparedChunk  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chunk local SEC HTML filings, embed them, and upsert document_chunks."
    )
    parser.add_argument("--downloads-dir", type=Path, default=DEFAULT_DOWNLOADS_DIR)
    parser.add_argument("--markdown-dir", type=Path, default=DEFAULT_MARKDOWN_DIR)
    parser.add_argument("--accession-number")
    parser.add_argument("--limit-documents", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-embed", action="store_true")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-chunk-tokens", type=int, default=DEFAULT_MAX_CHUNK_TOKENS)
    parser.add_argument(
        "--keep-inline-xbrl-hidden-data",
        action="store_true",
        help="Keep hidden SEC inline-XBRL metadata before Docling conversion.",
    )
    return parser.parse_args()


def ingest_document_chunks(args: argparse.Namespace) -> dict[str, int]:
    filings = select_filings(
        load_filing_inputs(args.downloads_dir, args.markdown_dir),
        accession_number=args.accession_number,
        limit_documents=args.limit_documents,
    )
    if not filings:
        raise ValueError("No filings matched the requested filters.")

    count_tokens = create_token_counter()
    source_documents = fetch_source_documents(
        [filing.accession_number for filing in filings]
    )
    client = None if args.no_embed or args.dry_run else create_embedding_client()

    total_chunks = 0
    total_tokens = 0
    documents_written = 0

    for filing in filings:
        source_document = source_documents.get(filing.accession_number)
        if source_document is None:
            raise ValueError(
                "Missing source_documents row for accession "
                f"{filing.accession_number}. Run data/load_markdown_source_documents.py first."
            )

        chunks = prepare_chunks(
            filing,
            source_document,
            count_tokens=count_tokens,
            max_chunk_tokens=args.max_chunk_tokens,
            strip_inline_xbrl_hidden_data=not args.keep_inline_xbrl_hidden_data,
        )
        total_chunks += len(chunks)
        total_tokens += sum(chunk.token_count for chunk in chunks)
        print_chunk_summary(filing, chunks)

        if args.dry_run:
            continue

        embeddings = None
        if not args.no_embed:
            embeddings = embed_chunks(client, chunks, batch_size=args.batch_size)

        upsert_chunks(chunks, embeddings)
        cleanup_stale_chunks(source_document.id, len(chunks))
        documents_written += 1

    print_result(
        document_count=len(filings),
        documents_written=documents_written,
        chunk_count=total_chunks,
        token_count=total_tokens,
        dry_run=args.dry_run,
        no_embed=args.no_embed,
    )
    return {
        "documents": len(filings),
        "documents_written": documents_written,
        "chunks": total_chunks,
        "tokens": total_tokens,
    }


def create_token_counter():
    encoding = tiktoken.encoding_for_model(settings.openai_embedding_model)

    def count_tokens(text: str) -> int:
        return len(encoding.encode(text))

    return count_tokens


def print_chunk_summary(filing: FilingInput, chunks: list[PreparedChunk]) -> None:
    token_counts = [chunk.token_count for chunk in chunks]
    print(
        f"{filing.ticker} {filing.fiscal_year} {filing.accession_number}: "
        f"{len(chunks)} chunk(s), "
        f"tokens min={min(token_counts)} max={max(token_counts)} "
        f"avg={sum(token_counts) // len(token_counts)}",
        flush=True,
    )


def print_result(
    *,
    document_count: int,
    documents_written: int,
    chunk_count: int,
    token_count: int,
    dry_run: bool,
    no_embed: bool,
) -> None:
    print(
        f"Prepared {chunk_count} chunk(s) across {document_count} document(s); "
        f"{token_count} embedding token(s)."
    )
    if dry_run:
        print("Dry run complete; wrote nothing.")
    elif no_embed:
        print(f"Wrote {documents_written} document(s) with null embeddings.")
    else:
        print(f"Wrote {documents_written} embedded document(s).")


if __name__ == "__main__":
    ingest_document_chunks(parse_args())
