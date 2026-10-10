"""Python mirror of Snowflake STAGING + MART transforms (for extracts and local run)."""
from __future__ import annotations

import json
import re
from datetime import datetime

import numpy as np
import pandas as pd

from etl.config import CHURN_DAYS


def _to_number(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    cleaned = cleaned.replace({"": np.nan, "nan": np.nan, "None": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


def stage_sales(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["SALE_ID"] = _to_number(df["Sale_ID"]).astype("Int64")
    df["SALE_TS"] = pd.to_datetime(df["Sale_Date"], errors="coerce")
    df["SALE_DATE"] = df["SALE_TS"].dt.normalize()
    df["STORE_ID"] = _to_number(df["Store_ID"]).astype("Int64")
    df["STORE_NAME"] = df["Store_Name"]
    df["CITY"] = df["City"]
    df["STATE"] = df["State"]
    df["REGION"] = df["Region"]
    df["CASHIER_NAME"] = df["Cashier_Name"]
    df["PAYMENT_TYPE"] = df["Payment_Type"]
    df["CUSTOMER_ID"] = _to_number(df["CUSTOMER_ID_RAW"]).astype("Int64")
    df["CUSTOMER_TYPE"] = df["Customer_Type"]
    df["UPDATE_TS"] = pd.to_datetime(df["Update_Date"], errors="coerce")
    keep = [
        "SALE_ID",
        "SALE_TS",
        "SALE_DATE",
        "STORE_ID",
        "STORE_NAME",
        "CITY",
        "STATE",
        "REGION",
        "CASHIER_NAME",
        "PAYMENT_TYPE",
        "CUSTOMER_ID",
        "CUSTOMER_TYPE",
        "UPDATE_TS",
        "_LOAD_DATE",
        "_FILE_NAME",
    ]
    return df[keep].drop_duplicates("SALE_ID", keep="last")


def stage_items(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["ITEM_ID"] = _to_number(df["Item_ID"]).astype("Int64")
    df["SALE_ID"] = _to_number(df["Sale_ID"]).astype("Int64")
    df["PRODUCT_ID"] = _to_number(df["Product_ID"]).astype("Int64")
    df["PRODUCT_NAME"] = df["Product_Name"]
    df["CATEGORY"] = df["Category"]
    df["UNIT_PRICE_USD"] = _to_number(df["Unit_Price_USD"])
    df["QUANTITY"] = _to_number(df["Quantity"])
    df["DISCOUNT_PCT"] = _to_number(df["Discount_Pct"])
    df["TOTAL_VALUE"] = _to_number(df["Total_Value"])
    df["UPDATE_TS"] = pd.to_datetime(df["Update_Date"], errors="coerce")
    keep = [
        "ITEM_ID",
        "SALE_ID",
        "PRODUCT_ID",
        "PRODUCT_NAME",
        "CATEGORY",
        "UNIT_PRICE_USD",
        "QUANTITY",
        "DISCOUNT_PCT",
        "TOTAL_VALUE",
        "UPDATE_TS",
        "_LOAD_DATE",
        "_FILE_NAME",
    ]
    return df[keep].drop_duplicates("ITEM_ID", keep="last")


def stage_customers(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    customers = []
    phones = []
    for _, row in raw.iterrows():
        payload = json.loads(row["PAYLOAD"])
        customers.append(
            {
                "CUSTOMER_ID": payload["Customer_Id"],
                "CUSTOMER_NAME": payload["Customer_Name"],
                "GENDER": payload["Gender"],
                "AGE": payload["Age"],
                "_LOAD_DATE": row["_LOAD_DATE"],
            }
        )
        for phone in payload.get("Phones") or []:
            phones.append(
                {
                    "CUSTOMER_ID": payload["Customer_Id"],
                    "PHONE_NO": phone.get("Phone_No"),
                    "PHONE_STATUS": phone.get("Status"),
                    "_LOAD_DATE": row["_LOAD_DATE"],
                }
            )
    return pd.DataFrame(customers), pd.DataFrame(phones)


def age_band(age: float) -> str:
    if pd.isna(age):
        return "Unknown"
    age = int(age)
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    return "65+"


def build_mart(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    sales = stage_sales(raw["sales"])
    items = stage_items(raw["items"])
    customers, phones = stage_customers(raw["customers"])

    dim_store = (
        sales.sort_values("UPDATE_TS")
        .drop_duplicates("STORE_ID", keep="last")[
            ["STORE_ID", "STORE_NAME", "CITY", "STATE", "REGION", "CASHIER_NAME"]
        ]
        .reset_index(drop=True)
    )
    dim_product = (
        items.sort_values("UPDATE_TS")
        .drop_duplicates("PRODUCT_ID", keep="last")[
            ["PRODUCT_ID", "PRODUCT_NAME", "CATEGORY"]
        ]
        .reset_index(drop=True)
    )
    dim_payment = sales[["PAYMENT_TYPE"]].drop_duplicates().reset_index(drop=True)
    active = phones[phones["PHONE_STATUS"] == "Active"][
        ["CUSTOMER_ID", "PHONE_NO"]
    ].rename(columns={"PHONE_NO": "ACTIVE_PHONE"})
    dim_customer = customers.merge(active, on="CUSTOMER_ID", how="left")
    dim_customer["AGE_BAND"] = dim_customer["AGE"].map(age_band)

    min_d = sales["SALE_DATE"].min()
    max_d = sales["SALE_DATE"].max()
    dim_date = pd.DataFrame({"DATE_KEY": pd.date_range(min_d, max_d, freq="D")})
    dim_date["YEAR"] = dim_date["DATE_KEY"].dt.year
    dim_date["QUARTER"] = dim_date["DATE_KEY"].dt.quarter
    dim_date["MONTH"] = dim_date["DATE_KEY"].dt.month
    dim_date["MONTH_NAME"] = dim_date["DATE_KEY"].dt.strftime("%b")
    dim_date["ISO_WEEK"] = dim_date["DATE_KEY"].dt.isocalendar().week.astype(int)
    dim_date["DAY_OF_MONTH"] = dim_date["DATE_KEY"].dt.day
    dim_date["DOW_ISO"] = dim_date["DATE_KEY"].dt.dayofweek + 1
    dim_date["DAY_NAME"] = dim_date["DATE_KEY"].dt.strftime("%A")
    dim_date["IS_WEEKEND"] = dim_date["DOW_ISO"].isin([6, 7])

    basket = (
        items.groupby("SALE_ID", as_index=False)
        .agg(
            LINE_COUNT=("ITEM_ID", "count"),
            BASKET_QTY=("QUANTITY", "sum"),
            BASKET_VALUE=("TOTAL_VALUE", "sum"),
        )
    )
    items["DISCOUNT_AMT"] = (
        items["UNIT_PRICE_USD"] * items["QUANTITY"] * items["DISCOUNT_PCT"] / 100.0
    )
    disc = items.groupby("SALE_ID", as_index=False)["DISCOUNT_AMT"].sum().rename(
        columns={"DISCOUNT_AMT": "BASKET_DISCOUNT_AMT"}
    )
    basket = basket.merge(disc, on="SALE_ID", how="left")

    fact_sales = sales.merge(basket, on="SALE_ID", how="left")
    fact_sales["HAS_LINE_ITEMS"] = fact_sales["LINE_COUNT"].notna()
    fact_sales["SALE_HOUR"] = fact_sales["SALE_TS"].dt.hour
    fact_sales["SALE_DOW"] = fact_sales["SALE_TS"].dt.strftime("%A")

    fact_items = items.merge(
        sales[
            [
                "SALE_ID",
                "SALE_TS",
                "SALE_DATE",
                "STORE_ID",
                "CUSTOMER_ID",
                "CUSTOMER_TYPE",
                "PAYMENT_TYPE",
            ]
        ],
        on="SALE_ID",
        how="inner",
    )

    snapshot = fact_sales["SALE_DATE"].max()
    marts = _analysis_tables(
        fact_sales, fact_items, dim_store, dim_product, dim_date, snapshot
    )
    return {
        "dim_date": dim_date,
        "dim_store": dim_store,
        "dim_product": dim_product,
        "dim_payment": dim_payment,
        "dim_customer": dim_customer,
        "dim_customer_phone": phones,
        "fact_sales": fact_sales,
        "fact_sales_items": fact_items,
        **marts,
        "dq_parse_issues": _parse_issue_sample(raw["items"]),
    }


def _analysis_tables(
    fact_sales: pd.DataFrame,
    fact_items: pd.DataFrame,
    dim_store: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_date: pd.DataFrame,
    snapshot: pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    with_items = fact_sales["HAS_LINE_ITEMS"]
    kpi = pd.DataFrame(
        [
            {
                "SNAPSHOT_DATE": snapshot,
                "TXN_COUNT": len(fact_sales),
                "STORE_COUNT": fact_sales["STORE_ID"].nunique(),
                "REVENUE_WITH_ITEMS": fact_sales.loc[with_items, "BASKET_VALUE"].sum(),
                "AVG_BASKET_VALUE": fact_sales.loc[with_items, "BASKET_VALUE"].mean(),
                "AVG_BASKET_SIZE": fact_sales.loc[with_items, "BASKET_QTY"].mean(),
                "AVG_LINES_PER_BASKET": fact_sales.loc[with_items, "LINE_COUNT"].mean(),
                "ITEM_COVERAGE_PCT": with_items.mean(),
                "MEMBER_TXNS": (fact_sales["CUSTOMER_TYPE"] == "Member").sum(),
                "GUEST_TXNS": (fact_sales["CUSTOMER_TYPE"] == "Guest").sum(),
            }
        ]
    )

    daily = (
        fact_sales.merge(dim_store, on="STORE_ID", how="left")
        .groupby(
            [
                "SALE_DATE",
                "STORE_ID",
                "STORE_NAME",
                "REGION",
                "CITY",
                "CUSTOMER_TYPE",
                "PAYMENT_TYPE",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            TXN_COUNT=("SALE_ID", "count"),
            TXN_WITH_ITEMS=("HAS_LINE_ITEMS", "sum"),
            REVENUE=("BASKET_VALUE", "sum"),
            UNITS=("BASKET_QTY", "sum"),
            DISCOUNT_AMT=("BASKET_DISCOUNT_AMT", "sum"),
            AVG_BASKET_VALUE=("BASKET_VALUE", "mean"),
        )
    )
    daily["YEAR"] = pd.to_datetime(daily["SALE_DATE"]).dt.year
    daily["QUARTER"] = pd.to_datetime(daily["SALE_DATE"]).dt.quarter
    daily["MONTH"] = pd.to_datetime(daily["SALE_DATE"]).dt.month
    daily["MONTH_NAME"] = pd.to_datetime(daily["SALE_DATE"]).dt.strftime("%b")

    day_rev = (
        fact_sales.groupby("SALE_DATE", as_index=False)
        .agg(REVENUE=("BASKET_VALUE", "sum"), TXN_COUNT=("SALE_ID", "count"))
        .sort_values("SALE_DATE")
    )
    day_rev["YEAR"] = pd.to_datetime(day_rev["SALE_DATE"]).dt.year
    day_rev["MONTH"] = pd.to_datetime(day_rev["SALE_DATE"]).dt.month
    day_rev["QUARTER"] = pd.to_datetime(day_rev["SALE_DATE"]).dt.quarter
    day_rev["YTD_REVENUE"] = day_rev.groupby("YEAR")["REVENUE"].cumsum()
    day_rev["MTD_REVENUE"] = day_rev.groupby(["YEAR", "MONTH"])["REVENUE"].cumsum()
    day_rev["QTD_REVENUE"] = day_rev.groupby(["YEAR", "QUARTER"])["REVENUE"].cumsum()
    day_rev["PREV_DAY_REVENUE"] = day_rev["REVENUE"].shift(1)
    day_rev["MOM_REVENUE"] = day_rev.groupby(["YEAR", "MONTH"])["REVENUE"].transform("sum")
    monthly = (
        day_rev.groupby(["YEAR", "MONTH"], as_index=False)["REVENUE"]
        .sum()
        .sort_values(["YEAR", "MONTH"])
    )
    monthly["PREV_MONTH_REVENUE"] = monthly["REVENUE"].shift(1)
    monthly["MOM_GROWTH_PCT"] = (
        monthly["REVENUE"] / monthly["PREV_MONTH_REVENUE"] - 1
    )

    hourly = fact_sales.groupby(
        ["SALE_DOW", "SALE_HOUR", "STORE_ID", "CUSTOMER_TYPE"],
        dropna=False,
        as_index=False,
    ).agg(TXN_COUNT=("SALE_ID", "count"), REVENUE=("BASKET_VALUE", "sum"))

    prod = (
        fact_items.merge(dim_product, on="PRODUCT_ID", how="left")
        .groupby(
            ["PRODUCT_ID", "PRODUCT_NAME", "CATEGORY", "SALE_DATE", "STORE_ID", "CUSTOMER_TYPE"],
            dropna=False,
            as_index=False,
        )
        .agg(
            UNITS=("QUANTITY", "sum"),
            REVENUE=("TOTAL_VALUE", "sum"),
            DISCOUNT_AMT=("DISCOUNT_AMT", "sum"),
            AVG_DISCOUNT_PCT=("DISCOUNT_PCT", "mean"),
            LINE_COUNT=("ITEM_ID", "count"),
        )
    )

    tmp = fact_items.merge(dim_product, on="PRODUCT_ID", how="left")
    tmp["DISCOUNT_BAND"] = pd.cut(
        tmp["DISCOUNT_PCT"],
        bins=[-0.1, 0, 5, 10, 100],
        labels=["0%", "5%", "10%", "15%+"],
    )
    discount_band = tmp.groupby(["DISCOUNT_BAND", "CATEGORY"], as_index=False, observed=False).agg(
        LINE_COUNT=("ITEM_ID", "count"),
        UNITS=("QUANTITY", "sum"),
        REVENUE=("TOTAL_VALUE", "sum"),
        DISCOUNT_AMT=("DISCOUNT_AMT", "sum"),
        AVG_LINE_VALUE=("TOTAL_VALUE", "mean"),
    )

    members = fact_sales[fact_sales["CUSTOMER_TYPE"] == "Member"].copy()
    rfm = members.groupby("CUSTOMER_ID", as_index=False).agg(
        FREQUENCY=("SALE_ID", "count"),
        MONETARY=("BASKET_VALUE", "sum"),
        LAST_PURCHASE_DATE=("SALE_DATE", "max"),
        FIRST_PURCHASE_DATE=("SALE_DATE", "min"),
    )
    rfm["RECENCY_DAYS"] = (snapshot - rfm["LAST_PURCHASE_DATE"]).dt.days
    rfm["TENURE_DAYS"] = (rfm["LAST_PURCHASE_DATE"] - rfm["FIRST_PURCHASE_DATE"]).dt.days
    rfm["AOV"] = rfm["MONETARY"] / rfm["FREQUENCY"]
    rfm["CLV_PROXY"] = rfm["FREQUENCY"] * rfm["AOV"]
    rfm["IS_CHURNED_90D"] = rfm["RECENCY_DAYS"] > CHURN_DAYS
    rfm["R_SCORE"] = pd.qcut(rfm["RECENCY_DAYS"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F_SCORE"] = pd.qcut(rfm["FREQUENCY"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M_SCORE"] = pd.qcut(rfm["MONETARY"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    basket_pairs = _market_basket(fact_items, dim_product)

    complete = fact_sales[fact_sales["HAS_LINE_ITEMS"]].copy()
    mu = complete["BASKET_VALUE"].mean()
    sd = complete["BASKET_VALUE"].std()
    complete["VALUE_ZSCORE"] = (complete["BASKET_VALUE"] - mu) / sd
    complete["IS_VALUE_OUTLIER"] = complete["VALUE_ZSCORE"].abs() >= 3
    gross = complete["BASKET_VALUE"] + complete["BASKET_DISCOUNT_AMT"].fillna(0)
    complete["IS_HIGH_DISCOUNT_BULK"] = (
        (complete["BASKET_DISCOUNT_AMT"].fillna(0) / gross >= 0.12)
        & (complete["BASKET_QTY"] >= 20)
    )
    unusual = complete[complete["IS_VALUE_OUTLIER"] | complete["IS_HIGH_DISCOUNT_BULK"]][
        [
            "SALE_ID",
            "SALE_TS",
            "STORE_ID",
            "CUSTOMER_TYPE",
            "PAYMENT_TYPE",
            "BASKET_VALUE",
            "BASKET_QTY",
            "LINE_COUNT",
            "BASKET_DISCOUNT_AMT",
            "VALUE_ZSCORE",
            "IS_VALUE_OUTLIER",
            "IS_HIGH_DISCOUNT_BULK",
        ]
    ]

    feed = fact_sales.groupby(["SALE_DATE", "STORE_ID"], as_index=False).agg(
        TXN_COUNT=("SALE_ID", "count"),
        TXN_WITH_ITEMS=("HAS_LINE_ITEMS", "sum"),
    )
    feed["TXN_MISSING_ITEMS"] = feed["TXN_COUNT"] - feed["TXN_WITH_ITEMS"]
    feed["ITEM_COVERAGE_PCT"] = feed["TXN_WITH_ITEMS"] / feed["TXN_COUNT"]

    member_guest = fact_sales.groupby("CUSTOMER_TYPE", as_index=False).agg(
        TXN_COUNT=("SALE_ID", "count"),
        STORES=("STORE_ID", "nunique"),
        REVENUE=("BASKET_VALUE", "sum"),
        AVG_BASKET_VALUE=("BASKET_VALUE", "mean"),
        AVG_BASKET_SIZE=("BASKET_QTY", "mean"),
        AVG_LINES=("LINE_COUNT", "mean"),
    )

    return {
        "mart_kpi_snapshot": kpi,
        "mart_daily_sales": daily,
        "mart_time_intel": day_rev,
        "mart_monthly_growth": monthly,
        "mart_hourly_dow": hourly,
        "mart_product_perf": prod,
        "mart_discount_band": discount_band,
        "mart_customer_rfm": rfm,
        "mart_market_basket": basket_pairs,
        "mart_unusual_txn": unusual,
        "mart_feed_completeness": feed,
        "mart_member_vs_guest": member_guest,
    }


def _market_basket(fact_items: pd.DataFrame, dim_product: pd.DataFrame) -> pd.DataFrame:
    uniq = fact_items[["SALE_ID", "PRODUCT_ID"]].drop_duplicates()
    pairs = uniq.merge(uniq, on="SALE_ID")
    pairs = pairs[pairs["PRODUCT_ID_x"] < pairs["PRODUCT_ID_y"]]
    pair_n = (
        pairs.groupby(["PRODUCT_ID_x", "PRODUCT_ID_y"], as_index=False)
        .SALE_ID.nunique()
        .rename(
            columns={
                "PRODUCT_ID_x": "PRODUCT_A",
                "PRODUCT_ID_y": "PRODUCT_B",
                "SALE_ID": "PAIR_BASKETS",
            }
        )
    )
    prod_n = uniq.groupby("PRODUCT_ID").SALE_ID.nunique()
    total = uniq["SALE_ID"].nunique()
    names = dim_product.set_index("PRODUCT_ID")["PRODUCT_NAME"]
    pair_n["PRODUCT_A_NAME"] = pair_n["PRODUCT_A"].map(names)
    pair_n["PRODUCT_B_NAME"] = pair_n["PRODUCT_B"].map(names)
    pair_n["SUPPORT"] = pair_n["PAIR_BASKETS"] / total
    pair_n["CONFIDENCE_A_TO_B"] = pair_n["PAIR_BASKETS"] / pair_n["PRODUCT_A"].map(prod_n)
    pair_n["CONFIDENCE_B_TO_A"] = pair_n["PAIR_BASKETS"] / pair_n["PRODUCT_B"].map(prod_n)
    pair_n["LIFT"] = pair_n["SUPPORT"] / (
        (pair_n["PRODUCT_A"].map(prod_n) / total) * (pair_n["PRODUCT_B"].map(prod_n) / total)
    )
    return pair_n.sort_values(["LIFT", "PAIR_BASKETS"], ascending=False).head(50)


def _parse_issue_sample(raw_items: pd.DataFrame) -> pd.DataFrame:
    price_bad = raw_items["Unit_Price_USD"].astype(str).str.contains(r"\$", regex=True)
    qty_bad = raw_items["Quantity"].astype(str).str.contains(r"[A-Za-z]", regex=True)
    disc_bad = raw_items["Discount_Pct"].astype(str).str.contains(r"%", regex=True)
    flags = pd.DataFrame(
        {
            "issue": ["unit_price_dollar_sign", "quantity_suffix", "discount_percent_sign"],
            "row_count": [int(price_bad.sum()), int(qty_bad.sum()), int(disc_bad.sum())],
        }
    )
    return flags
