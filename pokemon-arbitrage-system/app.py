"""Pokemon card arbitrage backend.

MVP principle:
- Backend finds or stores candidate opportunities.
- Owner must approve before an item appears on storefront.
- Storefront accepts order requests only. It does not claim guaranteed stock.
"""

from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from storage import connect, init_db, rows_to_dicts


app = FastAPI(title="Pokemon Card Arbitrage Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class OpportunityCreate(BaseModel):
    title: str
    card_name: str
    set_name: str = ""
    condition_note: str = ""
    image_url: str = ""
    source_name: str
    source_url: str
    asking_price_hkd: float = Field(ge=0)
    target_resale_hkd: float = Field(ge=0)
    confidence: int = Field(default=60, ge=0, le=100)
    risk_note: str = ""


class OrderCreate(BaseModel):
    opportunity_id: int
    buyer_name: str
    buyer_contact: str
    quantity: int = Field(default=1, ge=1)
    message: str = ""


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed_sources()


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/sources")
def list_sources() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM sources ORDER BY id").fetchall()
    return rows_to_dicts(rows)


@app.post("/api/sources/{source_id}/approve")
def approve_source(source_id: int) -> dict[str, Any]:
    with connect() as conn:
        conn.execute("UPDATE sources SET approved = 1 WHERE id = ?", (source_id,))
        conn.commit()
    return {"ok": True, "source_id": source_id}


@app.get("/api/opportunities")
def list_opportunities(status: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if status:
            rows = conn.execute("SELECT * FROM opportunities WHERE status = ? ORDER BY estimated_profit_hkd DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM opportunities ORDER BY created_at DESC").fetchall()
    return rows_to_dicts(rows)


@app.post("/api/opportunities")
def create_opportunity(payload: OpportunityCreate) -> dict[str, Any]:
    profit = payload.target_resale_hkd - payload.asking_price_hkd
    margin = profit / payload.asking_price_hkd * 100 if payload.asking_price_hkd else 0
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO opportunities (
                title, card_name, set_name, condition_note, image_url, source_name, source_url,
                asking_price_hkd, target_resale_hkd, estimated_profit_hkd,
                estimated_margin_pct, confidence, risk_note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.title,
                payload.card_name,
                payload.set_name,
                payload.condition_note,
                payload.image_url,
                payload.source_name,
                payload.source_url,
                payload.asking_price_hkd,
                payload.target_resale_hkd,
                profit,
                margin,
                payload.confidence,
                payload.risk_note,
            ),
        )
        conn.commit()
    return {"ok": True, "id": cursor.lastrowid, "estimated_profit_hkd": profit, "estimated_margin_pct": round(margin, 2)}


@app.post("/api/opportunities/seed")
def seed_demo_opportunities() -> dict[str, Any]:
    demo = [
        OpportunityCreate(
            title="Charizard VSTAR SAR PSA 10 local deal watch",
            card_name="Charizard VSTAR SAR",
            set_name="VSTAR Universe",
            condition_note="PSA 10 slab. Verify cert and slab condition.",
            image_url="https://images.pokemontcg.io/swsh12pt5/GG56_hires.png",
            source_name="Carousell HK",
            source_url="https://www.carousell.com.hk/search/Charizard%20VSTAR%20PSA%2010",
            asking_price_hkd=720,
            target_resale_hkd=920,
            confidence=68,
            risk_note="Need seller confirmation and recent eBay sold comp check.",
        ),
        OpportunityCreate(
            title="Pokemon 151 Booster Box local sealed watch",
            card_name="Pokemon 151 Booster Box",
            set_name="Pokemon 151",
            condition_note="Sealed box. Avoid no-shrink or suspicious reseal.",
            image_url="https://images.pokemontcg.io/sv3pt5/199_hires.png",
            source_name="Carousell HK",
            source_url="https://www.carousell.com.hk/search/pokemon%20151%20booster%20box",
            asking_price_hkd=980,
            target_resale_hkd=1250,
            confidence=62,
            risk_note="Sealed authenticity and availability must be checked manually.",
        ),
    ]
    ids = [create_opportunity(item)["id"] for item in demo]
    return {"ok": True, "ids": ids}


@app.post("/api/opportunities/{opportunity_id}/approve")
def approve_opportunity(opportunity_id: int) -> dict[str, Any]:
    return update_opportunity_status(opportunity_id, "approved")


@app.post("/api/opportunities/{opportunity_id}/reject")
def reject_opportunity(opportunity_id: int) -> dict[str, Any]:
    return update_opportunity_status(opportunity_id, "rejected")


@app.get("/api/storefront")
def storefront() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM opportunities WHERE status = 'approved' ORDER BY estimated_profit_hkd DESC"
        ).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/orders")
def create_order(payload: OrderCreate) -> dict[str, Any]:
    with connect() as conn:
        opp = conn.execute("SELECT * FROM opportunities WHERE id = ? AND status = 'approved'", (payload.opportunity_id,)).fetchone()
        if not opp:
            raise HTTPException(status_code=404, detail="Approved opportunity not found")
        cursor = conn.execute(
            """
            INSERT INTO orders (opportunity_id, buyer_name, buyer_contact, quantity, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.opportunity_id, payload.buyer_name, payload.buyer_contact, payload.quantity, payload.message),
        )
        conn.commit()
    return {"ok": True, "order_id": cursor.lastrowid, "note": "Order request received. Availability and final price must be confirmed manually."}


@app.get("/api/orders")
def list_orders() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT orders.*, opportunities.title, opportunities.card_name
            FROM orders
            JOIN opportunities ON opportunities.id = orders.opportunity_id
            ORDER BY orders.created_at DESC
            """
        ).fetchall()
    return rows_to_dicts(rows)


def update_opportunity_status(opportunity_id: int, status: str) -> dict[str, Any]:
    with connect() as conn:
        cursor = conn.execute("UPDATE opportunities SET status = ? WHERE id = ?", (status, opportunity_id))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"ok": True, "id": opportunity_id, "status": status}


def seed_sources() -> None:
    sources = [
        ("Carousell HK", "https://www.carousell.com.hk/search/pokemon%20card", "buy source", "local listing", 1),
        ("eBay Sold Listings", "https://www.ebay.com/sch/i.html?_nkw=pokemon+card&LH_Complete=1&LH_Sold=1", "price comp", "sold comp", 1),
        ("PriceCharting", "https://www.pricecharting.com/category/pokemon-cards", "price comp", "price guide", 1),
        ("PokePrices", "https://www.pokeprices.io/", "price comp", "price guide", 1),
        ("CardIndex", "https://www.cardindex.co/", "price comp", "graded price", 1),
        ("Beelive TCG", "https://beelivetcg.com/", "retail comp", "local shop", 1),
        ("TT Poke", "https://www.tt-poke.com/en", "retail / P2P comp", "local shop", 1),
        ("Cardex Marketplace", "https://www.cardex.trading/", "buy source / comp", "marketplace", 1),
        ("CardCornerX", "https://cardcornerx.com/", "retail / trade comp", "local shop", 1),
        ("General CardShop", "https://linktr.ee/generalcard", "local comp", "social shop", 1),
        ("Facebook Marketplace / Groups", "https://www.facebook.com/marketplace/", "manual buy source", "manual", 0),
        ("TCGplayer", "https://www.tcgplayer.com/categories/trading-and-collectible-card-games/pokemon", "secondary comp", "US marketplace", 0),
    ]
    with connect() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO sources (name, url, role, source_type, approved)
            VALUES (?, ?, ?, ?, ?)
            """,
            sources,
        )
        conn.commit()


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8787, reload=False)
