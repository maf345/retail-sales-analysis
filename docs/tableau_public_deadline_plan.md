# Tableau Public — deadline plan (must-have vs good-to-have)

**Submitted scope (final):** two dashboards only — **Executive** and **Members & churn**. See **[DASHBOARD_SCOPE.md](DASHBOARD_SCOPE.md)** for outcome mapping. Dashboards 3–5 below were **not** built for Public; analyses remain in Snowflake, extracts, and the PPT.

Use this when **Tableau Desktop + Snowflake** is blocking you. The mart is already built in Snowflake for the written case; the dashboard reads **`extracts/tableau_public_pack.xlsx`** (same numbers, publishable on Public).

In the deck, say once: *Production mart is `RETAIL_SALES.MART` in Snowflake; Tableau Public cannot live-connect, so this workbook uses the exported pack.*

---

## Connect (5 minutes)

1. Open **Tableau Public Desktop**.
2. **Connect → Microsoft Excel** → `extracts/tableau_public_pack.xlsx`.
3. You will see **12 sheets** (each is a small table). You do **not** need to join them. Build **one worksheet per sheet** using **only fields from that sheet**.
4. Save as `tableau/Retail_Sales_Public.twbx` and publish to your profile when done.

Optional second file (only if you have time): `extracts/mart_unusual_txn.csv` for unusual transactions.

---

## Priority legend

| Priority | Meaning |
| --- | --- |
| **P0 — Must-have** | Covers the brief’s core asks; do these first. |
| **P1 — Good-to-have** | Strengthens the story; add if P0 is done. |
| **P2 — Nice-to-have** | Only if time remains. |

Brief alignment: **sales performance**, **churn / members**, **store & region**, **product & discount**, **time trends**, **member vs guest**, **feed / data quality**, **payment**.

---

## Dashboard 1 — Executive (P0) — build this first

**Goal:** One screen answers “how big is the business and where does money go?”

| Sheet in Excel | Worksheet title | Rows / columns | Measure | Mark | Priority |
| --- | --- | --- | --- | --- | --- |
| `kpi` | KPI scorecard | — | Drag all to **Text**: `TXN_COUNT`, `REVENUE_WITH_ITEMS`, `AVG_BASKET_VALUE`, `AVG_BASKET_SIZE`, `ITEM_COVERAGE_PCT`, `MEMBER_TXNS`, `GUEST_TXNS` | Text | **P0** |
| `store_perf` | Revenue by store | `STORE_NAME` | `SUM(REVENUE)` | Bar | **P0** |
| `payment` | Payment mix | `PAYMENT_TYPE` | `SUM(REVENUE)` or `SUM(TXN_COUNT)` | Pie or bar | **P0** |
| `member_guest` | Member vs guest | `CUSTOMER_TYPE` | `SUM(REVENUE)`, `SUM(TXN_COUNT)` | Bar (side by side) | **P0** |
| `monthly_growth` | Revenue trend | `PERIOD` | `SUM(REVENUE)` | Line | **P1** |
| `monthly_growth` | MoM growth | `PERIOD` | `AVG(MOM_GROWTH_PCT)` | Bar | **P1** |

**Dashboard layout:** KPI text across the top; store bar + payment pie middle; member vs guest bottom.

**Filters (P1):** none required on P0. Optional: none on this pack (already aggregated).

**Caption for reviewers:** Item revenue uses baskets with line items; `ITEM_COVERAGE_PCT` ≈ 44% — call out on KPI or Dashboard 3.

---

## Dashboard 2 — Customers & churn (P0)

**Goal:** Churn definition + member behavior (brief requirement).

