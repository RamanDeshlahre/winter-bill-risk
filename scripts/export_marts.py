"""Export the dbt marts from the DuckDB database to CSV files in data/marts/.

The Python analysis and the Tableau dashboard both read these CSVs, so they don't
need a database connection. Run after `dbt build`:  python scripts/export_marts.py
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "winter_bill_risk.duckdb"
OUT = ROOT / "data" / "marts"

TABLES = [
    "dim_households",
    "fct_household_month",
    "mart_dd_winter_balance",
    "mart_household_winter_risk",
    "mart_meter_anomaly_features",
    "mart_daily_usage_by_group",
    "mart_credit_features",
    "int_household_daily_expected",   # view, used for the example-household charts
]

OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DATABASE), read_only=True)
for table in TABLES:
    target = OUT / f"{table}.csv"
    con.execute(f"COPY (SELECT * FROM {table}) TO '{target.as_posix()}' (HEADER, DELIMITER ',')")
    rows = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"exported {table:32s} {rows:>8,} rows")
con.close()
