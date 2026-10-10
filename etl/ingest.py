"""Read dated landing files into RAW-shaped dataframes (no business rules)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from etl.config import LANDING_DIR, ROOT, SOURCE_FILES


def resolve_as_of_date(as_of_date: str | None) -> str:
    if as_of_date:
        return as_of_date
    if LANDING_DIR.exists():
        dated = sorted(
            [p.name for p in LANDING_DIR.iterdir() if p.is_dir() and len(p.name) == 10]
        )
        if dated:
            return dated[-1]
    return datetime.now().strftime("%Y-%m-%d")


def prepare_landing(as_of_date: str) -> Path:
    """Copy the original source drop into landing/YYYY-MM-DD if missing."""
    dest = LANDING_DIR / as_of_date
    dest.mkdir(parents=True, exist_ok=True)
    mapping = {
        SOURCE_FILES["sales"]: ROOT / "Retail_Sales.xlsx",
        SOURCE_FILES["items"]: ROOT / "Retail_Items.xlsx",
        SOURCE_FILES["customers"]: ROOT / "Customers.json",
    }
    for name, src in mapping.items():
        target = dest / name
        if not target.exists():
            if not src.exists():
                raise FileNotFoundError(f"Missing source file: {src}")
            shutil.copy2(src, target)
    return dest


def ingest_sales(path: Path, load_date: str, ingested_at: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = df.rename(columns={"Unnamed: 9": "CUSTOMER_ID_RAW"})
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].apply(_as_raw_str)
    df["_LOAD_DATE"] = load_date
    df["_FILE_NAME"] = path.name
    df["_INGESTED_AT"] = ingested_at
    return df


def ingest_items(path: Path, load_date: str, ingested_at: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].apply(_as_raw_str)
    df["_LOAD_DATE"] = load_date
    df["_FILE_NAME"] = path.name
    df["_INGESTED_AT"] = ingested_at
    return df


def ingest_customers(path: Path, load_date: str, ingested_at: str) -> pd.DataFrame:
    with path.open(encoding="utf-8") as f:
        records = json.load(f)
    rows = []
    for rec in records:
        rows.append(
            {
                "CUSTOMER_ID": rec.get("Customer_Id"),
                "PAYLOAD": json.dumps(rec, ensure_ascii=True),
                "_LOAD_DATE": load_date,
                "_FILE_NAME": path.name,
                "_INGESTED_AT": ingested_at,
            }
        )
    return pd.DataFrame(rows)


def _as_raw_str(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    text = str(value).strip()
    if text.lower() in {"nan", "none", ""}:
        return None
    if text.endswith(".0") and text.replace(".", "", 1).isdigit() is False:
        pass
    return text


def load_raw(as_of_date: str) -> dict[str, pd.DataFrame]:
    folder = prepare_landing(as_of_date)
    ingested_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "sales": ingest_sales(folder / SOURCE_FILES["sales"], as_of_date, ingested_at),
        "items": ingest_items(folder / SOURCE_FILES["items"], as_of_date, ingested_at),
        "customers": ingest_customers(
            folder / SOURCE_FILES["customers"], as_of_date, ingested_at
        ),
    }