| Sheet | Worksheet | Fields | Mark | Priority |
| --- | --- | --- | --- | --- |
| `rfm_summary` | Churn vs active members | Rows: `CHURN_FLAG` · Columns: `SUM(CUSTOMERS)` | Bar | **P0** |
| `rfm_summary` | Churned vs active profile | Rows: `CHURN_FLAG` · Text/`AVG`: `AVG_MONETARY`, `AVG_FREQUENCY`, `AVG_RECENCY` | Table or bar | **P1** |
| `member_guest` | Avg basket by type | Rows: `CUSTOMER_TYPE` · `AVG(AVG_BASKET_VALUE)`, `AVG(AVG_BASKET_SIZE)` | Bar | **P1** |

**Dashboard layout:** Large churn bar (9,371 vs active — your numbers from `rfm_summary`); small table of averages.

**Say in caption:** Churn = member, no purchase in **90 days** before snapshot; guests excluded. High “churned” % is expected (low visit frequency in data).

**P2:** Connect `extracts/mart_customer_rfm.csv` for RFM heat (`R_SCORE`, `F_SCORE`, `M_SCORE`) — skip if out of time.

---

## Dashboard 3 — Products & promotions (P0)

**Goal:** Product/category and discount (brief requirement).

| Sheet | Worksheet | Fields | Mark | Priority |
| --- | --- | --- | --- | --- |
| `product_total` | Top products | Rows: `PRODUCT_NAME` · Columns: `SUM(REVENUE)` · Color: `CATEGORY` | Bar, sort desc, top 10 filter | **P0** |
| `discount_band` | Discount bands | Rows: `DISCOUNT_BAND` · Columns: `SUM(REVENUE)` · Color: `CATEGORY` | Bar | **P0** |
| `market_basket` | Basket pairs | Rows: `PRODUCT_A_NAME` · Columns: `AVG(LIFT)` · Filter top 5 | Bar | **P1** |

**P2:** `dim_product` alone — not needed if `product_total` is done.

---

## Dashboard 4 — Operations & data quality (P0 for this dataset)

**Goal:** Missing line items = ops finding (differentiates your case).

| Sheet | Worksheet | Fields | Mark | Priority |
| --- | --- | --- | --- | --- |
| `feed_monthly` | Item feed coverage | Columns: `MONTH` · Rows: `AVG(ITEM_COVERAGE_PCT)` | Line | **P0** |
| `store_perf` | Coverage by store | Rows: `STORE_NAME` · `AVG(ITEM_COVERAGE)` | Bar | **P1** |
| `kpi` | Coverage KPI | Text: `ITEM_COVERAGE_PCT` only | Text | **P0** (can live on Dashboard 1 instead) |

**Caption:** ~55.6% of **sales headers** have no item rows; do not drop them from txn KPIs.

---

## Dashboard 5 — Time & store depth (P1 — good-to-have)

| Sheet | Worksheet | Fields | Mark | Priority |
| --- | --- | --- | --- | --- |
| `hourly` | Peak hours | Rows: `SALE_DOW` · Columns: `SALE_HOUR` · Color: `SUM(TXN_COUNT)` | Heatmap (square) | **P1** |
| `store_perf` | Avg basket by store | `STORE_NAME` · `AVG(AVG_BASKET)` | Bar | **P1** |
| `store_perf` | Cashier note | Use `CASHIER_NAME` on tooltip (1:1 with store) | — | **P2** |

**P2 — YTD/MTD/QTD:** Not in the Excel pack. Use `extracts/mart_time_intel.csv` as a **second** Excel/CSV connection, sheet with `SALE_DATE` + `YTD_REVENUE` / `MTD_REVENUE` / `QTD_REVENUE` line chart. Skip if under 30 minutes left.

**P2 — Unusual transactions:** `extracts/mart_unusual_txn.csv` → table of `SALE_ID`, `BASKET_VALUE`, `VALUE_ZSCORE`.

---

## Minimum viable submission (if only ~2 hours left)

Do **only P0**:

