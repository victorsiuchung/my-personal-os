import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROBE_URLS = [
    "https://www.milanstation.com.hk/",
    "https://www.milanstation.com.hk/search?q=Hermes",
    "https://www.milanstation.com.hk/?s=Hermes",
    "https://www.milanstation.com.hk/wp-json/",
    "https://www.milanstation.com.hk/wp-json/wc/store/products?search=Hermes",
    "https://www.milanstation.com.hk/sitemap.xml",
    "https://www.milanstation.com.hk/product-sitemap.xml",
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
    if any(term in notes for term in ("quotation", "店舖", "shop", "full set", "receipt")):
        return "medium"
    if any(term in notes for term in ("no receipt", "缺收據", "unknown")):
        return "high"
    return "review"


def from_csv(path: Path) -> list[Candidate]:
    now = datetime.now(timezone.utc).isoformat()
    rows: list[Candidate] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            listing_url = row.get("listing_url", "").strip()
            rows.append(
                Candidate(
                    source=row.get("source", "Milan Station").strip() or "Milan Station",
                    query=row.get("query", "").strip(),
                    title=row.get("title", "").strip(),
                    price_hkd=parse_hkd(row.get("price_hkd")),
                    listing_url=listing_url,
                    seller_contact_url=row.get("seller_contact_url", "").strip() or listing_url,
                    location=row.get("location", "Hong Kong").strip() or "Hong Kong",
                    condition=row.get("condition", "").strip(),
                    notes=row.get("notes", "").strip(),
                    snapshot_time=now,
                    risk_flag=risk_flag(row),
                    publish_status="needs_approval",
                )
            )
    return rows


def fetch_probe(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=20) as response:
            content = response.read().decode("utf-8", errors="replace")
            return {
                "url": url,
                "ok": True,
                "status": response.status,
                "content_type": response.headers.get("Content-Type", ""),
                "length": len(content),
                "has_hermes": "Hermes" in content or "Hermès" in content,
                "has_price": "HK$" in content or "HKD" in content,
            }
    except HTTPError as exc:
        return {"url": url, "ok": False, "status": exc.code, "reason": "server_error_or_blocked"}
    except URLError as exc:
        return {"url": url, "ok": False, "status": None, "reason": str(exc.reason)}


def write_json(path: Path, rows: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Milan Station candidates into backend JSON.")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/milanstation_candidates.json"))
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps([fetch_probe(url) for url in PROBE_URLS], ensure_ascii=False, indent=2))
        return

    if not args.csv:
        raise SystemExit("Provide --csv outputs/milanstation_import_template.csv or run --probe.")

    candidates = from_csv(args.csv)
    write_json(args.out, candidates)
    print(f"Imported {len(candidates)} candidates to {args.out}")


if __name__ == "__main__":
    main()
