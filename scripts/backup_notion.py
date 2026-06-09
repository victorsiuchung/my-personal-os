#!/usr/bin/env python3
"""Back up a Notion database to a timestamped JSON file."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def normalize_notion_id(value: str) -> str:
    raw_id = value.strip().split("?")[0].rstrip("/").split("/")[-1]
    if "-" in raw_id and len(raw_id.split("-")[-1]) == 32:
        return raw_id.split("-")[-1]
    return raw_id.replace("-", "")


def notion_request(api_key: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{NOTION_API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print(f"Notion API error {error.code}: {body}", file=sys.stderr)
        sys.exit(1)


def query_all_pages(api_key: str, database_id: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        payload: dict[str, Any] = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor

        data = notion_request(api_key, "POST", f"/databases/{database_id}/query", payload)
        pages.extend(data.get("results", []))

        if not data.get("has_more"):
            return pages
        cursor = data.get("next_cursor")


def main() -> None:
    api_key = required_env("NOTION_SECRET")
    database_id = normalize_notion_id(required_env("NOTION_DATABASE"))

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    database = notion_request(api_key, "GET", f"/databases/{database_id}")
    pages = query_all_pages(api_key, database_id)

    backup = {
        "backup_created_at": created_at,
        "database_id": database_id,
        "database": database,
        "pages": pages,
    }

    output_dir = Path("backups/notion")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"notion-database-{created_at}.json"
    output_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")

    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"backup_path={output_path.as_posix()}\n")

    print(f"Backed up {len(pages)} Notion pages to {output_path}")


if __name__ == "__main__":
    main()