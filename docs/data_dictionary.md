# Data dictionary

Grain and the rule that protects it. Guests have a null customer key. Cashier attributes sit on the store dimension because each cashier maps to one store in this extract.

## Landing files

| File | Grain | Notes |
| --- | --- | --- |
| `Retail_Sales.xlsx` | One row per sale header | Column `Unnamed: 9` is customer id. Members always have it. Guests never do. |
| `Retail_Items.xlsx` | One row per sale line | Price may contain `$`, quantity may contain `p`/`pcs`, discount may contain `%`. |
| `Customers.json` | One document per customer | Nested `Phones` array. Status is `Active` or `Inactive`. |

Every RAW row is stamped with `_LOAD_DATE` (folder date), `_FILE_NAME`, and `_INGESTED_AT`.

## RAW (audit copy)

| Table | Contents |
| --- | --- |
| `RAW.SALES_HEADER` | Header columns as varchar, including the renamed customer id |
| `RAW.SALES_ITEMS` | Line columns as varchar, symbols still present |
| `RAW.CUSTOMERS` | `PAYLOAD` is VARIANT (the JSON document) |
| `RAW.LOAD_LOG` | Row counts per source and load date |

Local SQLite uses the same idea with tables `raw_sales_header`, `raw_sales_items`, `raw_customers`, `raw_load_log`.

## Staging

| Object | Rule |
| --- | --- |
| `STAGING.V_SALES_HEADER` | Typed sale. Latest `UPDATE_DATE` per `SALE_ID`. |
| `STAGING.V_SALES_ITEMS` | `$` / `pcs` / `%` stripped. Latest row per `ITEM_ID`. |
| `STAGING.V_CUSTOMER_LATEST` | Latest JSON document per customer (full snapshot). |
| `STAGING.V_CUSTOMER` | Name, gender, age from that document. |
| `STAGING.V_CUSTOMER_PHONE` | `LATERAL FLATTEN` on `Phones`. One row per number. |

`Gender = Unknown` stays Unknown. No imputation.

## Mart dimensions

| Table | Grain | Columns that matter |
| --- | --- | --- |
| `DIM_DATE` | One calendar day | `DATE_KEY`, year, quarter, month, ISO week, weekend flag |
| `DIM_STORE` | One store | Name, city, state, region, **cashier name** |
| `DIM_PRODUCT` | One product | Name, category |
| `DIM_PAYMENT` | One tender | Payment type |
| `DIM_CUSTOMER` | One customer | Name, gender, age, age band, **active phone** |
| `DIM_CUSTOMER_PHONE` | One phone number | Number and Active/Inactive status |

## Mart facts

| Table | Grain | Measures |
| --- | --- | --- |
| `FACT_SALES` | One `SALE_ID` | `HAS_LINE_ITEMS`, line count, basket qty, basket value, basket discount, hour, day name. `CUSTOMER_ID` is null for guests. |
| `FACT_SALES_ITEMS` | One `ITEM_ID` that matches a header | Unit price, qty, discount %, line total, discount amount |

Header KPIs use `FACT_SALES`. Product, discount, and basket KPIs use rows where `HAS_LINE_ITEMS` is true (or `FACT_SALES_ITEMS`).

## Analysis marts (dashboard-ready)

| Table | Use |
| --- | --- |
| `MART_KPI_SNAPSHOT` | Executive totals at max sale date |
| `MART_DAILY_SALES` | Store / region / member / payment by day |
| `MART_TIME_INTEL` | YTD, MTD, QTD, prior-day revenue |
| `MART_MONTHLY_GROWTH` | Month revenue and MoM growth (`YEAR`, `MONTH`, `REVENUE`, `MOM_GROWTH_PCT`) |
| `MART_HOURLY_DOW` | Weekday × hour |
| `MART_PRODUCT_PERF` | Product revenue, units, discount |
| `MART_DISCOUNT_BAND` | 0% / 5% / 10% / 15%+ by category |
| `MART_CUSTOMER_RFM` | Members only. Recency, frequency, monetary, 90-day churn flag, RFM quintiles |
| `MART_MARKET_BASKET` | Top 50 pairs by lift on complete baskets |
| `MART_UNUSUAL_TXN` | \|z\| ≥ 3 on basket value, or high-discount bulk (qty ≥ 20 and discount ≥ 12% of gross) |
| `MART_FEED_COMPLETENESS` | Headers vs headers-with-items by day and store |
| `MART_MEMBER_VS_GUEST` | Spend and basket comparison |

Churn: a **member** whose last purchase is more than 90 days before the snapshot (maximum sale date). Guests are excluded. Customers who never appear on a sale are not scored.

Basket discount amount is `unit price × quantity × discount percent / 100`. `Total_Value` is checked against `unit price × quantity × (1 − discount percent / 100)`.
