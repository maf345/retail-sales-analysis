# Run this project on another laptop (no Cursor)

Anyone with Python 3.10+, Tableau Desktop, and the Snowflake password can finish and submit from this repo.

## What is already done in the shared Snowflake account

If `MAF345` still has access to `tasuvwl-ih32543`, the mart may already be loaded:

```sql
USE DATABASE RETAIL_SALES;
USE SCHEMA MART;
SELECT * FROM MART.MART_KPI_SNAPSHOT;
```

You should see **60,000** transactions and about **44.4%** item coverage. If that query works, you can **skip re-running the pipeline** and go straight to Tableau. Re-run only if tables are missing or you need to prove the ETL on your machine.

## One-time setup on the new laptop

1. **Clone**

   ```bash
   git clone https://github.com/maf345/retail-sales-analysis.git
   cd retail-sales-analysis
   ```

2. **Python environment**

   Windows (PowerShell):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   copy .env.example .env
   ```

   macOS / Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

3. **Secrets** — Edit `.env` and set `SNOWFLAKE_PASSWORD`. Get the password from your teammate **outside git** (Teams, password manager, etc.). Never commit `.env`.

4. **Optional: run the pipeline** (proves ETL + refreshes Snowflake)

   ```powershell
   python -m etl.run_pipeline --as-of-date 2026-10-10
   ```

   Source files live in `source/`. The job copies them into `landing/2026-10-10/` if needed, loads Snowflake, writes `docs/dq_log.md`, and rebuilds `Retail_Sales_Analysis_Onsite_Deck.pptx`.

## Tableau (manual — required for the 40% dashboard grade)

Tableau Desktop trial is enough. Follow **[tableau_publish.md](tableau_publish.md)** step by step:

- Connect to Snowflake → `RETAIL_SALES` / `MART`
- Build sheets, five dashboards, and a story
- Save as `tableau/Retail_Sales_Analysis.twbx` (extract) or `.twb` (live) for the submission zip

Cursor is not involved.

## Submission zip (align with the brief)

Final Tableau scope: **Executive** + **Members & churn** dashboards on Tableau Public — see [DASHBOARD_SCOPE.md](DASHBOARD_SCOPE.md).

Include at least:

| Item | Location |
| --- | --- |
| Python ETL | `etl/` |
| Snowflake SQL | `sql/` |
| Source + landing pattern | `source/`, `landing/` |
| DQ + dictionary + notes | `docs/` |
| Deck | `Retail_Sales_Analysis_Onsite_Deck.pptx` |
| Tableau workbook + Public URL | `tableau/*.twbx` and publish link |
| Excel pack (same as Public) | `extracts/tableau_public_pack.xlsx` |
| How to run | `README.md` |

Do **not** zip `.env`, `.venv/`, or `data/`.

If the zip is too large for email, use a shared drive link as the brief describes.

## Troubleshooting

| Issue | What to do |
| --- | --- |
| Snowflake login / MFA | Complete the browser prompt; pipeline cannot click MFA for you. |
| `Missing optional dependency: pandas` | `pip install pyarrow` (already in `requirements.txt`). |
| Tableau cannot connect | Check warehouse `COMPUTE_WH` is running; role `ACCOUNTADMIN` or one with `RETAIL_SALES` usage. |
| Trial Snowflake expired | Re-run is only possible if the account is renewed; otherwise ask for a new trial and run `python -m etl.run_pipeline` once credentials work. |
