# Pokemon Card Arbitrage Sources For Approval

This list defines which sources the backend should watch before publishing approved deals to the storefront.

## Recommended Source Stack

| Priority | Source | Role | Type | Notes |
|---:|---|---|---|---|
| 1 | Carousell HK | Local second-hand asking prices | Buy source | Best local hunting ground. Treat as asking price unless marked sold/reserved. |
| 2 | eBay Sold Listings | Completed transaction comps | Price comp | Strongest public sold-price reference. Add FX, shipping, tax, and platform spread. |
| 3 | PriceCharting | Raw / graded historical price | Price comp | Useful for PSA / raw card baseline. |
| 4 | PokePrices | Raw price, PSA premium, gem rate | Price comp | Useful for grading-upside analysis. |
| 5 | CardIndex | Graded market data | Price comp | Good for higher-value slabs. |
| 6 | Beelive TCG | Hong Kong retail/local reference | Retail comp | Useful to avoid overpaying on local listings. |
| 7 | TT Poke | HK PSA/raw/sealed reference | Retail / P2P comp | Good local graded-card context. |
| 8 | Cardex Marketplace | HK/community marketplace | Buy source / comp | Useful local supply signal. |
| 9 | CardCornerX | Singles/slabs/sealed shop reference | Retail / trade comp | Good shop reference before private seller deals. |
| 10 | General CardShop / Card Express | Social/shop channels | Local comp | Useful for drops and local availability. |
| 11 | Facebook Marketplace / groups | Local second-hand listings | Manual buy source | High supply, but needs manual verification and scam filtering. |
| 12 | TCGplayer | US market price reference | Price comp | Useful reference but less direct for Hong Kong resale. |

## Approval Recommendation

Approve for MVP:

- Carousell HK
- eBay Sold Listings
- PriceCharting
- PokePrices
- CardIndex
- Beelive TCG
- TT Poke
- Cardex
- CardCornerX
- General CardShop

Manual-only for now:

- Facebook Marketplace / groups

Use as secondary reference only:

- TCGplayer

## Risk Notes

- Carousell and Facebook do not guarantee authenticity or availability.
- Raw card condition can change value dramatically.
- Slabs require cert verification.
- Sealed boxes require reseal checks.
- Do not publish an item as owned inventory unless it is already in hand.
- First storefront version should use order requests, not automatic payment capture.

