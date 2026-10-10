"""Load RAW tables and run Snowflake SQL (DDL → staging → mart)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from etl.config import SNOWFLAKE, SQL_DIR


def snowflake_configured() -> bool:
    return bool(SNOWFLAKE.get("password"))


def connect():
    import snowflake.connector

    if not snowflake_configured():
        raise RuntimeError(
            "SNOWFLAKE_PASSWORD is not set. Copy .env.example to .env and add the password."
        )
    return snowflake.connector.connect(
        account=SNOWFLAKE["account"],
        user=SNOWFLAKE["user"],
        password=SNOWFLAKE["password"],
        warehouse=SNOWFLAKE["warehouse"],
        role=SNOWFLAKE["role"],
    )


def run_sql_file(cur, path: Path) -> None:
    sql = _strip_comments(path.read_text(encoding="utf-8"))
    statements = [s.strip() for s in _split_sql(sql) if s.strip()]
    for stmt in statements:
        cur.execute(stmt)


def _strip_comments(sql: str) -> str:
    """Drop full-line and trailing -- comments so a semicolon inside a comment cannot split SQL."""
    kept = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        if "--" in line:
            line = line.split("--", 1)[0]
        kept.append(line)
    return "\n".join(kept)


def _split_sql(sql: str) -> list[str]:
    """Split on semicolons that are not inside quotes."""
    parts, buf, in_s, in_d = [], [], False, False
    for ch in sql:
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        if ch == ";" and not in_s and not in_d:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def bootstrap_and_load(raw: dict[str, pd.DataFrame], as_of_date: str) -> str:
    conn = connect()
    cur = conn.cursor()
    try:
        run_sql_file(cur, SQL_DIR / "01_ddl.sql")
        cur.execute("USE DATABASE RETAIL_SALES")
        cur.execute("USE WAREHOUSE COMPUTE_WH")

        _replace_raw(cur, conn, "RAW.SALES_HEADER", _header_for_sf(raw["sales"]), as_of_date)
        _replace_raw(cur, conn, "RAW.SALES_ITEMS", _items_for_sf(raw["items"]), as_of_date)
        _load_customers(cur, conn, raw["customers"], as_of_date)

        cur.executemany(
            """
            INSERT INTO RAW.LOAD_LOG (LOAD_DATE, SOURCE_NAME, FILE_NAME, ROW_COUNT, STATUS, MESSAGE)
            VALUES (%s, %s, %s, %s, 'SUCCESS', 'RAW replace for load date')
            """,
            [
                (as_of_date, "SALES_HEADER", "Retail_Sales.xlsx", len(raw["sales"])),
                (as_of_date, "SALES_ITEMS", "Retail_Items.xlsx", len(raw["items"])),
                (as_of_date, "CUSTOMERS", "Customers.json", len(raw["customers"])),
            ],
        )

        for name in ["02_staging.sql", "03_mart.sql", "04_analysis_mart.sql"]:
            run_sql_file(cur, SQL_DIR / name)

        conn.commit()
        return "Snowflake RAW + MART rebuilt successfully"
    finally:
        cur.close()
        conn.close()


def _replace_raw(cur, conn, table: str, df: pd.DataFrame, as_of_date: str) -> None:
    from snowflake.connector.pandas_tools import write_pandas

    cur.execute(f"DELETE FROM {table} WHERE _LOAD_DATE = %s", (as_of_date,))
    ok, nchunks, nrows, _ = write_pandas(
        conn,
        df,
        table_name=table.split(".")[-1],
        database="RETAIL_SALES",
        schema="RAW",
        quote_identifiers=False,
        auto_create_table=False,
    )
    if not ok:
        raise RuntimeError(f"write_pandas failed for {table} ({nchunks} chunks, {nrows} rows)")


def _header_for_sf(df: pd.DataFrame) -> pd.DataFrame:
    colmap = {
        "Sale_ID": "SALE_ID",
        "Sale_Date": "SALE_DATE",
        "Store_ID": "STORE_ID",
        "Store_Name": "STORE_NAME",
        "City": "CITY",
        "State": "STATE",
        "Region": "REGION",
        "Cashier_Name": "CASHIER_NAME",
        "Payment_Type": "PAYMENT_TYPE",
        "CUSTOMER_ID_RAW": "CUSTOMER_ID_RAW",
        "Customer_Type": "CUSTOMER_TYPE",
        "Update_Date": "UPDATE_DATE",
        "_LOAD_DATE": "_LOAD_DATE",
        "_FILE_NAME": "_FILE_NAME",
        "_INGESTED_AT": "_INGESTED_AT",
    }
    out = df.rename(columns=colmap)
    return out[list(colmap.values())]


def _items_for_sf(df: pd.DataFrame) -> pd.DataFrame:
    colmap = {
        "Item_ID": "ITEM_ID",
        "Sale_ID": "SALE_ID",
        "Product_ID": "PRODUCT_ID",
        "Product_Name": "PRODUCT_NAME",
        "Category": "CATEGORY",
        "Unit_Price_USD": "UNIT_PRICE_USD",
        "Quantity": "QUANTITY",
        "Discount_Pct": "DISCOUNT_PCT",
        "Total_Value": "TOTAL_VALUE",
        "Update_Date": "UPDATE_DATE",
        "_LOAD_DATE": "_LOAD_DATE",
        "_FILE_NAME": "_FILE_NAME",
        "_INGESTED_AT": "_INGESTED_AT",
    }
    out = df.rename(columns=colmap)
    return out[list(colmap.values())]


def _load_customers(cur, conn, df: pd.DataFrame, as_of_date: str) -> None:
    from snowflake.connector.pandas_tools import write_pandas

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS RAW.CUSTOMERS_STAGE (
            CUSTOMER_ID NUMBER,
            PAYLOAD VARCHAR,
            _LOAD_DATE DATE,
            _FILE_NAME VARCHAR,
            _INGESTED_AT TIMESTAMP_NTZ
        )
        """
    )
    cur.execute("DELETE FROM RAW.CUSTOMERS_STAGE WHERE _LOAD_DATE = %s", (as_of_date,))
    stage = df.copy()
    write_pandas(
        conn,
        stage,
        table_name="CUSTOMERS_STAGE",
        database="RETAIL_SALES",
        schema="RAW",
        quote_identifiers=False,
        auto_create_table=False,
    )
    cur.execute("DELETE FROM RAW.CUSTOMERS WHERE _LOAD_DATE = %s", (as_of_date,))
    cur.execute(
        """
        INSERT INTO RAW.CUSTOMERS (CUSTOMER_ID, PAYLOAD, _LOAD_DATE, _FILE_NAME, _INGESTED_AT)
        SELECT CUSTOMER_ID, PARSE_JSON(PAYLOAD), _LOAD_DATE, _FILE_NAME, _INGESTED_AT
        FROM RAW.CUSTOMERS_STAGE
        WHERE _LOAD_DATE = %s
        """,
        (as_of_date,),
    )
