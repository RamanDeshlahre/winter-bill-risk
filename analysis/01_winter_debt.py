"""Part 1 - How winter turns a fixed Direct Debit into debt, and how early we can spot it.

Inputs (dbt marts): fct_household_month, mart_dd_winter_balance, mart_household_winter_risk
Outputs: charts in reports/figures, metrics in reports/metrics/winter_debt.json,
         data/outputs/energy_debt_triggers.csv (one row per household, for Tableau)
"""
import textwrap

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import (ACCENT, GROUP_COLOURS, GROUP_ORDER, NEUTRAL, OUTPUTS, RANDOM_STATE,
                    load_mart, month_axis, plt, save_figure, save_metrics)

# In-season trigger: contact a customer if, at the end of November, their account is
# behind by at least this share of one monthly Direct Debit.
TRIGGER_MONTH = "2013-11-01"
TRIGGER_BEHIND_SHARE = 0.10

print("Part 1: winter debt")
monthly = load_mart("fct_household_month", ["month_start"])
balance = load_mart("mart_dd_winter_balance", ["month_start"])
risk = load_mart("mart_household_winter_risk")
risk = risk[risk.acorn_group.isin(GROUP_ORDER)].reset_index(drop=True)
balance = balance[balance.household_id.isin(risk.household_id)]
metrics = {"households_analysed": int(len(risk)),
           "households_by_group": risk.acorn_group.value_counts().to_dict()}

# ---------------------------------------------------------------- 1. Seasonality
baseline = monthly[(monthly.month_start >= "2012-10-01") & (monthly.month_start <= "2013-09-30")
                   & monthly.household_id.isin(risk.household_id)]
season = baseline.groupby(["month_start", "acorn_group"]).avg_daily_kwh.mean().unstack()
temps = baseline.groupby("month_start").avg_temp_c.first()

fig, ax = plt.subplots(figsize=(9, 4.5))
for g in GROUP_ORDER:
    ax.plot(season.index, season[g], marker="o", lw=2, color=GROUP_COLOURS[g], label=g)
ax.set_ylabel("Average daily electricity use (kWh)")
ax2 = ax.twinx()
ax2.bar(temps.index, temps.values, width=20, color=NEUTRAL, alpha=0.15, label="Avg temperature")
ax2.set_ylabel("Average temperature (°C)", color=NEUTRAL)
ax2.grid(False)
ax.set_zorder(ax2.get_zorder() + 1)
ax.patch.set_visible(False)
month_axis(ax)
ax.set_title("Every group uses more electricity when it gets cold (Oct 2012 - Sep 2013)")
ax.legend(loc="upper right")
save_figure(fig, "01_seasonal_usage_by_group")

winter_vs_summer = (risk.groupby("acorn_group").baseline_winter_summer_ratio.median() - 1)
metrics["median_winter_uplift_vs_summer"] = winter_vs_summer.round(3).to_dict()

# ---------------------------------------------------------------- 2. Balance path
path = balance.groupby(["month_start", "acorn_group"]).agg(
    mean_balance=("account_balance_gbp", "mean"), share_in_debit=("is_in_debit", "mean")).reset_index()
overall = balance.groupby("month_start").agg(mean_balance=("account_balance_gbp", "mean"),
                                             share_in_debit=("is_in_debit", "mean"),
                                             mean_dd=("direct_debit_gbp", "mean"),
                                             mean_bill=("est_bill_gbp", "mean"))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
path["month_label"] = "End " + path.month_start.dt.strftime("%b")
for g in GROUP_ORDER:
    p = path[path.acorn_group == g]
    axes[0].plot(p.month_label, p.mean_balance, marker="o", lw=2, color=GROUP_COLOURS[g], label=g)
    axes[1].plot(p.month_label, p.share_in_debit * 100, marker="o", lw=2, color=GROUP_COLOURS[g], label=g)
