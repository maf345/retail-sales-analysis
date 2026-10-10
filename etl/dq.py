"""Data-quality checks written to docs/dq_log.md and RAW.LOAD_LOG."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from etl.config import DOCS_DIR


def run_dq(raw: dict[str, pd.DataFrame], mart: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sales = mart["fact_sales"]
    items = mart["fact_sales_items"]
    customers = mart["dim_customer"]
    issues = mart["dq_parse_issues"]

    checks = []

    def add(name, status, detail):
        checks.append({"check_name": name, "status": status, "detail": detail})

    add(
        "sales_pk_unique",
        "PASS" if sales["SALE_ID"].is_unique else "FAIL",
        f"{sales['SALE_ID'].nunique()} unique / {len(sales)} rows",
    )
    add(
        "items_pk_unique",
        "PASS" if items["ITEM_ID"].is_unique else "FAIL",
        f"{items['ITEM_ID'].nunique()} unique / {len(items)} rows",
    )
    add(
        "customer_pk_unique",
        "PASS" if customers["CUSTOMER_ID"].is_unique else "FAIL",
        f"{customers['CUSTOMER_ID'].nunique()} customers",
    )
    orphan_items = (~raw_sale_ids_match(raw)).sum() if False else 0
    item_sales = set(items["SALE_ID"].dropna().astype(int))
    header_sales = set(sales["SALE_ID"].dropna().astype(int))
    add(
        "items_without_header",
        "PASS" if len(item_sales - header_sales) == 0 else "FAIL",
        f"{len(item_sales - header_sales)} orphan sale ids",
    )
    missing_lines = len(header_sales - item_sales)
    pct = 1 - sales["HAS_LINE_ITEMS"].mean()
    add(
        "headers_missing_line_items",
        "WARN",
        f"{missing_lines:,} sales ({pct:.1%}) have no basket rows — keep as ops KPI, do not drop",
    )
    members = sales[sales["CUSTOMER_TYPE"] == "Member"]
    guests = sales[sales["CUSTOMER_TYPE"] == "Guest"]
    add(
        "member_always_has_customer_id",
        "PASS" if members["CUSTOMER_ID"].notna().all() else "FAIL",
        f"null member keys={members['CUSTOMER_ID'].isna().sum()}",
    )
    add(
        "guest_never_has_customer_id",
        "PASS" if guests["CUSTOMER_ID"].isna().all() else "FAIL",
        f"guest keys present={guests['CUSTOMER_ID'].notna().sum()}",
    )
    member_ids = set(members["CUSTOMER_ID"].dropna().astype(int))
    cust_ids = set(customers["CUSTOMER_ID"].astype(int))
    add(
        "members_match_customer_dim",
        "PASS" if len(member_ids - cust_ids) == 0 else "FAIL",
        f"unmatched members={len(member_ids - cust_ids)}; unused customers={len(cust_ids - member_ids)}",
    )
    for _, row in issues.iterrows():
        add(row["issue"], "WARN" if row["row_count"] else "PASS", f"{int(row['row_count'])} raw rows cleaned in staging")

    store_cashier = mart["dim_store"].groupby("CASHIER_NAME")["STORE_ID"].nunique().max()
    add(
        "cashier_one_to_one_store",
        "WARN" if store_cashier == 1 else "FAIL",
        "Each cashier maps to exactly one store in this extract — report as store performance",
    )
    return pd.DataFrame(checks)


def raw_sale_ids_match(raw):
    return pd.Series(dtype=bool)


def write_dq_log(checks: pd.DataFrame, as_of_date: str) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_DIR / "dq_log.md"
    lines = [
        "# Data quality log",
        "",
        f"Load date: **{as_of_date}**",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for _, row in checks.iterrows():
        lines.append(f"| {row['check_name']} | {row['status']} | {row['detail']} |")
    lines.extend(
        [
            "",
            "## Resolution rules",
            "",
            "- `$` on price, `p`/`pcs` on qty, `%` on discount: strip in staging; RAW is unchanged.",
            "- Missing line items: **do not delete** header sales. `HAS_LINE_ITEMS` drives product/basket KPIs.",
            "- `Unnamed: 9` renamed to customer id at ingest; guests stay NULL.",
            "- `Gender = Unknown` is kept; no imputation.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
