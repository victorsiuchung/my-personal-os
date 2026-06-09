# Second-hand Market Dashboard Playbook

Use this playbook when creating a dashboard for watching second-hand market prices.

## Purpose

The dashboard should act like a market price observer. It helps decide whether a listing is worth checking, negotiating, or skipping.

## Default Structure

1. Home dashboard overview
2. Recommendation panel
3. Main observation list
4. Detail view for each item
5. Source reference panel
6. Export watchlist action
7. Dark mode

## Recommended UI Style

Use a shadcn/ui + Tailwind-inspired visual style:

- Neutral light/dark palette
- 8px cards and buttons
- Subtle borders
- Quiet shadows
- Badge/pill metadata
- Search and filter controls
- Left list, right detail view
- Clear recommendation grades

## Data Sources

Use at least three kinds of sources:

- Local second-hand listings, such as Carousell, DC Fever, HKEPC, Facebook groups, or local marketplaces
- Sold/completed transaction references, such as eBay Sold Listings, PriceCharting, or specialist price trackers
- First-hand / retail references, such as local shops or official stores

## Recommendation Logic

Each item should include:

- Asking price
- Local listing source
- Sold/completed comp source
- First-hand reference source
- Estimated fair range
- Discount against new price
- Market observer note
- Risk checklist

Suggested grades:

- Recommend: price is meaningfully below sold comps or retail alternatives
- Watch: fair price, but needs verification or negotiation
- Skip: too expensive, unclear, risky, or too close to new price

## Detail View

Each listing detail should show:

- Title
- Source
- Asking price
- Reference price
- Sold/local comps
- New-price comparison
- Estimated edge
- Why it is recommended or not
- Buy-check notes
- Source link

## Publishing Flow

When creating a standalone HTML dashboard:

1. Save the HTML under `docs/` in GitHub.
2. Publish with GitHub Pages.
3. Record the permanent URL in Notion.
4. Add the GitHub file link and short description.

## Safety Note

For second-hand markets, do not treat asking prices as real成交價. Use sold listings where possible, and always verify seller reputation, item condition, authenticity, warranty, and pickup/payment risk.
