from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from ingest.models import FilingInput, PreparedChunk, SourceDocumentRef


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class MarkdownChunk:
    content: str
    headings: list[str]


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

    document = parse_docling_document(
        filing.html_path,
        strip_inline_xbrl_hidden_data=strip_inline_xbrl_hidden_data,
    )
    markdown = export_docling_markdown(document)
    markdown_chunks = split_markdown_chunks(
        markdown,
        count_tokens=count_tokens,
        max_chunk_tokens=max_chunk_tokens,
    )

    prepared = []
    for markdown_chunk in markdown_chunks:
        content = clean_chunk_content(markdown_chunk.content).strip()
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
                metadata=chunk_metadata(filing, markdown_chunk),
            )
        )

    if not prepared:
        raise ValueError(f"Docling produced no Markdown chunks for {filing.accession_number}")
    return prepared


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


def export_docling_markdown(document: object) -> str:
    markdown = document.export_to_markdown()
    if not markdown.strip():
        raise ValueError("Docling exported empty Markdown.")
    return markdown


def split_markdown_chunks(
    markdown: str,
    *,
    count_tokens: Callable[[str], int],
    max_chunk_tokens: int,
) -> list[MarkdownChunk]:
    chunks: list[MarkdownChunk] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []
    current_headings: list[str] = []

    for block in markdown_blocks(markdown):
        heading = parse_heading(block)
        if heading is not None:
            level, text = heading
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(text)

        candidate_lines = [*current_lines, block]
        if current_lines and count_tokens("\n\n".join(candidate_lines)) > max_chunk_tokens:
            flush_chunk(chunks, current_lines, current_headings)
            current_lines = []
            current_headings = list(heading_stack)

        if not current_lines:
            current_headings = list(heading_stack)

        if count_tokens(block) > max_chunk_tokens:
            flush_chunk(chunks, current_lines, current_headings)
            current_lines = []
            current_headings = list(heading_stack)
            if is_markdown_table(block):
                chunks.extend(
                    split_oversized_table(
                        block,
                        headings=current_headings,
                        count_tokens=count_tokens,
                        max_chunk_tokens=max_chunk_tokens,
                    )
                )
            else:
                chunks.extend(
                    split_oversized_block(
                        block,
                        headings=current_headings,
                        count_tokens=count_tokens,
                        max_chunk_tokens=max_chunk_tokens,
                    )
                )
            continue

        current_lines.append(block)

    flush_chunk(chunks, current_lines, current_headings)
    return chunks


def markdown_blocks(markdown: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", markdown) if block.strip()]


def parse_heading(block: str) -> tuple[int, str] | None:
    first_line = block.splitlines()[0]
    match = HEADING_PATTERN.match(first_line)
    if match is None:
        return None
    return len(match.group(1)), clean_chunk_content(match.group(2)).strip()


def is_markdown_table(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    return (
        len(lines) >= 2
        and lines[0].startswith("|")
        and lines[0].endswith("|")
        and re.fullmatch(r"\|[\s:-]+\|(?:[\s:-]+\|)*", lines[1]) is not None
    )


def flush_chunk(
    chunks: list[MarkdownChunk],
    lines: list[str],
    headings: list[str],
) -> None:
    content = "\n\n".join(lines).strip()
    if content:
        chunks.append(MarkdownChunk(content=content, headings=list(headings)))


def split_oversized_block(
    block: str,
    *,
    headings: list[str],
    count_tokens: Callable[[str], int],
    max_chunk_tokens: int,
) -> list[MarkdownChunk]:
    chunks: list[MarkdownChunk] = []
    current_lines: list[str] = []

    for line in block.splitlines():
        candidate = "\n".join([*current_lines, line]).strip()
        if current_lines and count_tokens(candidate) > max_chunk_tokens:
            chunks.append(MarkdownChunk(content="\n".join(current_lines), headings=list(headings)))
            current_lines = []
        current_lines.append(line)

    if current_lines:
        chunks.append(MarkdownChunk(content="\n".join(current_lines), headings=list(headings)))

    return chunks


def split_oversized_table(
    block: str,
    *,
    headings: list[str],
    count_tokens: Callable[[str], int],
    max_chunk_tokens: int,
) -> list[MarkdownChunk]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    header = lines[:2]
    rows = lines[2:]

    if count_tokens("\n".join(header)) > max_chunk_tokens:
        raise ValueError("Markdown table header is above the chunk token limit.")

    chunks: list[MarkdownChunk] = []
    current_rows: list[str] = []

    for row in rows:
        row_table = "\n".join([*header, row])
        if count_tokens(row_table) > max_chunk_tokens:
            raise ValueError("Markdown table row is above the chunk token limit.")

        candidate = "\n".join([*header, *current_rows, row])
        if current_rows and count_tokens(candidate) > max_chunk_tokens:
            chunks.append(
                MarkdownChunk(
                    content="\n".join([*header, *current_rows]),
                    headings=list(headings),
                )
            )
            current_rows = []

        current_rows.append(row)

    chunks.append(
        MarkdownChunk(
            content="\n".join([*header, *current_rows]),
            headings=list(headings),
        )
    )
    return chunks


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


def chunk_metadata(filing: FilingInput, chunk: MarkdownChunk) -> dict[str, Any]:
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
        "headings": chunk.headings,
        "captions": [],
        "chunker": "docling-html-to-markdown",
        "embedding_model": settings.openai_embedding_model,
        "embedding_dimensions": settings.openai_embedding_dimensions,
    }