1. **One dashboard “Retail overview”** — `kpi` + `store_perf` + `payment` + `member_guest`.
2. **One dashboard “Churn & products”** — `rfm_summary` churn bar + `product_total` top 10 + `feed_monthly` line OR `ITEM_COVERAGE_PCT` on KPI.
3. **One story (3 slides)** — (1) Overview dashboard, (2) Churn & products, (3) one sentence on Snowflake mart + feed gap.

That still hits: sales, store, payment, member/guest, churn, product, discount optional (add `discount_band` bar if 15 min), data quality.

---

## Recommended order of work (timeboxed)

| Order | Task | ~Time |
| --- | --- | --- |
| 1 | Connect Excel pack | 5 min |
| 2 | KPI text sheet (`kpi`) | 10 min |
| 3 | Store revenue bar (`store_perf`) | 10 min |
| 4 | Payment pie (`payment`) | 10 min |
| 5 | Member vs guest (`member_guest`) | 10 min |
| 6 | Churn bar (`rfm_summary`) | 10 min |
| 7 | Top products (`product_total`) | 15 min |
| 8 | Feed coverage line (`feed_monthly`) | 10 min |
| 9 | Assemble Dashboard 1 + 2 | 20 min |
| 10 | Discount bands (`discount_band`) | 15 min |
| 11 | Monthly revenue line (`monthly_growth`) | 15 min |
| 12 | Hourly heatmap (`hourly`) | 20 min |
| 13 | Basket lift (`market_basket`) | 15 min |
| 14 | Story + publish Public | 20 min |

Stop at step 9 if the clock runs out; publish anyway.

---

## Excel sheet → column cheat sheet

| Sheet | Columns you will use |
| --- | --- |
| `kpi` | `TXN_COUNT`, `REVENUE_WITH_ITEMS`, `AVG_BASKET_VALUE`, `AVG_BASKET_SIZE`, `ITEM_COVERAGE_PCT`, `MEMBER_TXNS`, `GUEST_TXNS`, `STORE_COUNT` |
| `store_perf` | `STORE_NAME`, `REGION`, `CASHIER_NAME`, `CITY`, `REVENUE`, `TXN_COUNT`, `AVG_BASKET`, `ITEM_COVERAGE` |
| `payment` | `PAYMENT_TYPE`, `TXN_COUNT`, `REVENUE` |
| `member_guest` | `CUSTOMER_TYPE`, `TXN_COUNT`, `REVENUE`, `AVG_BASKET_VALUE`, `AVG_BASKET_SIZE`, `AVG_LINES` |
| `monthly_growth` | `PERIOD`, `YEAR`, `MONTH`, `REVENUE`, `MOM_GROWTH_PCT`, `PREV_MONTH_REVENUE` |
| `product_total` | `PRODUCT_NAME`, `CATEGORY`, `UNITS`, `REVENUE`, `DISCOUNT_AMT` |
| `discount_band` | `DISCOUNT_BAND`, `CATEGORY`, `LINE_COUNT`, `UNITS`, `REVENUE`, `DISCOUNT_AMT` |
| `market_basket` | `PRODUCT_A_NAME`, `PRODUCT_B_NAME`, `LIFT`, `PAIR_BASKETS`, `SUPPORT` |
| `rfm_summary` | `CHURN_FLAG`, `CUSTOMERS`, `AVG_FREQUENCY`, `AVG_MONETARY`, `AVG_RECENCY` |
| `hourly` | `SALE_DOW`, `SALE_HOUR`, `TXN_COUNT`, `REVENUE` |
| `feed_monthly` | `MONTH`, `TXN_COUNT`, `TXN_WITH_ITEMS`, `TXN_MISSING_ITEMS`, `ITEM_COVERAGE_PCT` |

---

## Publish

1. **Server → Tableau Public → Save to Tableau Public**.
2. Paste the workbook URL into your submission email / zip readme.
3. Zip for assessors: `etl/`, `sql/`, `source/`, `docs/`, `Retail_Sales_Analysis_Onsite_Deck.pptx`, `tableau/*.twbx`, and mention Snowflake account + mart name in README.
