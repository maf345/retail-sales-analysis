# Tableau deliverable scope (final)

**Platform:** Tableau Public  
**Data source:** `extracts/tableau_public_pack.xlsx` (export of `RETAIL_SALES.MART` in Snowflake)  
**Workbook:** save/publish as `tableau/Retail_Sales_Public.twbx` (add to submission zip; not required in git if published to Tableau Public profile)

Dashboards 4–5 and optional sheets (hourly heatmap, market basket, feed-only dashboard, YTD from CSV) were **out of scope** for the submitted workbook to meet the deadline. Snowflake mart, ETL, SQL, and PPT still cover architecture and analyses not shown on Public.

---

## Dashboard 1 — Executive

**Reviewer questions answered:**

| Question | Source sheet | Fields |
| --- | --- | --- |
| How much revenue did we generate? | `kpi` | `REVENUE_WITH_ITEMS` |
| How many transactions occurred? | `kpi` | `TXN_COUNT` |
| Average basket value and size? | `kpi` | `AVG_BASKET_VALUE`, `AVG_BASKET_SIZE` |
| How much item-level coverage exists? | `kpi` | `ITEM_COVERAGE_PCT` (~44.4%) |
| Which stores generate the most revenue? | `store_perf` | `STORE_NAME`, `REVENUE` |
| What payment methods drive sales? | `payment` | `PAYMENT_TYPE`, `REVENUE` / `TXN_COUNT` |
| How do members compare with guests? | `member_guest` | `CUSTOMER_TYPE`, `REVENUE`, `TXN_COUNT` |

**Talking point:** Revenue and basket metrics use item-covered baskets where noted; header transaction count includes all 60k tickets. Item coverage is an ops KPI (items file only covers part of sale ids).

---

## Dashboard 2 — Members & churn

**Reviewer questions answered:**

| Question | Source sheet | Fields |
| --- | --- | --- |
| How many members have churned? | `rfm_summary` | `CHURN_FLAG` = `Churned 90d`, `CUSTOMERS` |
| Is churn significant? | `rfm_summary` + `docs/findings.json` | ~9,371 of 13,993 members (~67%) at 90-day rule |
| How do churned members differ from active? | `rfm_summary` | `AVG_MONETARY`, `AVG_FREQUENCY`, `AVG_RECENCY` by `CHURN_FLAG` |
| Do members exhibit better basket behavior than guests? | `member_guest` | `AVG_BASKET_VALUE`, `AVG_BASKET_SIZE`, `AVG_LINES` by `CUSTOMER_TYPE` |

**Definition (state in presentation):** Member with no purchase in the **90 days** before max sale date (2026-06-30). Guests excluded. High churn % reflects low visit frequency (~2.4 trips per member over the period), not necessarily a broken loyalty program.

---

## Not in Public workbook (covered elsewhere)

| Topic | Where reviewers still see it |
| --- | --- |
| Product top sellers, discount bands | `extracts/`, `Retail_Sales_Analysis_Onsite_Deck.pptx`, Snowflake `MART_PRODUCT_PERF`, `MART_DISCOUNT_BAND` |
| Feed completeness / missing line items | PPT, `docs/dq_log.md`, `MART_FEED_COMPLETENESS` |
| ELT, star schema, JSON flatten | PPT, `sql/`, `etl/` |
| Hourly / MoM / basket lift | CSV extracts + Snowflake marts; optional follow-up |

---

## Publish checklist

1. Publish workbook to Tableau Public profile (link in submission email).
2. Zip: `etl/`, `sql/`, `source/`, `landing/`, `docs/`, `extracts/tableau_public_pack.xlsx`, `Retail_Sales_Analysis_Onsite_Deck.pptx`, `tableau/*.twbx`, `README.md`.
3. Do not zip `.env` or `.venv`.
