"""Local star-schema database used when Snowflake credentials are not configured.

RAW partitions are kept by load date so a second dated folder merges in,
and re-running the same date replaces that partition (idempotent).
The mart tables are rebuilt from every partition, with newer UPDATE_DATE winning.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from etl.config import ROOT

DB_PATH = ROOT / "data" / "retail_sales.sqlite"

RAW_TABLES = {
    "sales": "raw_sales_header",
    "items": "raw_sales_items",
    "customers": "raw_customers",
}


def upsert_raw(raw: dict[str, pd.DataFrame], as_of_date: str) -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        for key, table in RAW_TABLES.items():
            frame = raw[key]
            exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
            if exists:
                con.execute(f'DELETE FROM "{table}" WHERE "_LOAD_DATE" = ?', (as_of_date,))
                frame.to_sql(table, con, if_exists="append", index=False)
            else:
                frame.to_sql(table, con, if_exists="replace", index=False)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_load_log (
                load_date TEXT,
                source_name TEXT,
                row_count INTEGER,
                ingested_at TEXT
            )
            """
        )
        con.execute("DELETE FROM raw_load_log WHERE load_date = ?", (as_of_date,))
        for key, table in RAW_TABLES.items():
            con.execute(
                "INSERT INTO raw_load_log (load_date, source_name, row_count, ingested_at) VALUES (?, ?, ?, datetime('now'))",
                (as_of_date, table, len(raw[key])),
            )
        con.commit()
    finally:
        con.close()
    return DB_PATH


def read_all_raw() -> dict[str, pd.DataFrame]:
    con = sqlite3.connect(DB_PATH)
    try:
        return {key: pd.read_sql_query(f'SELECT * FROM "{table}"', con) for key, table in RAW_TABLES.items()}
    finally:
        con.close()


def write_mart(mart: dict) -> None:
    con = sqlite3.connect(DB_PATH)
    try:
        for name, frame in mart.items():
            if not isinstance(frame, pd.DataFrame):
                continue
            if name.startswith("dq_"):
                continue
            _sqlite_frame(frame).to_sql(name, con, if_exists="replace", index=False)
        con.commit()
    finally:
        con.close()


def _sqlite_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = pd.to_datetime(out[col]).dt.strftime("%Y-%m-%d %H:%M:%S")
        elif out[col].dtype == bool:
            out[col] = out[col].astype(int)
    return out
