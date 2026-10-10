# Build the Tableau workbook by hand

The reviewer expects the dashboard connected to Snowflake `RETAIL_SALES.MART`. Nothing in this repo draws the Tableau charts for you. Use Tableau Desktop (the product that can log into Snowflake). Tableau Public cannot connect live to Snowflake.

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

## 3. Sheets to create

Create one sheet per row. Put dimensions on Rows or Columns and measures on the other shelf. Set the mark type in the Marks card.

| Sheet | Rows / columns | Measure | Mark | Filter |
| --- | --- | --- | --- | --- |
| KPI | — | `TXN_COUNT`, `REVENUE_WITH_ITEMS`, `AVG_BASKET_VALUE`, `AVG_BASKET_SIZE`, `ITEM_COVERAGE_PCT` from `MART_KPI_SNAPSHOT` | Text / BAN | none |
| Revenue by month | `PERIOD` or `DIM_DATE` month | `BASKET_VALUE` (or `REVENUE` on `MART_MONTHLY_GROWTH`) | Line | `HAS_LINE_ITEMS` = true for dollar revenue |
| MoM growth | month | `MOM_GROWTH_PCT` on `MART_MONTHLY_GROWTH` | Bar | none |
| YTD / MTD / QTD | `SALE_DATE` | `YTD_REVENUE`, `MTD_REVENUE`, `QTD_REVENUE` on `MART_TIME_INTEL` | Line | none |
| Store performance | `STORE_NAME`, `REGION`, `CASHIER_NAME` | `SUM(BASKET_VALUE)`, `COUNT(SALE_ID)` | Bar | none |
| Hour and weekday | `SALE_DOW`, `SALE_HOUR` | `COUNT(SALE_ID)` | Heat map (square + color) | none |
| Member vs guest | `CUSTOMER_TYPE` | revenue, average basket, transaction count from `MART_MEMBER_VS_GUEST` | Bar | none |
| Churn | `IS_CHURNED_90D` | `COUNT(CUSTOMER_ID)` from `MART_CUSTOMER_RFM` | Bar | members only; this table already excludes guests |
| RFM | `R_SCORE`, `F_SCORE`, `M_SCORE` | `COUNT(CUSTOMER_ID)`, `SUM(MONETARY)` | Highlight table | `IS_CHURNED_90D` = true when you talk about win-back |
| Product revenue | `PRODUCT_NAME`, `CATEGORY` | `SUM(TOTAL_VALUE)`, `SUM(QUANTITY)` | Bar | item fact only |
| Discount bands | `DISCOUNT_BAND`, `CATEGORY` | revenue and units from `MART_DISCOUNT_BAND` | Bar | none |
| Baskets bought together | `PRODUCT_A_NAME`, `PRODUCT_B_NAME` | `LIFT`, `PAIR_BASKETS` from `MART_MARKET_BASKET` | Bar, sort by lift | none |
| Payment mix | `PAYMENT_TYPE` | `SUM(BASKET_VALUE)`, `COUNT(SALE_ID)` | Pie or bar | none |
| Feed completeness | month | `ITEM_COVERAGE_PCT` from `MART_FEED_COMPLETENESS` | Line | none |
| Unusual tickets | `SALE_ID` | `BASKET_VALUE`, `VALUE_ZSCORE` from `MART_UNUSUAL_TXN` | Table | none |

Calculated fields worth adding on `FACT_SALES`:

- Revenue for product views: already on the item fact as `TOTAL_VALUE`.
- Coverage: `SUM(IIF([HAS_LINE_ITEMS], 1, 0)) / COUNT([SALE_ID])`.

Format currency as dollars and coverage as a percent.

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