axes[0].axhline(0, color="black", lw=0.8)
axes[0].set_title("Average account balance (£)")
axes[0].set_ylabel("£ (negative = customer owes money)")
axes[1].set_title("Share of households in debit (%)")
axes[1].set_ylim(0, 100)
axes[1].legend()
fig.suptitle("A Direct Debit set in October falls behind as winter bills arrive",
             fontweight="bold", y=1.03)
save_figure(fig, "02_winter_balance_path")

metrics["avg_monthly_direct_debit_gbp"] = round(float(risk.direct_debit_gbp.mean()), 2)
metrics["share_in_debit_by_month"] = {d.strftime("%Y-%m"): round(float(v), 3)
                                      for d, v in overall.share_in_debit.items()}
metrics["mean_balance_by_month_gbp"] = {d.strftime("%Y-%m"): round(float(v), 2)
                                        for d, v in overall.mean_balance.items()}
metrics["median_peak_debt_gbp_by_group"] = risk.groupby("acorn_group").peak_debt_gbp.median().round(2).to_dict()
metrics["at_risk_share_overall"] = round(float(risk.is_at_risk.mean()), 3)
metrics["at_risk_share_by_group"] = risk.groupby("acorn_group").is_at_risk.mean().round(3).to_dict()
metrics["median_winter_bill_change_vs_prior_winter"] = round(float(risk.winter_bill_change_vs_prior_winter.median()), 3)
metrics["median_seasonal_only_peak_debt_gbp"] = round(float(risk.seasonal_only_peak_debt_gbp.median()), 2)

# ---------------------------------------------------------------- 3. Early warning
y = risk.is_at_risk.astype(int).values
features = pd.DataFrame({
    "oct_feb_share": risk.baseline_oct_feb_kwh_share,
    "winter_summer_ratio": risk.baseline_winter_summer_ratio,
    "kwh_per_hdd": risk.baseline_kwh_per_hdd,
    "monthly_cv": risk.baseline_monthly_cv,
    "log_annual_kwh": np.log(risk.baseline_annual_kwh),
    "on_dynamic_tariff": (risk.tariff_group == "dynamic_tou").astype(int),
})
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
october_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
october_score = cross_val_predict(october_model, features, y, cv=cv, method="predict_proba")[:, 1]

behind = (balance.assign(behind_months=-balance.account_balance_gbp / balance.direct_debit_gbp)
          .pivot(index="household_id", columns="month_start", values="behind_months")
          .reindex(risk.household_id))

auc = {
    "Target by area (Adversity = at risk)": roc_auc_score(y, (risk.acorn_group == "Adversity").astype(int)),
    "October prediction from last year's usage": roc_auc_score(y, october_score),
    "Account balance at end of October": roc_auc_score(y, behind[pd.Timestamp("2013-10-01")].values),
    "Account balance at end of November": roc_auc_score(y, behind[pd.Timestamp("2013-11-01")].values),
    "Account balance at end of December": roc_auc_score(y, behind[pd.Timestamp("2013-12-01")].values),
}
metrics["early_warning_auc"] = {k: round(float(v), 3) for k, v in auc.items()}

fig, ax = plt.subplots(figsize=(9, 3.8))
labels = list(auc.keys())
values = list(auc.values())
colours = [NEUTRAL, NEUTRAL, "#9ec1d9", "#2a6f97", "#9ec1d9"]
ypos = np.arange(len(labels))[::-1]
ax.hlines(ypos, 0.5, values, color=colours, lw=3)
ax.scatter(values, ypos, color=colours, s=90, zorder=3)
ax.set_yticks(ypos, labels)
ax.axvline(0.5, color="black", ls="--", lw=0.8)
ax.text(0.505, ypos.min() - 0.55, "random guess (0.5)", fontsize=8)
for yv, v in zip(ypos, values):
    left = v < 0.5
    ax.text(v - 0.015 if left else v + 0.015, yv, f"{v:.2f}", va="center", ha="right" if left else "left")
