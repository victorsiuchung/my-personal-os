# eBay Backend Connector MVP

Date: 2026-06-10

## Current status

Public eBay search pages were tested for Hong Kong and global searches.

Observed result:

- `https://www.ebay.com.hk/sch/i.html?_nkw=Hermes+Kelly+28` returned HTTP 403.
- `https://www.ebay.com.hk/sch/i.html?_nkw=Hermes+Birkin+30` returned HTTP 403.
- `https://www.ebay.com/sch/i.html?_nkw=Hermes+Kelly+28&LH_Sold=1&LH_Complete=1` returned HTTP 403 by direct fetch and an eBay error page in browser mode.
- eBay RSS-style search also returned HTTP 403.

Conclusion: public page scraping is not reliable from this runtime.

## Official API path

The correct route is eBay Browse API:

`GET https://api.ebay.com/buy/browse/v1/item_summary/search`

Official docs:

https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search

It can return current active listing summaries by keyword, with item URL, title, price, condition, image, seller and item location fields depending on the response. It requires an eBay OAuth token.

Set:

```powershell
$env:EBAY_OAUTH_TOKEN = "..."
$env:EBAY_MARKETPLACE = "EBAY_US"
python outputs/ebay_backend_importer.py --api --out outputs/ebay_candidates.json
```

Note: eBay sold/completed data may require a different eBay API/product or authorized data source. Browse API is for active listings.

## Fallback CSV import

```powershell
python outputs/ebay_backend_importer.py --csv outputs/ebay_import_template.csv --out outputs/ebay_candidates.json
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

Use eBay as a market reference source, especially for global comps and sold prices, but prefer official API/token access or a data provider instead of scraping public pages.
