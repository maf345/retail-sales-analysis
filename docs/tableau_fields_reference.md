# Tableau field names (match Snowflake exactly)

Snowflake columns are **UPPERCASE**. In the Data pane Tableau may show them as `Txn Count` or `TXN_COUNT` depending on version. Search using the **table name + column** below.

Nothing in step 3 is a Tableau calculated field **unless noted**. Most KPIs already exist as columns on `MART_*` tables.

## Why search fails

1. **Wrong table** — `TXN_COUNT` on `MART_KPI_SNAPSHOT` is not the same as on `MART_DAILY_SALES` or `FACT_SALES`.
2. **Table not on the canvas** — If you only added `FACT_SALES` + dims, fields on `MART_MEMBER_VS_GUEST` will not appear until you drag that table in (Snowflake connection → Database `RETAIL_SALES`, Schema `MART` → double-click the table).
3. **One sheet = one grain** — For pre-built mart tables, use **only fields from that table** on that sheet (no join required). Tableau may warn “not related”; you can ignore it for these summary sheets.
4. **`PERIOD` does not exist in Snowflake** — Use `YEAR` + `MONTH` or `MONTH_NAME` from `DIM_DATE` / `MART_DAILY_SALES`, or use `MART_MONTHLY_GROWTH`.
5. **Green vs blue** — If a numeric column is green (measure) but already aggregated (e.g. one row in `MART_KPI_SNAPSHOT`), use **MAX** or **ATTR** instead of SUM, or drop it on Text with default aggregation.

## Recommended: add these tables in Tableau

From schema **MART**, add every table you will use (double-click each):

| Table | Use for sheets |
| --- | --- |
| `MART_KPI_SNAPSHOT` | Executive KPI |
| `MART_MONTHLY_GROWTH` | Monthly revenue, MoM |
| `MART_TIME_INTEL` | YTD / MTD / QTD |
| `MART_DAILY_SALES` | Optional daily / store trends |
| `MART_HOURLY_DOW` | Hour × weekday heat map |
| `MART_MEMBER_VS_GUEST` | Member vs guest |
| `MART_CUSTOMER_RFM` | Churn, RFM |
| `MART_PRODUCT_PERF` | Product revenue |
| `MART_DISCOUNT_BAND` | Discount bands |
| `MART_MARKET_BASKET` | Basket pairs |
| `MART_FEED_COMPLETENESS` | Feed coverage |
| `MART_UNUSUAL_TXN` | Unusual tickets |
| `FACT_SALES` | Payment mix, store from fact (or use `MART_DAILY_SALES`) |
| `FACT_SALES_ITEMS` | Line-level (usually use `MART_PRODUCT_PERF` instead) |
| `DIM_STORE`, `DIM_DATE`, `DIM_PRODUCT`, `DIM_PAYMENT`, `DIM_CUSTOMER` | Only if building from facts |

Star-schema joins (section 2 of `tableau_publish.md`) are for sheets built **only** from `FACT_SALES` + dims. Summary sheets should use the **`MART_*` table** directly.

---

## Sheet-by-sheet: exact columns

### KPI (table: `MART_KPI_SNAPSHOT`, 1 row)

| Data pane field | Role | On sheet |
| --- | --- | --- |
| `SNAPSHOT_DATE` | date | optional label |
| `TXN_COUNT` | measure | Text |
| `STORE_COUNT` | measure | Text |
| `REVENUE_WITH_ITEMS` | measure | Text |
| `AVG_BASKET_VALUE` | measure | Text |
| `AVG_BASKET_SIZE` | measure | Text |
| `AVG_LINES_PER_BASKET` | measure | Text |
| `ITEM_COVERAGE_PCT` | measure (0–1) | Text, format % |
| `MEMBER_TXNS` | measure | Text |
| `GUEST_TXNS` | measure | Text |

Mark: **Text**. Drag measures to **Text** on Marks. Aggregation: **MAX** or **SUM** (one row — same result).

### Revenue by month (table: `MART_MONTHLY_GROWTH`)

| Field | Role | On sheet |
| --- | --- | --- |
| `YEAR` | dimension | Filter or detail |
| `MONTH` | dimension | Columns (or create calc below) |
| `REVENUE` | measure | Rows, **SUM** |

Optional axis label calc (Tableau calculated field):

```text
Month Label: STR([MONTH]) + "/" + STR([YEAR])
```

Or use **MONTH** on Columns and **YEAR** on Color.

### MoM growth (table: `MART_MONTHLY_GROWTH`)

| Field | On sheet |
| --- | --- |
| `MONTH` (and `YEAR`) | Columns |
| `MOM_GROWTH_PCT` | Rows, **SUM** or **AVG** (one value per month — same) |

Format `MOM_GROWTH_PCT` as percentage.

### YTD / MTD / QTD (table: `MART_TIME_INTEL`)

| Field | On sheet |
| --- | --- |
| `SALE_DATE` | Columns (continuous date, day) |
| `YTD_REVENUE` | Rows |
| `MTD_REVENUE` | Rows (second axis or separate sheet) |
| `QTD_REVENUE` | Rows |

Also on this table: `REVENUE`, `TXN_COUNT`, `PREV_DAY_REVENUE`, `PREV_YEAR_DAY_REVENUE`.

Use **Line** mark. Do not SUM `YTD_REVENUE` across dates — use **MAX** per day or plot each day’s running total as-is (already cumulative in SQL).

### Store performance

**Option A — table `MART_DAILY_SALES`**

| Field | On sheet |
| --- | --- |
| `STORE_NAME` | Rows |
| `REGION` | Color or filter |
| `CASHIER_NAME` | not on this table — use Option B |
| `REVENUE` | Columns **SUM** |
| `TXN_COUNT` | Columns **SUM** |

