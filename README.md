# Retail sales analysis

Hybrid ELT: files land by date, Python loads Snowflake `RAW`, SQL builds the star schema and analysis mart. Tableau is built by hand against `RETAIL_SALES.MART`.

## Layout

| Path | Role |
| --- | --- |
| `source/` | Original files you were given (Excel, JSON, requirement brief) |
| `landing/YYYY-MM-DD/` | That day's drop. The pipeline copies from `source/` on first run. |
| `etl/` | Ingest, data-quality checks, local mart used for the deck |
| `sql/` | Snowflake DDL, staging, star schema, analysis mart |
| `extracts/` | CSV / Excel copies of the mart, if Tableau cannot reach Snowflake |
| `docs/` | Data dictionary, DQ log, interview notes, Tableau steps |
| `Retail_Sales_Analysis_Onsite_Deck.pptx` | Architecture and findings |

## Run the load

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Put the Snowflake password only in `.env`. Then:

```powershell
.\.venv\Scripts\python.exe -m etl.run_pipeline --as-of-date 2026-10-10
```

Account `tasuvwl-ih32543`, user `MAF345`, warehouse `COMPUTE_WH`, database `RETAIL_SALES`, schemas `RAW`, `STAGING`, `MART`.

Re-running the same date replaces that date's raw rows. A new folder `landing/2026-10-11/` is the next day's drop. Newer `Update_Date` wins.

Tableau Public (submitted): two dashboards — [docs/DASHBOARD_SCOPE.md](docs/DASHBOARD_SCOPE.md). Build notes: [docs/tableau_public_deadline_plan.md](docs/tableau_public_deadline_plan.md). Snowflake Desktop path: [docs/tableau_publish.md](docs/tableau_publish.md).

Another machine (no Cursor): [docs/COLLEAGUE_SETUP.md](docs/COLLEAGUE_SETUP.md).
