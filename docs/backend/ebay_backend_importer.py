import argparse
import csv
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SEARCH_TERMS = [
    "Hermes Kelly 28",
    "Hermes Birkin 30",
    "Hermes Constance 18",
    "Hermes Lindy 26",
    "Chanel Classic Flap Medium",
]

PUBLIC_PROBE_URLS = [
    "https://www.ebay.com.hk/sch/i.html?_nkw=Hermes+Kelly+28",
    "https://www.ebay.com.hk/sch/i.html?_nkw=Hermes+Birkin+30",
    "https://www.ebay.com/sch/i.html?_nkw=Hermes+Kelly+28&LH_Sold=1&LH_Complete=1",
    "https://www.ebay.com/sch/i.html?_nkw=Hermes+Kelly+28&_rss=1",
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


def risk_flag(row: dict[str, Any]) -> str:
    text = " ".join(str(row.get(key, "")) for key in ("title", "condition", "notes")).lower()
    if any(term in text for term in ("replica", "mirror", "copy", "no receipt", "缺收據")):
        return "high"
    if any(term in text for term in ("authenticated", "entrupy", "receipt", "full set", "pre-owned")):
        return "medium"
    return "review"


def from_csv(path: Path) -> list[Candidate]:
    now = datetime.now(timezone.utc).isoformat()
    rows: list[Candidate] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            listing_url = row.get("listing_url", "").strip()
            rows.append(
                Candidate(
                    source=row.get("source", "eBay").strip() or "eBay",
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
    return rows


def public_probe() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for url in PUBLIC_PROBE_URLS:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=25) as response:
                html = response.read().decode("utf-8", errors="replace")
                results.append(
                    {
                        "url": url,
                        "ok": True,
                        "status": response.status,
                        "length": len(html),
                        "has_items": "s-item" in html,
                        "has_price": "s-item__price" in html or "HK$" in html,
                    }
                )
        except HTTPError as exc:
            results.append({"url": url, "ok": False, "status": exc.code, "reason": "blocked_or_unavailable"})
        except URLError as exc:
            results.append({"url": url, "ok": False, "status": None, "reason": str(exc.reason)})
    return results


def browse_api_search(token: str, query: str, marketplace: str, limit: int) -> dict[str, Any]:
    params = {
        "q": query,
        "limit": str(limit),
        "fieldgroups": "EXTENDED",
    }
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search?" + urlencode(params)
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": marketplace,
            "Accept": "application/json",
            "User-Agent": "Codex luxury bag backend importer",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def api_candidates(token: str, marketplace: str, limit: int) -> list[Candidate]:
    now = datetime.now(timezone.utc).isoformat()
    rows: list[Candidate] = []
    for query in SEARCH_TERMS:
        data = browse_api_search(token, query, marketplace, limit)
        for item in data.get("itemSummaries", []):
            price = item.get("price", {})
            amount = price.get("value")
            currency = price.get("currency", "")
            title = item.get("title", "")
            web_url = item.get("itemWebUrl", "")
            location = item.get("itemLocation", {})
            location_text = ", ".join(part for part in [location.get("city"), location.get("country")] if part)
            rows.append(
                Candidate(
                    source="eBay Browse API",
                    query=query,
                    title=title,
                    price_hkd=parse_hkd(amount) if currency == "HKD" else None,
                    listing_url=web_url,
                    seller_contact_url=web_url,
                    location=location_text,
                    condition=item.get("condition", ""),
                    notes=f"currency={currency}; raw_price={amount}; item_id={item.get('itemId', '')}",
                    snapshot_time=now,
                    risk_flag=risk_flag(item),
                    publish_status="needs_approval",
                )
            )
    return rows


def write_json(path: Path, rows: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import eBay luxury bag candidates into backend JSON.")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/ebay_candidates.json"))
    parser.add_argument("--probe-public", action="store_true")
    parser.add_argument("--api", action="store_true", help="Use official eBay Browse API. Requires EBAY_OAUTH_TOKEN.")
    parser.add_argument("--marketplace", default=os.getenv("EBAY_MARKETPLACE", "EBAY_US"))
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.probe_public:
        print(json.dumps(public_probe(), ensure_ascii=False, indent=2))
        return

    if args.api:
        token = os.getenv("EBAY_OAUTH_TOKEN", "").strip()
        if not token:
            print(json.dumps({"ok": False, "reason": "missing_token", "required_env": "EBAY_OAUTH_TOKEN"}, indent=2))
            return
        rows = api_candidates(token, args.marketplace, args.limit)
        write_json(args.out, rows)
        print(f"Imported {len(rows)} eBay API candidates to {args.out}")
        return

    if not args.csv:
        raise SystemExit("Provide --csv outputs/ebay_import_template.csv, --api, or --probe-public.")

    rows = from_csv(args.csv)
    write_json(args.out, rows)
    print(f"Imported {len(rows)} candidates to {args.out}")


if __name__ == "__main__":
    main()
