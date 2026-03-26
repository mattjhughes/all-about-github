#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def extract_title(markdown_text: str, readme_path: Path) -> str:
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return readme_path.stem


def markdown_to_html(markdown_text: str) -> str:
    try:
        import markdown  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The 'markdown' package is required. Install dependencies before running."
        ) from exc

    return markdown.markdown(
        markdown_text,
        extensions=[
            "extra",
            "fenced_code",
            "tables",
            "sane_lists",
            "nl2br",
        ],
        output_format="html5",
    )


def build_payload(readme_text: str, readme_path: Path) -> dict[str, str]:
    title = os.getenv("WORKVIVO_PAGE_TITLE", "").strip() or extract_title(
        readme_text, readme_path
    )
    subtitle = os.getenv("WORKVIVO_PAGE_SUBTITLE", "").strip() or "Mirrored from README.md"

    return {
        "title": title,
        "subtitle": subtitle,
        "space_id": os.getenv("WORKVIVO_SPACE_ID", "23244").strip(),
        "html_content": markdown_to_html(readme_text),
    }


def update_page(api_base: str, page_id: str, token: str, organisation_id: str, payload: dict[str, str]) -> None:
    try:
        import requests  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The 'requests' package is required. Install dependencies before running."
        ) from exc

    response = requests.put(
        f"{api_base.rstrip('/')}/pages/{page_id}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Workvivo-Id": organisation_id,
        },
        data=payload,
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Workvivo request failed with status {response.status_code}: {response.text}"
        )

    try:
        body = response.json()
    except ValueError:
        body = {"status": "unknown", "body": response.text}

    print(json.dumps(body, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mirror README.md content into a Workvivo page."
    )
    parser.add_argument(
        "--readme",
        default="README.md",
        help="Path to the Markdown file to mirror.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render the Workvivo payload locally without calling the API.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    readme_path = Path(args.readme)

    if not readme_path.exists():
        raise RuntimeError(f"Markdown source not found: {readme_path}")

    readme_text = readme_path.read_text(encoding="utf-8")
    payload = build_payload(readme_text, readme_path)

    if args.dry_run:
        preview = {
            "page_id": os.getenv("WORKVIVO_PAGE_ID", "76239").strip(),
            "payload": payload,
        }
        print(json.dumps(preview, indent=2))
        return 0

    token = require_env("WORKVIVO")
    organisation_id = require_env("WORKVIVO_ID")
    page_id = os.getenv("WORKVIVO_PAGE_ID", "76239").strip()
    api_base = os.getenv("WORKVIVO_API_BASE", "https://api.workvivo.com/v1").strip()

    update_page(api_base, page_id, token, organisation_id, payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
