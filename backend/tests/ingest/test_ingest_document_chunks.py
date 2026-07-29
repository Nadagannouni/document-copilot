from __future__ import annotations

import json
from argparse import Namespace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ingest import chunking, embeddings, manifests
from ingest import ingest_document_chunks as ingest
from ingest.models import FilingInput, PreparedChunk, SourceDocumentRef


def write_json(path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def manifest_entry(accession_number: str = "0000320193-25-000079") -> dict:
    return {
        "ticker": "AAPL",
        "form": "10-K",
        "filing_date": "2025-10-31",
        "report_date": "2025-09-27",
        "accession_number": accession_number,
        "source_url": "https://example.com/aapl.htm",
        "local_path": "2025/aapl.htm",
    }


def markdown_entry(accession_number: str = "0000320193-25-000079") -> dict:
    return {
        "accession_number": accession_number,
        "local_path": "2025/aapl.md",
    }


def test_load_filing_inputs_joins_downloads_and_markdown_manifest(tmp_path) -> None:
    downloads_dir = tmp_path / "downloads"
    markdown_dir = tmp_path / "markdown"
    (downloads_dir / "2025").mkdir(parents=True)
    (markdown_dir / "2025").mkdir(parents=True)
    (downloads_dir / "2025" / "aapl.htm").write_text("<html></html>", encoding="utf-8")
    (markdown_dir / "2025" / "aapl.md").write_text("# AAPL", encoding="utf-8")
    write_json(downloads_dir / "manifest.json", {"filings": [manifest_entry()]})
    write_json(markdown_dir / "manifest.json", {"filings": [markdown_entry()]})

    filings = manifests.load_filing_inputs(downloads_dir, markdown_dir)

    assert len(filings) == 1
    assert filings[0].accession_number == "0000320193-25-000079"
    assert filings[0].fiscal_year == 2025
    assert filings[0].html_path == downloads_dir.resolve() / "2025" / "aapl.htm"
    assert filings[0].markdown_path == markdown_dir.resolve() / "2025" / "aapl.md"


def test_load_filing_inputs_requires_markdown_manifest_entry(tmp_path) -> None:
    downloads_dir = tmp_path / "downloads"
    markdown_dir = tmp_path / "markdown"
    (downloads_dir / "2025").mkdir(parents=True)
    markdown_dir.mkdir()
    (downloads_dir / "2025" / "aapl.htm").write_text("<html></html>", encoding="utf-8")
    write_json(downloads_dir / "manifest.json", {"filings": [manifest_entry()]})
    write_json(markdown_dir / "manifest.json", {"filings": []})

    with pytest.raises(ValueError, match="Missing Markdown manifest entry"):
        manifests.load_filing_inputs(downloads_dir, markdown_dir)


def test_select_filings_filters_and_limits() -> None:
    filings = [
        SimpleNamespace(accession_number="a"),
        SimpleNamespace(accession_number="b"),
        SimpleNamespace(accession_number="c"),
    ]

    assert manifests.select_filings(filings, accession_number="b", limit_documents=None) == [
        filings[1]
    ]
    assert manifests.select_filings(filings, accession_number=None, limit_documents=2) == [
        filings[0],
        filings[1],
    ]


def test_prepare_chunks_uses_docling_markdown_and_stable_indexes(monkeypatch, tmp_path) -> None:
    source_document_id = uuid4()
    filing = FilingInput(
        ticker="AAPL",
        fiscal_year=2025,
        accession_number="0000320193-25-000079",
        filing_type="10-K",
        filing_date="2025-10-31",
        report_date="2025-09-27",
        source_url="https://example.com/aapl.htm",
        html_path=tmp_path / "aapl.htm",
        markdown_path=tmp_path / "aapl.md",
        html_local_path="2025/aapl.htm",
        markdown_local_path="2025/aapl.md",
    )
    monkeypatch.setattr(chunking, "parse_docling_document", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        chunking,
        "export_docling_markdown",
        lambda document: "# Item 7\n\nRevenue increased.\n\nMargins expanded.",
    )

    prepared = chunking.prepare_chunks(
        filing,
        SourceDocumentRef(source_document_id, filing.accession_number),
        count_tokens=lambda text: len(text.split()),
        max_chunk_tokens=10,
        strip_inline_xbrl_hidden_data=True,
    )

    assert [chunk.chunk_index for chunk in prepared] == [0]
    assert prepared[0].content == "# Item 7\n\nRevenue increased.\n\nMargins expanded."
    assert prepared[0].metadata["headings"] == ["Item 7"]
    assert prepared[0].metadata["chunker"] == "docling-html-to-markdown"


def test_prepare_chunks_rejects_oversized_chunk(monkeypatch, tmp_path) -> None:
    filing = FilingInput(
        ticker="AAPL",
        fiscal_year=2025,
        accession_number="0000320193-25-000079",
        filing_type="10-K",
        filing_date="2025-10-31",
        report_date="2025-09-27",
        source_url="https://example.com/aapl.htm",
        html_path=tmp_path / "aapl.htm",
        markdown_path=tmp_path / "aapl.md",
        html_local_path="2025/aapl.htm",
        markdown_local_path="2025/aapl.md",
    )
    monkeypatch.setattr(chunking, "parse_docling_document", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        chunking,
        "export_docling_markdown",
        lambda document: "too many tokens",
    )

    with pytest.raises(ValueError, match="above limit"):
        chunking.prepare_chunks(
            filing,
            SourceDocumentRef(uuid4(), filing.accession_number),
            count_tokens=lambda text: 3,
            max_chunk_tokens=2,
            strip_inline_xbrl_hidden_data=True,
        )


def test_split_markdown_chunks_preserves_heading_context() -> None:
    chunks = chunking.split_markdown_chunks(
        "# Item 1\n\nBusiness overview.\n\n## Cloud\n\nRevenue table:\n\n| A | B |\n| - | - |\n| 1 | 2 |",
        count_tokens=lambda text: len(text.split()),
        max_chunk_tokens=20,
    )

    assert chunks[0].headings == ["Item 1"]
    assert all(chunk.headings == ["Item 1", "Cloud"] for chunk in chunks[1:])
    assert "| A | B |" in chunks[-1].content


def test_split_markdown_chunks_splits_oversized_tables_with_repeated_header() -> None:
    chunks = chunking.split_markdown_chunks(
        "# Item 8\n\n| Year | Revenue |\n| --- | --- |\n| 2023 | 100 |\n| 2024 | 200 |\n| 2025 | 300 |",
        count_tokens=lambda text: len(text.split()),
        max_chunk_tokens=18,
    )
    table_chunks = [chunk for chunk in chunks if "| Year | Revenue |" in chunk.content]

    assert len(table_chunks) == 3
    assert all("| --- | --- |" in chunk.content for chunk in table_chunks)
    assert all(chunk.headings == ["Item 8"] for chunk in table_chunks)
    assert all(len(chunk.content.split()) <= 18 for chunk in table_chunks)


def test_clean_sec_inline_xbrl_html_removes_internal_anchor_attributes() -> None:
    html = (
        '<a id="i719388195b384d85a4e238ad88eba90a_85" '
        'href="#i719388195b384d85a4e238ad88eba90a_85">Item 7</a>'
        '<ix:nonFraction contextRef="abc" unitRef="usd">100</ix:nonFraction>'
    )

    cleaned = chunking.clean_sec_inline_xbrl_html(html, strip_hidden_data=False)

    assert "i719388195b384d85a4e238ad88eba90a_85" not in cleaned
    assert "contextRef" not in cleaned
    assert "unitRef" not in cleaned
    assert "Item 7" in cleaned
    assert "100" in cleaned


def test_clean_chunk_content_removes_leaked_html_artifacts() -> None:
    content = "Revenue #i719388195b384d85a4e238ad88eba90a_85 <span>grew</span>"

    assert chunking.clean_chunk_content(content) == "Revenue  grew"


def test_embed_chunks_preserves_response_order(monkeypatch) -> None:
    monkeypatch.setattr(embeddings.settings, "openai_embedding_dimensions", 2)
    chunks = [
        PreparedChunk(uuid4(), 0, "first", 1, {}),
        PreparedChunk(uuid4(), 1, "second", 1, {}),
    ]

    class FakeEmbeddings:
        def create(self, **kwargs):
            assert kwargs["input"] == ["first", "second"]
            return SimpleNamespace(
                data=[
                    SimpleNamespace(index=1, embedding=[0.3, 0.4]),
                    SimpleNamespace(index=0, embedding=[0.1, 0.2]),
                ]
            )

    client = SimpleNamespace(embeddings=FakeEmbeddings())

    assert embeddings.embed_chunks(client, chunks, batch_size=2) == [
        [0.1, 0.2],
        [0.3, 0.4],
    ]


def test_embed_chunks_rejects_dimension_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(embeddings.settings, "openai_embedding_dimensions", 2)
    chunks = [PreparedChunk(uuid4(), 0, "first", 1, {})]
    client = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(
                data=[SimpleNamespace(index=0, embedding=[0.1])]
            )
        )
    )

    with pytest.raises(ValueError, match="dimension mismatch"):
        embeddings.embed_chunks(client, chunks, batch_size=1)


