# Pokemon Card Arbitrage System

Backend and storefront workflow for Hong Kong Pokemon card arbitrage.

## Core Idea

1. Watch second-hand / local marketplace sources.
2. Compare asking price with market comps.
3. Calculate estimated resale margin.
4. Keep every candidate in `pending` status.
5. Owner approves a candidate.
6. Approved candidates appear on the storefront as preorder / availability-check listings.
7. Buyer submits an order request.
8. Owner buys source item only after confirming buyer intent and availability.

## Important Operating Rule

Do not present unowned items as guaranteed stock. The storefront wording should stay clear:

- subject to availability
- preorder / sourcing request
- final price and delivery confirmed manually
- no payment captured by this MVP

## Data Sources To Approve

See:

```text
source-approval.md
```

## Run Backend

```bash
cd pokemon-arbitrage-system
pip install -r requirements.txt
python app.py
```

API runs at:

```text
http://127.0.0.1:8787
```

## Deploy Backend

GitHub Pages can only host static HTML, so the Python API needs a backend host such as Render, Railway, Fly.io, or a VPS.

This folder includes:

```text
Dockerfile
render.yaml
```

Recommended simple path:

1. Push this folder to GitHub.
2. Create a new Render Web Service from the repo.
3. Set the root directory to `pokemon-arbitrage-system`.
4. Use Docker deployment.
5. After Render gives you a public URL, update `apiBase` in `docs/pokemon-arbitrage-storefront.html`.

Example:

```js
const apiBase = "https://your-render-service.onrender.com";
```

## Main Endpoints

```text
GET  /api/health
GET  /api/sources
GET  /api/opportunities
POST /api/opportunities/seed
POST /api/opportunities/{id}/approve
POST /api/opportunities/{id}/reject
GET  /api/storefront
POST /api/orders
GET  /api/orders
```

## Next Step

After source approval, add source-specific collectors:

- Carousell HK search importer
- eBay sold listing checker
- Beelive / TT Poke / Cardex / CardCornerX retail reference importers
- Manual Facebook Marketplace / group deal entry
