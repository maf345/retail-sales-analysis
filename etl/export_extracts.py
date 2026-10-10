"""Write Tableau Public extracts (CSV + a compact workbook of aggregates)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from etl.config import EXTRACTS_DIR

SKIP = {"dq_parse_issues"}


def export_extracts(mart: dict[str, pd.DataFrame]) -> list[Path]:
    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for name, df in mart.items():
        if name in SKIP or not isinstance(df, pd.DataFrame):
            continue
        path = EXTRACTS_DIR / f"{name}.csv"
        out = _for_csv(df)
        out.to_csv(path, index=False)
        written.append(path)

    compact = {
        "kpi": mart["mart_kpi_snapshot"],
        "member_guest": mart["mart_member_vs_guest"],
        "monthly_growth": mart["mart_monthly_growth"],
        "discount_band": mart["mart_discount_band"],
        "market_basket": mart["mart_market_basket"],
        "dim_store": mart["dim_store"],
        "dim_product": mart["dim_product"],
        "product_total": (
            mart["mart_product_perf"]
            .groupby(["PRODUCT_ID", "PRODUCT_NAME", "CATEGORY"], as_index=False)
            .agg(UNITS=("UNITS", "sum"), REVENUE=("REVENUE", "sum"), DISCOUNT_AMT=("DISCOUNT_AMT", "sum"))
        ),
        "rfm_summary": _rfm_summary(mart["mart_customer_rfm"]),
        "hourly": (
            mart["mart_hourly_dow"]
            .groupby(["SALE_DOW", "SALE_HOUR"], as_index=False)
            .agg(TXN_COUNT=("TXN_COUNT", "sum"), REVENUE=("REVENUE", "sum"))
        ),
        "feed_monthly": _feed_monthly(mart["mart_feed_completeness"]),
        "store_perf": _store_perf(mart["fact_sales"], mart["dim_store"]),
        "payment": mart["fact_sales"]
        .groupby("PAYMENT_TYPE", as_index=False)
        .agg(TXN_COUNT=("SALE_ID", "count"), REVENUE=("BASKET_VALUE", "sum")),
    }
    xlsx = EXTRACTS_DIR / "tableau_public_pack.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        for sheet, df in compact.items():
            _for_csv(df).to_excel(writer, sheet_name=sheet[:31], index=False)
    written.append(xlsx)
    return written


def _rfm_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    out = rfm.copy()
    out["CHURN_FLAG"] = out["IS_CHURNED_90D"].map({True: "Churned 90d", False: "Active"})
    return (
        out.groupby("CHURN_FLAG", as_index=False)
        .agg(
            CUSTOMERS=("CUSTOMER_ID", "count"),
            AVG_FREQUENCY=("FREQUENCY", "mean"),
            AVG_MONETARY=("MONETARY", "mean"),
            AVG_RECENCY=("RECENCY_DAYS", "mean"),
        )
    )


def _feed_monthly(feed: pd.DataFrame) -> pd.DataFrame:
    tmp = feed.copy()
    tmp["MONTH"] = pd.to_datetime(tmp["SALE_DATE"]).dt.to_period("M").astype(str)
    g = tmp.groupby("MONTH", as_index=False).agg(
        TXN_COUNT=("TXN_COUNT", "sum"),
        TXN_WITH_ITEMS=("TXN_WITH_ITEMS", "sum"),
        TXN_MISSING_ITEMS=("TXN_MISSING_ITEMS", "sum"),
    )
    g["ITEM_COVERAGE_PCT"] = g["TXN_WITH_ITEMS"] / g["TXN_COUNT"]
    return g


def _store_perf(fact: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
    g = fact.groupby("STORE_ID", as_index=False).agg(
        TXN_COUNT=("SALE_ID", "count"),
        REVENUE=("BASKET_VALUE", "sum"),
        AVG_BASKET=("BASKET_VALUE", "mean"),
        ITEM_COVERAGE=("HAS_LINE_ITEMS", "mean"),
    )
    return g.merge(stores, on="STORE_ID", how="left")


def _for_csv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = pd.to_datetime(out[col]).dt.strftime("%Y-%m-%d %H:%M:%S")
        elif str(out[col].dtype) == "period[M]":
            out[col] = out[col].astype(str)
        elif out[col].dtype == bool:
            out[col] = out[col].astype(int)
    return out
