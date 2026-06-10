import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


CAROUSELL_SEARCHES = [
    "Hermes Kelly 28",
    "Hermes Birkin 30",
    "Hermes Constance 18",
    "Hermes Lindy 26",
    "Chanel Classic Flap Medium",
]


@dataclass
class Candidate:
    source: str
    query: str
    title: str
    price_hkd: int | None
    listing_url: str
    seller_contact_url: str
    location: str
    condition: str
    notes: str
    snapshot_time: str
    risk_flag: str
    publish_status: str


def parse_hkd(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def risk_flag(row: dict) -> str:
    notes = " ".join(str(row.get(key, "")) for key in ("title", "condition", "notes")).lower()
    if any(term in notes for term in ("no receipt", "缺收據", "copy", "replica", "mirror")):
        return "high"
    if any(term in notes for term in ("receipt", "full set", "盒", "塵袋")):
        return "medium"
    return "review"


def from_csv(path: Path) -> list[Candidate]:
    now = datetime.now(timezone.utc).isoformat()
    candidates: list[Candidate] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            listing_url = row.get("listing_url", "").strip()
            candidates.append(
                Candidate(
                    source=row.get("source", "Carousell HK").strip() or "Carousell HK",
                    query=row.get("query", "").strip(),
                    title=row.get("title", "").strip(),
                    price_hkd=parse_hkd(row.get("price_hkd")),
                    listing_url=listing_url,
                    seller_contact_url=row.get("seller_contact_url", "").strip() or listing_url,
                    location=row.get("location", "").strip(),
                    condition=row.get("condition", "").strip(),
                    notes=row.get("notes", "").strip(),
                    snapshot_time=now,
                    risk_flag=risk_flag(row),
                    publish_status="needs_approval",
                )
            )
    return candidates


def try_fetch_search(query: str) -> dict:
    url = f"https://www.carousell.com.hk/search/{query.replace(' ', '%20')}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return {"query": query, "url": url, "ok": False, "status": exc.code, "reason": "blocked_or_unavailable"}
    except URLError as exc:
        return {"query": query, "url": url, "ok": False, "status": None, "reason": str(exc.reason)}

    return {
        "query": query,
        "url": url,
        "ok": True,
        "status": 200,
        "html_length": len(html),
        "has_next_data": "__NEXT_DATA__" in html,
        "has_listing_text": "listing" in html.lower(),
    }


def write_json(path: Path, rows: Iterable[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(row) for row in rows]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Carousell luxury bag candidates into backend JSON.")
    parser.add_argument("--csv", type=Path, help="CSV exported/copied from Carousell research.")
    parser.add_argument("--out", type=Path, default=Path("outputs/carousell_candidates.json"))
    parser.add_argument("--probe", action="store_true", help="Probe public Carousell search pages and report availability.")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps([try_fetch_search(query) for query in CAROUSELL_SEARCHES], ensure_ascii=False, indent=2))
        return

    if not args.csv:
        raise SystemExit("Provide --csv outputs/carousell_import_template.csv or run --probe.")

    candidates = from_csv(args.csv)
    write_json(args.out, candidates)
    print(f"Imported {len(candidates)} candidates to {args.out}")


if __name__ == "__main__":
    main()
