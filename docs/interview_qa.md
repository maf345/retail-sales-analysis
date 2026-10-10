# Interview talking points

Say these out loud. Short answers first, then one example.

## Why ELT rather than ETL?

**One-liner:** Python is the ingestion and contract layer; Snowflake is the transform and mart. That is ELT with a thin extract.

- **ELT:** land Excel/JSON into `RAW` with almost no business logic. If a KPI definition changes tomorrow, replay from RAW. The file that arrived is still evidence.
- **Pure ETL** would clean in Python and load only the mart. You lose audit, mix file parsing with business rules, and cannot replay cheaply.
- **What Python still does:** parse `.xlsx` / `.json`, strip `$` / `pcs` / `%`, rename `Unnamed: 9` to customer id, row-level DQ, dated landing.
- **What Snowflake does:** `VARIANT` flatten, typed staging, star schema, incremental MERGE, analysis marts.

WPP-style production cares about *replay, audit, and a feed SLA* — not a hero notebook.

## Why a star schema?

- Facts are events: `fact_sales` one row per ticket, `fact_sales_items` one row per line.
- Dims are descriptors: date, store, product, customer, payment.
- Tableau and time intelligence (YTD/MTD/QTD/MoM) need `dim_date` and stable grain.
- Guests: **NULL customer key**. Never invent a customer row.
- Daily MERGE is on business keys. A wide denormalized dump fights incremental loads.

## Why is cashier on the store dimension?

In this extract each cashier maps to exactly one store. “Cashier performance” is store performance. Say so. If the grain ever changes, add `dim_cashier`.

## JSON flattening

- `RAW.CUSTOMERS.PAYLOAD` is `VARIANT` (the document as received).
- `LATERAL FLATTEN` on `Phones` → `dim_customer_phone`.
- `dim_customer` carries the **Active** phone for easy joins.
- Tableau never queries nested JSON. That is the relational mart they asked for.

## Incremental files

```
landing/2026-10-10/Retail_Sales.xlsx
landing/2026-10-11/   ← next day’s drop
```

`--as-of-date YYYY-MM-DD`. RAW stamped with `_LOAD_DATE`. MERGE on `SALE_ID` / `ITEM_ID` / `CUSTOMER_ID`, newer `UPDATE_DATE` wins. Same folder twice does not duplicate.

We only received one snapshot; the **code path and folder contract** are what production looks like.

## Churn definition (they will interrupt)

Member with no purchase in the **90 days** before the snapshot date (max `SALE_DATE`). Guests cannot churn. RFM sits beside that flag so we can target high-value dormant members.

## Missing line items

~55.6% of headers have no basket (`Sale_ID` only 100000–126666 in the items file). **Do not drop them.** Header KPIs stay; product/basket KPIs filter `HAS_LINE_ITEMS`. This is an ops finding about the items feed.

## Where the database is

`.env` holds the password (never chat, never git). `etl/load_snowflake.py` creates `RETAIL_SALES` and runs `sql/01` through `sql/04`. The reviewer database is that Snowflake mart. Tableau is built by hand against `RETAIL_SALES.MART` (see `docs/tableau_publish.md`).

## Tableau Public vs Snowflake

Tableau Public cannot live-connect to Snowflake. Production: Tableau Desktop on `RETAIL_SALES.MART`. Interview publish: `extracts/` CSVs and `tableau_public_pack.xlsx` → [public profile](https://public.tableau.com/app/profile/maf345/vizzes).

## Guest vs member

Members always have a customer id and match JSON 1:1. Guests never do. Do not average guests into retention.
