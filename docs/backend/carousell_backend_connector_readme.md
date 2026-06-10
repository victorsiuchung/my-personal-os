# Carousell Backend Connector MVP

Date: 2026-06-10

## Current status

Carousell HK blocks direct automated access from this runtime with HTTP 403 / Cloudflare. The in-app browser also shows a Cloudflare block page. Because of that, the MVP uses a safe fallback importer first:

1. Buyer opens Carousell manually.
2. Buyer copies exact listing URL, title, price, seller/contact URL, condition, and notes into `carousell_import_template.csv`.
3. Run `carousell_backend_importer.py`.
4. The script outputs `carousell_candidates.json` with backend-ready fields.

## Backend fields

- `source`
- `query`
- `title`
- `price_hkd`
- `listing_url`
- `seller_contact_url`
- `location`
- `condition`
- `notes`
- `snapshot_time`
- `risk_flag`
- `publish_status`

## Probe command

```powershell
python outputs/carousell_backend_importer.py --probe
```

Current probe result: Carousell search pages return `403 blocked_or_unavailable`.

## Import command

```powershell
python outputs/carousell_backend_importer.py --csv outputs/carousell_import_template.csv --out outputs/carousell_candidates.json
```

## Next integration options

1. Use manual CSV import now for exact seller links and approval flow.
2. Run a collector from a normal logged-in browser/session if Carousell permits access.
3. Use a paid marketplace data provider or official/partner API if available.
4. Add OCR/photo analysis after seller photos are downloaded or uploaded.
