from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import tiktoken

from app.config import settings
from ingest.models import FilingInput, PreparedChunk, SourceDocumentRef


def prepare_chunks(
    filing: FilingInput,
    source_document: SourceDocumentRef,
    *,
    count_tokens: Callable[[str], int],
    max_chunk_tokens: int,
    strip_inline_xbrl_hidden_data: bool,
) -> list[PreparedChunk]:
    if max_chunk_tokens < 1:
        raise ValueError("--max-chunk-tokens must be greater than 0")

    chunker = create_hybrid_chunker(max_chunk_tokens)
    document = parse_docling_document(
        filing.html_path,
        strip_inline_xbrl_hidden_data=strip_inline_xbrl_hidden_data,
    )

    prepared = []
    for chunk in chunker.chunk(dl_doc=document):
        content = clean_chunk_content(chunker.contextualize(chunk=chunk)).strip()
        if not content:
            continue

        token_count = count_tokens(content)
        if token_count > max_chunk_tokens:
            raise ValueError(
                f"{filing.accession_number} chunk {len(prepared)} has "
                f"{token_count} tokens, above limit {max_chunk_tokens}."
            )

        prepared.append(
            PreparedChunk(
                source_document_id=source_document.id,
                chunk_index=len(prepared),
                content=content,
                token_count=token_count,
                metadata=chunk_metadata(filing, chunk),
            )
        )

    if not prepared:
        raise ValueError(f"Docling produced no chunks for {filing.accession_number}")
    return prepared


def create_hybrid_chunker(max_chunk_tokens: int):
    from docling.chunking import HybridChunker
    from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

    encoding = tiktoken.encoding_for_model(settings.openai_embedding_model)
    tokenizer = OpenAITokenizer(tokenizer=encoding, max_tokens=max_chunk_tokens)
    return HybridChunker(
        tokenizer=tokenizer,
        merge_peers=True,
        repeat_table_header=True,
        omit_header_on_overflow=True,
    )


def parse_docling_document(
    html_path: Path,
    *,
    strip_inline_xbrl_hidden_data: bool,
):
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter

    html = html_path.read_text(encoding="utf-8", errors="replace")
    html = clean_sec_inline_xbrl_html(
        html,
        strip_hidden_data=strip_inline_xbrl_hidden_data,
    )
    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
    return converter.convert_string(
        html,
        format=InputFormat.HTML,
        name=html_path.name,
    ).document


def clean_sec_inline_xbrl_html(html: str, *, strip_hidden_data: bool) -> str:
    if strip_hidden_data:
        html = re.sub(
            r"<ix:header\b.*?</ix:header>",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        html = re.sub(
            r"<div\b[^>]*display\s*:\s*none[^>]*>\s*</div>",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

    html = re.sub(r'\s(?:id|href)=["\']#?i[a-z0-9_:-]+["\']', "", html, flags=re.IGNORECASE)
    html = re.sub(r'\s(?:contextRef|unitRef)=["\'][^"\']*["\']', "", html, flags=re.IGNORECASE)
    return html


def clean_chunk_content(content: str) -> str:
    content = re.sub(r"#i[a-z0-9_:-]+", "", content, flags=re.IGNORECASE)
    return re.sub(r"<[^>\n]{1,200}>", "", content)


def chunk_metadata(filing: FilingInput, chunk: object) -> dict[str, Any]:
    metadata = getattr(chunk, "meta", None)
    headings = [
        clean_chunk_content(str(item)).strip()
        for item in getattr(metadata, "headings", None) or []
    ]
    captions = [
        clean_chunk_content(str(item)).strip()
        for item in getattr(metadata, "captions", None) or []
    ]
    return {
        "ticker": filing.ticker,
        "fiscal_year": filing.fiscal_year,
        "accession_number": filing.accession_number,
        "filing_type": filing.filing_type,
        "filing_date": filing.filing_date,
        "report_date": filing.report_date,
        "source_url": filing.source_url,
        "html_local_path": filing.html_local_path,
        "markdown_local_path": filing.markdown_local_path,
        "headings": headings,
        "captions": captions,
        "chunker": "docling-hybrid",
        "embedding_model": settings.openai_embedding_model,
        "embedding_dimensions": settings.openai_embedding_dimensions,
    }