ax.set_xlim(0.4, 1.02)
ax.set_ylim(ypos.min() - 0.8, ypos.max() + 0.5)
ax.set_xlabel("ROC AUC for spotting at-risk households (1.0 = perfect)")
ax.set_title("Watching the account balance beats predicting in advance")
save_figure(fig, "03_early_warning_accuracy")

# Trigger trade-off at end of November
nov = behind[pd.Timestamp(TRIGGER_MONTH)].values
trade_off = []
for t in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]:
    flagged = nov >= t
    trade_off.append({"behind_share_threshold": t,
                      "share_contacted": flagged.mean(),
                      "precision": y[flagged].mean() if flagged.any() else np.nan,
                      "share_of_at_risk_caught": y[flagged].sum() / y.sum()})
trade_off = pd.DataFrame(trade_off)
trade_off.to_csv(OUTPUTS / "energy_trigger_trade_off.csv", index=False)
chosen = trade_off[trade_off.behind_share_threshold == TRIGGER_BEHIND_SHARE].iloc[0]
metrics["recommended_trigger"] = {
    "rule": f"Contact if, at end of November, the account is behind by >= {TRIGGER_BEHIND_SHARE:.0%} of a monthly Direct Debit",
    "share_contacted": round(float(chosen.share_contacted), 3),
    "precision": round(float(chosen.precision), 3),
    "share_of_at_risk_caught": round(float(chosen.share_of_at_risk_caught), 3),
}

# ---------------------------------------------------------------- 4. Support segments
triggers = risk[["household_id", "acorn_group", "tariff_group", "direct_debit_gbp",
                 "peak_debt_gbp", "peak_debt_in_months_of_dd", "is_at_risk"]].copy()
triggers["behind_months_end_nov"] = nov
triggers["balance_end_nov_gbp"] = -nov * triggers.direct_debit_gbp
triggers["october_risk_score"] = october_score
triggers["triggered"] = nov >= TRIGGER_BEHIND_SHARE
adversity = triggers.acorn_group == "Adversity"
triggers["support_segment"] = np.select(
    [triggers.triggered & adversity, triggers.triggered & ~adversity, ~triggers.triggered & adversity],
    ["1. Priority support", "2. Direct Debit review", "3. Light-touch information"],
    "4. No action")
actions = {
    "1. Priority support": "Personal call: offer a payment plan spread over spring, check eligibility for support schemes, record any vulnerability.",
    "2. Direct Debit review": "Automated message with an updated Direct Debit suggestion and a simple way to adjust it.",
    "3. Light-touch information": "Winter bill tips and where to get help - no change needed yet.",
    "4. No action": "Standard service.",
}
triggers["recommended_action"] = triggers.support_segment.map(actions)
triggers.to_csv(OUTPUTS / "energy_debt_triggers.csv", index=False)

segment_summary = triggers.groupby("support_segment").agg(
    households=("household_id", "size"),
    at_risk_rate=("is_at_risk", "mean"),
    median_peak_debt_gbp=("peak_debt_gbp", "median")).round(3)
metrics["support_segments"] = segment_summary.reset_index().to_dict(orient="records")

fig, ax = plt.subplots(figsize=(8, 3.6))
seg = segment_summary.sort_index()
bars = ax.bar([textwrap.fill(label, 16) for label in seg.index], seg.households,
              color=[ACCENT, "#2a6f97", "#f4a261", "#ced4da"])
for b, (n, r) in zip(bars, zip(seg.households, seg.at_risk_rate)):
    ax.text(b.get_x() + b.get_width() / 2, n + 6, f"{n} homes\n{r:.0%} at risk", ha="center", va="bottom", fontsize=9)
ax.set_ylabel("Households")
ax.set_ylim(0, seg.households.max() * 1.3)
ax.set_title("End-of-November trigger, split by area: who gets which kind of help")
ax.tick_params(axis="x", labelsize=9)
ax.set_axisbelow(True)
save_figure(fig, "04_support_segments")

save_metrics("winter_debt", metrics)
print("  done")
