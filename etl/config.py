"""Pipeline configuration. Secrets come from environment / .env only."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

SNOWFLAKE = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT", "tasuvwl-ih32543"),
    "user": os.getenv("SNOWFLAKE_USER", "MAF345"),
    "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "database": os.getenv("SNOWFLAKE_DATABASE", "RETAIL_SALES"),
    "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
}

SOURCE_DIR = ROOT / "source"
LANDING_DIR = ROOT / "landing"
SOURCE_FILES = {
    "sales": "Retail_Sales.xlsx",
    "items": "Retail_Items.xlsx",
    "customers": "Customers.json",
}
EXTRACTS_DIR = ROOT / "extracts"
DOCS_DIR = ROOT / "docs"
SQL_DIR = ROOT / "sql"
CHURN_DAYS = 90
