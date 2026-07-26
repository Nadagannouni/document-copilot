from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter


DATA_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = DATA_DIR / "downloads"
DEFAULT_OUTPUT_DIR = DATA_DIR / "markdown"
SUPPORTED_SUFFIXES = {".htm", ".html"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert downloaded HTML filings to Markdown with Docling."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing downloaded HTML files. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory where Markdown files will be written. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Keep existing output files and skip Markdown files that already exist.",
    )
    parser.add_argument(
        "--keep-inline-xbrl-hidden-data",
        action="store_true",
        help="Keep hidden SEC inline-XBRL metadata before converting.",
    )
    return parser.parse_args()


def convert_downloads(
    input_dir: Path,
    output_dir: Path,
    *,
    clear_output_dir: bool,
    strip_inline_xbrl_hidden_data: bool,
) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    manifest = read_manifest(input_dir)
    html_paths = sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )

    if clear_output_dir and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
    converted_paths: dict[str, str] = {}
    failures = []

    for html_path in html_paths:
        relative_html_path = html_path.relative_to(input_dir)
        markdown_path = output_dir / relative_html_path.with_suffix(".md")
        markdown_path.parent.mkdir(parents=True, exist_ok=True)

        if not clear_output_dir and markdown_path.exists():
            converted_paths[str(relative_html_path)] = str(
                markdown_path.relative_to(output_dir)
            )
            print(f"Skipped existing {markdown_path.relative_to(output_dir)}", flush=True)
            continue

        try:
            html = html_path.read_text(encoding="utf-8", errors="replace")
            if strip_inline_xbrl_hidden_data:
                html = strip_sec_inline_xbrl_hidden_data(html)
            result = converter.convert_string(
                html,
                format=InputFormat.HTML,
                name=html_path.name,
            )
            markdown_path.write_text(
                result.document.export_to_markdown().rstrip() + "\n",
                encoding="utf-8",
            )
        except Exception as exc:  # Boundary around third-party parser + file IO.
            failures.append(
                {
                    "source_path": str(relative_html_path),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        converted_paths[str(relative_html_path)] = str(
            markdown_path.relative_to(output_dir)
        )
        print(
            f"Converted {relative_html_path} -> {markdown_path.relative_to(output_dir)}",
            flush=True,
        )

    markdown_manifest = build_markdown_manifest(
        manifest=manifest,
        converted_paths=converted_paths,
        failures=failures,
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(markdown_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return markdown_manifest


def read_manifest(input_dir: Path) -> dict[str, Any]:
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def build_markdown_manifest(
    *,
    manifest: dict[str, Any],
    converted_paths: dict[str, str],
    failures: list[dict[str, str]],
) -> dict[str, Any]:
    markdown_manifest = {
        "source": manifest.get("source", "local HTML downloads"),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_manifest_generated_at_utc": manifest.get("generated_at_utc"),
        "form": manifest.get("form"),
        "format": "markdown",
        "converter": "docling",
        "converted_count": len(converted_paths),
        "failed_count": len(failures),
        "filings": [],
        "failures": failures,
    }

    source_filings = manifest.get("filings", [])
    if source_filings:
        for filing in source_filings:
            source_local_path = filing["local_path"]
            markdown_local_path = converted_paths.get(source_local_path)
            if not markdown_local_path:
                continue

            markdown_filing = dict(filing)
            markdown_filing["source_local_path"] = source_local_path
            markdown_filing["local_path"] = markdown_local_path
            markdown_manifest["filings"].append(markdown_filing)
    else:
        markdown_manifest["files"] = [
            {"source_local_path": source_path, "local_path": markdown_path}
            for source_path, markdown_path in converted_paths.items()
        ]

    return markdown_manifest


def strip_sec_inline_xbrl_hidden_data(html: str) -> str:
    # SEC inline-XBRL filings carry large hidden metadata blocks that are not useful
    # for Markdown retrieval and can make general HTML conversion extremely slow.
    html = re.sub(r"<ix:header\b.*?</ix:header>", "", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(
        r"<div\b[^>]*display\s*:\s*none[^>]*>\s*</div>",
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return html


if __name__ == "__main__":
    args = parse_args()
    result = convert_downloads(
        args.input_dir,
        args.output_dir,
        clear_output_dir=not args.keep_existing,
        strip_inline_xbrl_hidden_data=not args.keep_inline_xbrl_hidden_data,
    )
    print(
        "Converted "
        f"{result['converted_count']} file(s) to {args.output_dir.resolve()} "
        f"with {result['failed_count']} failure(s)."
    )
    print(f"Manifest: {args.output_dir.resolve() / 'manifest.json'}")