def test_create_embedding_client_uses_openai_key_first(monkeypatch) -> None:
    created = {}

    def fake_openai(**kwargs):
        created["openai"] = kwargs
        return "openai-client"

    def fake_azure(**kwargs):
        created["azure"] = kwargs
        return "azure-client"

    monkeypatch.setattr(embeddings.settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(embeddings.settings, "azure_openai_api_key", "azure-test")
    monkeypatch.setattr(embeddings, "OpenAI", fake_openai)
    monkeypatch.setattr(embeddings, "AzureOpenAI", fake_azure)

    assert embeddings.create_embedding_client() == "openai-client"
    assert created == {"openai": {"api_key": "sk-test"}}


def test_create_embedding_client_falls_back_to_azure(monkeypatch) -> None:
    created = {}

    def fake_openai(**kwargs):
        created["openai"] = kwargs
        return "openai-client"

    def fake_azure(**kwargs):
        created["azure"] = kwargs
        return "azure-client"

    monkeypatch.setattr(embeddings.settings, "openai_api_key", " ")
    monkeypatch.setattr(embeddings.settings, "azure_openai_api_key", "azure-test")
    monkeypatch.setattr(embeddings.settings, "azure_openai_endpoint", "https://example.openai.azure.com")
    monkeypatch.setattr(embeddings.settings, "azure_openai_api_version", "2024-10-21")
    monkeypatch.setattr(embeddings, "OpenAI", fake_openai)
    monkeypatch.setattr(embeddings, "AzureOpenAI", fake_azure)

    assert embeddings.create_embedding_client() == "azure-client"
    assert created == {
        "azure": {
            "api_key": "azure-test",
            "azure_endpoint": "https://example.openai.azure.com",
            "api_version": "2024-10-21",
        }
    }


def test_dry_run_does_not_embed_or_write(monkeypatch) -> None:
    filing = SimpleNamespace(ticker="AAPL", fiscal_year=2025, accession_number="a")
    source_document = SourceDocumentRef(uuid4(), "a")
    prepared = [PreparedChunk(source_document.id, 0, "content", 1, {})]
    monkeypatch.setattr(ingest, "load_filing_inputs", lambda *args: [filing])
    monkeypatch.setattr(ingest, "select_filings", lambda filings, **kwargs: filings)
    monkeypatch.setattr(ingest, "fetch_source_documents", lambda accessions: {"a": source_document})
    monkeypatch.setattr(ingest, "prepare_chunks", lambda *args, **kwargs: prepared)
    monkeypatch.setattr(
        ingest,
        "embed_chunks",
        lambda *args, **kwargs: pytest.fail("dry run should not embed"),
    )
    monkeypatch.setattr(
        ingest,
        "upsert_chunks",
        lambda *args, **kwargs: pytest.fail("dry run should not write"),
    )

    result = ingest.ingest_document_chunks(
        Namespace(
            downloads_dir="downloads",
            markdown_dir="markdown",
            accession_number=None,
            limit_documents=None,
            dry_run=True,
            no_embed=False,
            batch_size=32,
            max_chunk_tokens=1200,
            keep_inline_xbrl_hidden_data=False,
        )
    )

    assert result == {
        "documents": 1,
        "documents_written": 0,
        "chunks": 1,
        "tokens": 1,
    }
