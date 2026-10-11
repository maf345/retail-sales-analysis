# Data quality log

Load date: **2026-10-10**
Generated: 2026-10-11 13:16 UTC

| Check | Status | Detail |
|---|---|---|
| sales_pk_unique | PASS | 60000 unique / 60000 rows |
| items_pk_unique | PASS | 80000 unique / 80000 rows |
| customer_pk_unique | PASS | 13993 customers |
| items_without_header | PASS | 0 item rows whose Sale_ID is not on a header |
| total_value_matches_formula | PASS | 0 lines differ from price * qty * (1 - discount) by more than $0.05 (max gap 0.0050) |
| headers_missing_line_items | WARN | 33,333 sales (55.6%) have no basket rows — keep as ops KPI, do not drop |
| member_always_has_customer_id | PASS | null member keys=0 |
| guest_never_has_customer_id | PASS | guest keys present=0 |
| members_match_customer_dim | PASS | unmatched members=0; unused customers=0 |
| unit_price_dollar_sign | WARN | 800 raw rows cleaned in staging |
| quantity_suffix | WARN | 1200 raw rows cleaned in staging |
| discount_percent_sign | WARN | 800 raw rows cleaned in staging |
| cashier_one_to_one_store | WARN | Each cashier maps to exactly one store in this extract — report as store performance |

## Resolution rules

- `$` on price, `p`/`pcs` on qty, `%` on discount: strip in staging; RAW is unchanged.
- Missing line items: **do not delete** header sales. `HAS_LINE_ITEMS` drives product/basket KPIs.
- `Unnamed: 9` renamed to customer id at ingest; guests stay NULL.
- `Gender = Unknown` is kept; no imputation.
