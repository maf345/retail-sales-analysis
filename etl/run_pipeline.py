"""
Hybrid ELT runner.

  python -m etl.run_pipeline --as-of-date 2026-10-10

Loads dated landing files, builds the local mart + Tableau extracts,
writes DQ/PPT inputs, and loads Snowflake when .env has a password.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.charts import render_charts
from etl.config import DOCS_DIR
from etl.dq import run_dq, write_dq_log
from etl.export_extracts import export_extracts
from etl.ingest import load_raw, resolve_as_of_date
from etl.load_snowflake import snowflake_configured, bootstrap_and_load
from etl.local_db import read_all_raw, upsert_raw, write_mart
from etl.transform import build_mart


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Retail sales hybrid ELT pipeline")
    p.add_argument("--as-of-date", default=None, help="Landing folder YYYY-MM-DD")
    p.add_argument("--skip-snowflake", action="store_true")
    p.add_argument("--skip-pptx", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    as_of = resolve_as_of_date(args.as_of_date)
    print(f"As-of / landing date: {as_of}")

    raw_batch = load_raw(as_of)
    db_path = upsert_raw(raw_batch, as_of)
    raw = read_all_raw()
    print(
        f"RAW rows  sales={len(raw['sales']):,}  items={len(raw['items']):,}  "
        f"customers={len(raw['customers']):,}  (this drop: "
        f"{len(raw_batch['sales']):,} / {len(raw_batch['items']):,} / {len(raw_batch['customers']):,})"
    )
    print(f"Local database: {db_path}")

    mart = build_mart(raw)
    write_mart(mart)
    checks = run_dq(raw, mart)
    dq_path = write_dq_log(checks, as_of)
    print(f"DQ log: {dq_path}")
    print(checks.to_string(index=False))

    paths = export_extracts(mart)
    print(f"Wrote {len(paths)} extract files")

    findings = build_findings(mart, checks, as_of)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    findings_path = DOCS_DIR / "findings.json"
    findings_path.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(f"Findings: {findings_path}")

    sf_msg = "Snowflake skipped (no password in .env or --skip-snowflake)"
    if snowflake_configured() and not args.skip_snowflake:
        try:
            sf_msg = bootstrap_and_load(raw_batch, as_of)
            print(sf_msg)
        except Exception as exc:
            sf_msg = f"Snowflake load failed: {exc}"
            print(sf_msg)
            findings["snowflake_status"] = sf_msg
            findings_path.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    else:
        print(sf_msg)
    findings["snowflake_status"] = sf_msg
    findings_path.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")

    if not args.skip_pptx:
        from etl.build_pptx import build_pptx

        chart_paths = render_charts(mart)
        pptx_path = build_pptx(findings, chart_paths)
        print(f"PPT: {pptx_path}")

    print("Pipeline complete.")


def build_findings(mart: dict, checks, as_of: str) -> dict:
    kpi = mart["mart_kpi_snapshot"].iloc[0]
    mg = mart["mart_member_vs_guest"].set_index("CUSTOMER_TYPE")
    rfm = mart["mart_customer_rfm"]
    monthly = mart["mart_monthly_growth"].sort_values(["YEAR", "MONTH"])
    last = monthly.iloc[-1]
    prod = (
        mart["mart_product_perf"]
        .groupby(["PRODUCT_NAME", "CATEGORY"], as_index=False)["REVENUE"]
        .sum()
        .sort_values("REVENUE", ascending=False)
    )
    stores = mart["fact_sales"].merge(mart["dim_store"], on="STORE_ID")
    store_rev = (
        stores.groupby(["STORE_NAME", "REGION", "CASHIER_NAME"], as_index=False)
        .agg(REVENUE=("BASKET_VALUE", "sum"), TXN=("SALE_ID", "count"))
        .sort_values("REVENUE", ascending=False)
    )
    hourly = (
        mart["mart_hourly_dow"]
        .groupby(["SALE_DOW", "SALE_HOUR"], as_index=False)["TXN_COUNT"]
        .sum()
        .sort_values("TXN_COUNT", ascending=False)
    )
    pay = (
        mart["fact_sales"]
        .groupby("PAYMENT_TYPE", as_index=False)
        .agg(TXN=("SALE_ID", "count"), REVENUE=("BASKET_VALUE", "sum"))
    )
    basket = mart["mart_market_basket"].head(5)
    unusual = mart["mart_unusual_txn"]
    disc = (
        mart["mart_discount_band"]
        .groupby("DISCOUNT_BAND", as_index=False, observed=False)["REVENUE"]
        .sum()
    )
    return {
        "as_of_date": as_of,
        "sale_date_min": str(pd_ts(mart["fact_sales"]["SALE_DATE"].min()))[:10],
        "sale_date_max": str(pd_ts(mart["fact_sales"]["SALE_DATE"].max()))[:10],
        "parse_issues": mart["dq_parse_issues"].to_dict(orient="records"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "kpi": {
            "txn_count": int(kpi["TXN_COUNT"]),
            "revenue_with_items": float(kpi["REVENUE_WITH_ITEMS"]),
            "avg_basket_value": float(kpi["AVG_BASKET_VALUE"]),
            "avg_basket_size": float(kpi["AVG_BASKET_SIZE"]),
            "item_coverage_pct": float(kpi["ITEM_COVERAGE_PCT"]),
            "member_txns": int(kpi["MEMBER_TXNS"]),
            "guest_txns": int(kpi["GUEST_TXNS"]),
            "stores": int(kpi["STORE_COUNT"]),
        },
        "member_guest": mg.round(2).to_dict(orient="index"),
        "churn": {
            "members": int(len(rfm)),
            "churned_90d": int(rfm["IS_CHURNED_90D"].sum()),
            "churn_rate": float(rfm["IS_CHURNED_90D"].mean()),
            "avg_frequency": float(rfm["FREQUENCY"].mean()),
            "avg_monetary": float(rfm["MONETARY"].mean()),
            "avg_recency": float(rfm["RECENCY_DAYS"].mean()),
        },
        "last_month": {
            "year": int(last["YEAR"]),
            "month": int(last["MONTH"]),
            "revenue": float(last["REVENUE"]),
            "mom_growth_pct": None
            if pd_isna(last.get("MOM_GROWTH_PCT"))
            else float(last["MOM_GROWTH_PCT"]),
        },
        "top_products": prod.head(5).round(2).to_dict(orient="records"),
        "bottom_products": prod.tail(3).round(2).to_dict(orient="records"),
        "stores": store_rev.round(2).to_dict(orient="records"),
        "peak_hour": hourly.iloc[0].to_dict(),
        "payment": pay.round(2).to_dict(orient="records"),
        "basket_pairs": basket.round(4).to_dict(orient="records"),
        "unusual_count": int(len(unusual)),
        "discount_revenue": disc.round(2).to_dict(orient="records"),
        "dq": checks.to_dict(orient="records"),
        "snowflake_account": "tasuvwl-ih32543",
        "tableau_public": "https://public.tableau.com/app/profile/maf345/vizzes",
    }


def pd_ts(value):
    import pandas as pd

    return pd.to_datetime(value)


def pd_isna(value) -> bool:
    import pandas as pd

    try:
        return bool(pd.isna(value))
    except Exception:
        return value is None


if __name__ == "__main__":
    main()