**Option B — `FACT_SALES` + `DIM_STORE` (relationship on `STORE_ID`)**

| Field | Table | On sheet |
| --- | --- | --- |
| `STORE_NAME` | DIM_STORE | Rows |
| `REGION` | DIM_STORE | Color |
| `CASHIER_NAME` | DIM_STORE | Tooltip |
| `BASKET_VALUE` | FACT_SALES | **SUM** |
| `SALE_ID` | FACT_SALES | **COUNT** |

### Hour and weekday (table: `MART_HOURLY_DOW`)

| Field | On sheet |
| --- | --- |
| `SALE_DOW` | Rows |
| `SALE_HOUR` | Columns |
| `TXN_COUNT` | Color / Size **SUM** |

Mark: **Square**, Color on **SUM(TXN_COUNT)**. Optional filters: `STORE_ID`, `CUSTOMER_TYPE`.

### Member vs guest (table: `MART_MEMBER_VS_GUEST`)

| Field | On sheet |
| --- | --- |
| `CUSTOMER_TYPE` | Rows |
| `TXN_COUNT` | Columns **SUM** |
| `REVENUE` | Columns **SUM** |
| `AVG_BASKET_VALUE` | Columns **AVG** |
| `AVG_BASKET_SIZE` | Columns **AVG** |
| `AVG_LINES` | Columns **AVG** |
| `STORES` | Tooltip **MAX** |

### Churn (table: `MART_CUSTOMER_RFM`)

| Field | On sheet |
| --- | --- |
| `IS_CHURNED_90D` | Rows (True / False) |
| `CUSTOMER_ID` | Columns **COUNT** |

Members only — table already excludes guests.

### RFM (table: `MART_CUSTOMER_RFM`)

| Field | On sheet |
| --- | --- |
| `R_SCORE` | Rows |
| `F_SCORE` | Columns |
| `M_SCORE` | Color |
| `CUSTOMER_ID` | Text **COUNT** |
| `MONETARY` | Text **SUM** |

Other columns: `FREQUENCY`, `RECENCY_DAYS`, `TENURE_DAYS`, `AOV`, `CLV_PROXY`, `LAST_PURCHASE_DATE`, `FIRST_PURCHASE_DATE`.

### Product revenue (table: `MART_PRODUCT_PERF`)

| Field | On sheet |
| --- | --- |
| `PRODUCT_NAME` | Rows |
| `CATEGORY` | Color |
| `REVENUE` | Columns **SUM** |
| `UNITS` | Columns **SUM** |

Optional filters: `SALE_DATE`, `STORE_ID`, `CUSTOMER_TYPE`.

### Discount bands (table: `MART_DISCOUNT_BAND`)

| Field | On sheet |
| --- | --- |
| `DISCOUNT_BAND` | Rows |
| `CATEGORY` | Color |
| `REVENUE` | **SUM** |
| `UNITS` | **SUM** |
| `LINE_COUNT` | **SUM** |
| `DISCOUNT_AMT` | **SUM** |

### Baskets bought together (table: `MART_MARKET_BASKET`)

| Field | On sheet |
| --- | --- |
| `PRODUCT_A_NAME` | Rows |
| `PRODUCT_B_NAME` | Rows or tooltip |
| `LIFT` | Columns, sort descending |
| `PAIR_BASKETS` | Size |
| `SUPPORT`, `CONFIDENCE_A_TO_B`, `CONFIDENCE_B_TO_A` | Tooltip |

### Payment mix (`FACT_SALES` only)

| Field | On sheet |
| --- | --- |
| `PAYMENT_TYPE` | Rows / Color |
| `BASKET_VALUE` | **SUM** |
| `SALE_ID` | **COUNT** |

Filter: none required. Null `BASKET_VALUE` on tickets without lines — use **SUM** (includes zeros).

### Feed completeness (table: `MART_FEED_COMPLETENESS`)

| Field | On sheet |
| --- | --- |
| `SALE_DATE` | Columns (month trunc) |
| `ITEM_COVERAGE_PCT` | Rows **AVG** or **SUM(TXN_WITH_ITEMS)/SUM(TXN_COUNT)** |

Columns on table: `TXN_COUNT`, `TXN_WITH_ITEMS`, `TXN_MISSING_ITEMS`, `STORE_ID`.

For monthly line: use **Month of SALE_DATE** on Columns, **AVG(ITEM_COVERAGE_PCT)** on Rows.

### Unusual tickets (table: `MART_UNUSUAL_TXN`)

| Field | On sheet |
| --- | --- |
| `SALE_ID` | Rows |
| `BASKET_VALUE` | Text |
| `VALUE_ZSCORE` | Text |
| `BASKET_QTY`, `LINE_COUNT`, `BASKET_DISCOUNT_AMT` | Text |
| `IS_VALUE_OUTLIER`, `IS_HIGH_DISCOUNT_BULK` | Color |

---

## Calculated fields (only if you build from `FACT_SALES`)

| Name | Formula |
| --- | --- |
| Item coverage | `SUM(IIF([HAS_LINE_ITEMS], 1, 0)) / COUNT([SALE_ID])` |
| Revenue with items only | `SUM(IIF([HAS_LINE_ITEMS], [BASKET_VALUE], 0))` |

Product line revenue uses **`TOTAL_VALUE`** on `FACT_SALES_ITEMS`, not `BASKET_VALUE`.

---

## Refresh Snowflake after SQL update

If `MART_MONTHLY_GROWTH` is missing in Tableau, re-run the pipeline once so Snowflake gets the new table:

```powershell
.\.venv\Scripts\python.exe -m etl.run_pipeline --as-of-date 2026-10-10
```

Then in Tableau: **Data → Refresh**.
