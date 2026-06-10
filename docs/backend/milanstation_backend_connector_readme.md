# Milan Station Backend Connector MVP

Date: 2026-06-10

## Current status

Milan Station public website currently returns server errors from this runtime.

Tested endpoints:

- `https://www.milanstation.com.hk/`
- `https://www.milanstation.com.hk/search?q=Hermes`
- `https://www.milanstation.com.hk/?s=Hermes`
- `https://www.milanstation.com.hk/wp-json/`
- `https://www.milanstation.com.hk/wp-json/wc/store/products?search=Hermes`
- `https://www.milanstation.com.hk/sitemap.xml`
- `https://www.milanstation.com.hk/product-sitemap.xml`

Observed result: HTTP 500 / database connection error.

## MVP fallback

Use `milanstation_import_template.csv` to capture exact product pages, shop quotations, or manual inventory records, then run:

```powershell
python outputs/milanstation_backend_importer.py --csv outputs/milanstation_import_template.csv --out outputs/milanstation_candidates.json
```

Probe command:

```powershell
python outputs/milanstation_backend_importer.py --probe
```

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

## Recommendation

Keep Milan Station as a lower-risk shop reference source, but do not depend on its website as the only automated feed. Pair it with manual quotation capture, Brand Off, Hermès official reference prices, and marketplace listings.
