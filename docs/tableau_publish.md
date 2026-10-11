# Build the Tableau workbook by hand

**Short on time?** Use Tableau Public + `extracts/tableau_public_pack.xlsx` and follow **[tableau_public_deadline_plan.md](tableau_public_deadline_plan.md)** (must-have vs good-to-have dashboards).

The reviewer expects the dashboard connected to Snowflake `RETAIL_SALES.MART` in production. Nothing in this repo draws the charts for you. **Tableau Desktop** can live-query Snowflake. **Tableau Public** cannot — use the Excel pack above and say so in the deck.

Anyone with the `.env` password, this repo, and Tableau Desktop can follow the same steps.

## 1. Confirm Snowflake has the mart

In Snowsight (https://tasuvwl-ih32543.snowflakecomputing.com), as `MAF345`:

```sql
USE DATABASE RETAIL_SALES;
USE SCHEMA MART;
SHOW TABLES;
SELECT * FROM MART.MART_KPI_SNAPSHOT;
```

You should see `DIM_*`, `FACT_SALES`, `FACT_SALES_ITEMS`, and the `MART_*` tables. If `SHOW TABLES` is empty, run from the repo:

```powershell
.\.venv\Scripts\python.exe -m etl.run_pipeline --as-of-date 2026-10-10
```

## 2. Connect Tableau Desktop

1. Open Tableau Desktop.
2. **Connect → To a Server → Snowflake**.
3. Server: `tasuvwl-ih32543.snowflakecomputing.com`
4. User: `MAF345`. Password: the value in `.env` (do not put it in the workbook notes or in git).
5. Warehouse: `COMPUTE_WH`. Database: `RETAIL_SALES`. Schema: `MART`.
6. Sign in. If Snowflake asks for MFA or a browser login, complete that prompt. The pipeline cannot click it for you.

Drag these tables onto the canvas. Tableau will suggest relationships; set them as below so grains do not fan out.

| Left | Key | Right |
| --- | --- | --- |
| `FACT_SALES` | `SALE_DATE` = `DATE_KEY` | `DIM_DATE` |
| `FACT_SALES` | `STORE_ID` | `DIM_STORE` |
| `FACT_SALES` | `PAYMENT_TYPE` | `DIM_PAYMENT` |
| `FACT_SALES` | `CUSTOMER_ID` | `DIM_CUSTOMER` |
| `FACT_SALES_ITEMS` | `SALE_ID` | `FACT_SALES` |
| `FACT_SALES_ITEMS` | `PRODUCT_ID` | `DIM_PRODUCT` |

`CUSTOMER_ID` is null on guest tickets. Leave that relationship as a left join from the fact. Do not invent a guest customer.

Use `FACT_SALES` for header KPIs (one row per ticket). Use `FACT_SALES_ITEMS` for product, discount, and basket (one row per line). Put `HAS_LINE_ITEMS` on product sheets so headers with no basket do not look like zero-dollar products.

If Desktop is not available, connect Tableau Public to `extracts/tableau_public_pack.xlsx` instead. Say in the presentation that live Snowflake is the production path and the Excel file is only the publish fallback.

### Add the summary tables (required for step 3)

Most measures are **not** on `FACT_SALES`. They are pre-built columns on **`MART_*` tables**.

1. In the left **Database** pane, open **MART**.
2. **Double-click** each table you need (at minimum: `MART_KPI_SNAPSHOT`, `MART_MONTHLY_GROWTH`, `MART_TIME_INTEL`, `MART_HOURLY_DOW`, `MART_MEMBER_VS_GUEST`, `MART_CUSTOMER_RFM`, `MART_PRODUCT_PERF`, `MART_DISCOUNT_BAND`, `MART_MARKET_BASKET`, `MART_FEED_COMPLETENESS`, `MART_UNUSUAL_TXN`, plus `FACT_SALES` for payment mix).
3. For each **sheet**, use fields from **one** table only (ignore “not related” warnings between tables).

**Exact Snowflake column names, table by table:** see **[tableau_fields_reference.md](tableau_fields_reference.md)**.

There is **no** `PERIOD` column in Snowflake. Use `YEAR` + `MONTH` on `MART_MONTHLY_GROWTH`, or `MONTH_NAME` on `MART_DAILY_SALES`.

## 3. Sheets to create

Create one sheet per row. Names below are **Snowflake columns** (search in Data pane with that spelling).

| Sheet | Snowflake table | Dimensions (Rows/Columns) | Measures (green) | Mark |
| --- | --- | --- | --- | --- |
| KPI | `MART_KPI_SNAPSHOT` | — | `TXN_COUNT`, `REVENUE_WITH_ITEMS`, `AVG_BASKET_VALUE`, `AVG_BASKET_SIZE`, `ITEM_COVERAGE_PCT` | Text |
| Revenue by month | `MART_MONTHLY_GROWTH` | `MONTH`, `YEAR` | `REVENUE` (SUM) | Line |
| MoM growth | `MART_MONTHLY_GROWTH` | `MONTH`, `YEAR` | `MOM_GROWTH_PCT` | Bar |
| YTD / MTD / QTD | `MART_TIME_INTEL` | `SALE_DATE` | `YTD_REVENUE`, `MTD_REVENUE`, `QTD_REVENUE` (do not double-SUM; see field guide) | Line |
| Store performance | `MART_DAILY_SALES` or `FACT_SALES`+`DIM_STORE` | `STORE_NAME`, `REGION` | `REVENUE` or `SUM(BASKET_VALUE)`, `TXN_COUNT` or `COUNT(SALE_ID)` | Bar |
| Hour and weekday | `MART_HOURLY_DOW` | `SALE_DOW`, `SALE_HOUR` | `TXN_COUNT` (SUM) | Square (heatmap) |
| Member vs guest | `MART_MEMBER_VS_GUEST` | `CUSTOMER_TYPE` | `REVENUE`, `TXN_COUNT`, `AVG_BASKET_VALUE` | Bar |
| Churn | `MART_CUSTOMER_RFM` | `IS_CHURNED_90D` | `COUNT(CUSTOMER_ID)` | Bar |
| RFM | `MART_CUSTOMER_RFM` | `R_SCORE`, `F_SCORE` | `M_SCORE` (color), `COUNT(CUSTOMER_ID)`, `SUM(MONETARY)` | Square / text |
| Product revenue | `MART_PRODUCT_PERF` | `PRODUCT_NAME`, `CATEGORY` | `REVENUE`, `UNITS` (SUM) | Bar |
| Discount bands | `MART_DISCOUNT_BAND` | `DISCOUNT_BAND`, `CATEGORY` | `REVENUE`, `UNITS` | Bar |
| Basket pairs | `MART_MARKET_BASKET` | `PRODUCT_A_NAME`, `PRODUCT_B_NAME` | `LIFT`, `PAIR_BASKETS` | Bar |
| Payment mix | `FACT_SALES` | `PAYMENT_TYPE` | `SUM(BASKET_VALUE)`, `COUNT(SALE_ID)` | Pie / bar |
| Feed completeness | `MART_FEED_COMPLETENESS` | `SALE_DATE` (month) | `AVG(ITEM_COVERAGE_PCT)` | Line |
| Unusual tickets | `MART_UNUSUAL_TXN` | `SALE_ID` | `BASKET_VALUE`, `VALUE_ZSCORE` | Table |

Only if you skip `MART_*` tables and use facts only — create calculated fields on `FACT_SALES`:

- `SUM(IIF([HAS_LINE_ITEMS], 1, 0)) / COUNT([SALE_ID])` for coverage
- Product lines: `SUM([TOTAL_VALUE])` on `FACT_SALES_ITEMS`, not `BASKET_VALUE`

Format currency as dollars and `ITEM_COVERAGE_PCT` / `MOM_GROWTH_PCT` as percent.

## 4. Dashboards

New dashboard, size **Automatic** or 1366×768. Float or tile the sheets. Add the filters **date**, **region**, **customer type** to the context of every sales dashboard (Apply to worksheets → All using this data source).

1. **Executive** — KPI sheet, monthly revenue, MoM, store bar, payment mix.
2. **Store and time** — store bar, hour/weekday heat map, YTD/MTD/QTD.
3. **Members** — member vs guest, churn, RFM. Caption: guests are not in the churn definition; 90 days flags most members because they buy about 2.4 times in 18 months; win back the high-monetary band.
4. **Assortment** — product bar, discount bands, top lift pairs.
5. **Feed quality** — coverage line, unusual-ticket table. Caption: 55.6% of headers have no lines (sale ids 100000–126666 only). Do not drop those headers.

## 5. Story

Story → New story → Size matches the dashboards. One point per dashboard, in this order:

1. Where revenue comes from (Executive).
2. When and which store (Store and time). Cashier equals store in this extract.
3. Who is at risk (Members).
4. What sells together and which discounts show up (Assortment).
5. Whether the items feed can be trusted (Feed quality).

Caption each point with the “so what”, not only the chart title.

## 6. Save and hand off

Save as `tableau/Retail_Sales_Analysis.twbx` (packaged) if you used the Excel extract, or `.twb` if the connection is live Snowflake. A live workbook still needs the reviewer’s Tableau to log into the same Snowflake account. For a reviewer who will not have your password, publish an extract (`.twbx` or `.hyper`) from the Snowflake connection: Data → Extract → Create, then save as `.twbx`.

Do not embed the password in the file if Tableau offers “embed credentials”, unless the reviewer told you to. Prefer an extract for the submission zip and a live connection for the on-site demo.
