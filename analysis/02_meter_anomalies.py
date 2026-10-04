"""Part 2 - Unusual meter readings: a prioritised review list (possible fraud, faults, empty homes).

Two methods are combined:
  * Transparent rules that an operations team can understand and challenge.
  * An Isolation Forest (unsupervised machine learning) that scores how unusual each
    household's overall pattern is, to catch cases the rules don't describe.
There are no confirmed fraud labels in this data, so nothing here is "proof" - the output
is a list of homes worth a closer look, each with the most likely explanation.

Inputs (dbt marts): mart_meter_anomaly_features, int_household_daily_expected
Outputs: data/outputs/meter_review_queue.csv, charts, reports/metrics/meter_anomalies.json
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from common import (ACCENT, NEUTRAL, OUTPUTS, RANDOM_STATE, load_mart, plt,
                    save_figure, save_metrics)

print("Part 2: meter anomalies")
features = load_mart("mart_meter_anomaly_features")
features = features[features.days_with_data >= 180].reset_index(drop=True)  # need enough history

# ---------------------------------------------------------------- 1. Rules
rules = {
    "near_zero_14d": (features.longest_near_zero_run_days >= 14,
                      "14+ days in a row at almost zero usage"),
    "sustained_drop_28d": (features.longest_sustained_low_run_days >= 28,
                           "Usage under 35% of the weather-adjusted expected level for 28+ days"),
    "sustained_rise_14d": (features.longest_sustained_high_run_days >= 14,
                           "Usage over 2.5x the expected level for 14+ days"),
    "data_gap_14d": (features.longest_data_gap_days >= 14,
                     "No readings received for 14+ days in a row"),
}
for code, (mask, _) in rules.items():
    features[f"rule_{code}"] = mask
rule_cols = [f"rule_{c}" for c in rules]
features["rules_triggered"] = features[rule_cols].sum(axis=1)

# ---------------------------------------------------------------- 2. Isolation Forest
model_cols = ["mean_daily_kwh", "daily_kwh_cv", "share_near_zero_days", "mean_peak_halfhour_kwh",
              "fit_kwh_per_hdd", "fit_r2", "min_usage_ratio_14d", "max_usage_ratio_14d",
              "longest_near_zero_run_days", "longest_sustained_low_run_days",
              "longest_sustained_high_run_days", "longest_data_gap_days", "share_partial_days"]
X = features[model_cols].copy()
X["mean_daily_kwh"] = np.log1p(X.mean_daily_kwh)       # usage is very skewed
X["max_usage_ratio_14d"] = np.log1p(X.max_usage_ratio_14d)
X = StandardScaler().fit_transform(X)
forest = IsolationForest(n_estimators=500, contamination="auto", random_state=RANDOM_STATE).fit(X)
# score_samples is higher for normal points, so flip it: higher = more unusual
raw = -forest.score_samples(X)
features["unusualness_percentile"] = pd.Series(raw).rank(pct=True).values
features["model_flag"] = features.unusualness_percentile >= 0.97   # top 3%

# ---------------------------------------------------------------- 3. Review queue
def likely_explanation(row):
    """Return (category, explanation) for a flagged household. Order matters: the most
    specific, least alarming explanation is checked first."""
    if row.rule_data_gap_14d and row.rules_triggered == 1:
        return ("Communications fault",
                "Meter stopped sending data. Check the meter connection before anything else.")
    if row.rule_near_zero_14d and row.share_near_zero_days > 0.10:
        return ("Likely empty home",
                "Long periods with almost no use (holidays, moved out). Confirm occupancy first.")
    if row.rule_near_zero_14d:
        return ("Sudden drop to near zero",
                "Could be an empty home, a meter fault or supply interference. Check recent account contact first.")
    if row.rule_sustained_drop_28d:
        return ("Sustained drop vs weather",
                "Usage well below what the weather predicts for a month or more: change of occupants, "
                "faulty meter, or possible meter bypass. Compare with past readings, then consider a meter check.")
    if row.rule_sustained_rise_14d:
        return ("Sustained increase",
                "New heating, an EV or more people at home. Bill-shock risk: offer a Direct Debit review.")
    return ("Unusual pattern (model only)",
            "No single rule fired, but the overall pattern is unusual compared with other homes. Analyst review.")

queue = features[(features.rules_triggered > 0) | features.model_flag].copy()
explained = queue.apply(likely_explanation, axis=1, result_type="expand")
queue["explanation_category"] = explained[0]
queue["likely_explanation"] = explained[1]
queue["reasons"] = queue.apply(
    lambda r: "; ".join(text for code, (_, text) in rules.items() if r[f"rule_{code}"])
    or "Isolation Forest: top 3% most unusual pattern", axis=1)
queue["priority_score"] = queue.rules_triggered + queue.unusualness_percentile
queue = queue.sort_values("priority_score", ascending=False)
queue.insert(0, "review_rank", range(1, len(queue) + 1))
out_cols = ["review_rank", "household_id", "acorn_group", "tariff_group", "priority_score",
            "unusualness_percentile", "rules_triggered", "reasons", "explanation_category", "likely_explanation",
            "mean_daily_kwh", "longest_near_zero_run_days", "longest_sustained_low_run_days",
            "longest_sustained_high_run_days", "longest_data_gap_days"]
queue[out_cols].to_csv(OUTPUTS / "meter_review_queue.csv", index=False)
features.to_csv(OUTPUTS / "meter_anomaly_scores.csv", index=False)

metrics = {
    "households_screened": int(len(features)),
    "households_in_review_queue": int(len(queue)),
    "share_in_review_queue": round(len(queue) / len(features), 3),
    "rule_counts": {c: int(features[f"rule_{c}"].sum()) for c in rules},
    "flagged_by_model_only": int((features.model_flag & (features.rules_triggered == 0)).sum()),
    "flagged_by_rules_and_model": int((features.model_flag & (features.rules_triggered > 0)).sum()),
    "queue_by_explanation": queue.explanation_category.value_counts().to_dict(),
    "queue_by_acorn_group": queue.acorn_group.value_counts().to_dict(),
}

# ---------------------------------------------------------------- 4. Charts
fig, ax = plt.subplots(figsize=(8, 4.5))
normal = features[(features.rules_triggered == 0) & ~features.model_flag]
ax.scatter(normal.mean_daily_kwh, normal.unusualness_percentile, s=12, color=NEUTRAL, alpha=0.4, label="Not flagged")
ruled = features[features.rules_triggered > 0]
ax.scatter(ruled.mean_daily_kwh, ruled.unusualness_percentile, s=30, color=ACCENT, label="Flagged by a rule")
model_only = features[features.model_flag & (features.rules_triggered == 0)]
ax.scatter(model_only.mean_daily_kwh, model_only.unusualness_percentile, s=40, marker="D",
           color="#2a6f97", label="Flagged by model only")
ax.axhline(0.97, color="black", ls="--", lw=0.8)
ax.set_xscale("log")
ax.set_xlabel("Average daily usage (kWh, log scale)")
ax.set_ylabel("Unusualness percentile (Isolation Forest)")
ax.set_title(f"{len(queue)} of {len(features)} homes go to the review list")
ax.legend(loc="lower right")
save_figure(fig, "05_anomaly_screening")

# Example households: one per main explanation type
daily = load_mart("int_household_daily_expected", ["reading_date"])
examples = []
for rule in ["rule_near_zero_14d", "rule_sustained_drop_28d", "rule_sustained_rise_14d"]:
    cand = queue[queue[rule]].sort_values("priority_score", ascending=False)
    cand = cand[~cand.household_id.isin(examples)]
    if len(cand):
        examples.append(cand.household_id.iloc[0])
titles = {"rule_near_zero_14d": "Long run of near-zero usage",
          "rule_sustained_drop_28d": "Sustained drop vs expected",
          "rule_sustained_rise_14d": "Sustained rise vs expected"}
fig, axes = plt.subplots(len(examples), 1, figsize=(10, 2.6 * len(examples)), sharex=True)
axes = np.atleast_1d(axes)
for ax, hid, rule in zip(axes, examples, list(titles)[:len(examples)]):
    d = daily[daily.household_id == hid].set_index("reading_date").sort_index()
    ax.plot(d.index, d.kwh_total, color=NEUTRAL, lw=0.6, alpha=0.6, label="Actual (daily)")
    ax.plot(d.index, d.expected_kwh, color="#2a6f97", lw=1.5, label="Expected for the weather")
    ax.plot(d.index, d.kwh_total.rolling(14, min_periods=7).mean(), color=ACCENT, lw=1.8, label="Actual (14-day avg)")
    ax.set_title(f"{titles[rule]}  -  household {hid}", fontsize=10, loc="left")
    ax.set_ylabel("kWh / day")
axes[0].legend(ncol=3, loc="upper right", fontsize=8)
fig.suptitle("What the review list looks like: three example households", fontweight="bold", y=1.0)
fig.tight_layout()
save_figure(fig, "06_anomaly_examples")
metrics["example_households"] = examples

save_metrics("meter_anomalies", metrics)
print("  done")
