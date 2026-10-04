"""Check that the dbt marts on your machine match the reference numbers produced when
this project was first built. If everything matches, the SQL and the analysis agree.

Run after exporting the marts:  python scripts/check_reconciliation.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
expected = json.loads((Path(__file__).parent / "expected_reconciliation.json").read_text())

actual = {f"rows.{name}": len(pd.read_csv(MARTS / f"{name}.csv")) for name in expected["rows"]}
risk = pd.read_csv(MARTS / "mart_household_winter_risk.csv")
months = pd.read_csv(MARTS / "fct_household_month.csv")
credit = pd.read_csv(MARTS / "mart_credit_features.csv")
actual.update({
    "values.sum_peak_debt_gbp": round(risk.peak_debt_gbp.sum(), 2),
    "values.mean_direct_debit_gbp": round(risk.direct_debit_gbp.mean(), 2),
    "values.households_at_risk": int(risk.is_at_risk.astype(str).str.lower().eq("true").sum()),
    "values.sum_monthly_bills_gbp": round(months.est_bill_gbp.sum(), 2),
    "values.sum_months_late_6m": int(credit.months_late_6m.sum()),
    "values.mean_avg_pay_ratio_5m": round(credit.avg_pay_ratio_5m.mean(), 4),
})

flat_expected = {f"rows.{k}": v for k, v in expected["rows"].items()}
flat_expected.update({f"values.{k}": v for k, v in expected["values"].items()})

failures = 0
for key, exp in flat_expected.items():
    got = actual[key]
    ok = abs(got - exp) <= max(0.01, abs(exp) * 1e-6)
    failures += not ok
    print(f"{'OK  ' if ok else 'DIFF'} {key:40s} expected {exp:>14} got {got:>14}")
print("\nAll checks passed." if failures == 0 else f"\n{failures} check(s) differ - investigate before trusting results.")
