"""Part 4 (bonus) - Did households on the dynamic time-of-use tariff change how much
electricity they used?

In 2013 about 1,100 trial households received day-ahead High / Low / Normal price
signals. We compare the SAME households before (Jul-Dec 2012) and during (Jul-Dec 2013)
the trial, against standard-tariff households over the same months. This
"difference-in-differences" removes anything that affected everyone (like weather).

Limitation: this uses DAILY totals, so it measures whether total use changed, not
whether people shifted use between hours. Load shifting needs the half-hourly data
(a natural extension).

Inputs (dbt mart): fct_household_month
Outputs: reports/figures/11_smart_tariff_response.png, reports/metrics/smart_tariff.json
"""
import numpy as np
import pandas as pd

from common import (ACCENT, GROUP_ORDER, NEUTRAL, RANDOM_STATE, load_mart, plt,
                    save_figure, save_metrics)

PRE = ("2012-07-01", "2012-12-01")
TRIAL = ("2013-07-01", "2013-12-01")
MIN_GOOD_MONTHS = 5      # of the 6 months in each period
MIN_COVERAGE = 0.8       # a "good" month has 80%+ complete days
BOOTSTRAPS = 2000

print("Part 4: smart tariff response")
monthly = load_mart("fct_household_month", ["month_start"])
monthly = monthly[monthly.acorn_group.isin(GROUP_ORDER) & (monthly.coverage >= MIN_COVERAGE)]

def period_usage(start, end, label):
    m = monthly[(monthly.month_start >= start) & (monthly.month_start <= end)]
    g = m.groupby(["household_id", "acorn_group", "tariff_group"]).agg(
        months=("month_start", "size"), kwh=("avg_daily_kwh", "mean")).reset_index()
    return g[g.months >= MIN_GOOD_MONTHS].rename(columns={"kwh": f"kwh_{label}"}).drop(columns="months")

panel = period_usage(*PRE, "pre").merge(period_usage(*TRIAL, "trial"),
                                        on=["household_id", "acorn_group", "tariff_group"])
panel = panel[(panel.kwh_pre > 0) & (panel.kwh_trial > 0)]
panel["log_change"] = np.log(panel.kwh_trial / panel.kwh_pre)

rng = np.random.default_rng(RANDOM_STATE)

def did(data: pd.DataFrame) -> dict:
    tou = data[data.tariff_group == "dynamic_tou"].log_change.values
    std = data[data.tariff_group == "standard_flat"].log_change.values
    estimate = tou.mean() - std.mean()
    boot = [rng.choice(tou, len(tou)).mean() - rng.choice(std, len(std)).mean() for _ in range(BOOTSTRAPS)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    to_pct = lambda v: (np.exp(v) - 1) * 100
    return {"households_tou": int(len(tou)), "households_standard": int(len(std)),
            "effect_pct": round(to_pct(estimate), 2),
            "ci95_low_pct": round(to_pct(lo), 2), "ci95_high_pct": round(to_pct(hi), 2),
            "standard_group_change_pct": round(to_pct(std.mean()), 2)}

results = {"All households": did(panel)}
for g in GROUP_ORDER:
    results[g] = did(panel[panel.acorn_group == g])

fig, ax = plt.subplots(figsize=(8, 3.8))
labels = list(results)
effects = [results[k]["effect_pct"] for k in labels]
lows = [results[k]["effect_pct"] - results[k]["ci95_low_pct"] for k in labels]
highs = [results[k]["ci95_high_pct"] - results[k]["effect_pct"] for k in labels]
colours = [ACCENT] + [NEUTRAL] * len(GROUP_ORDER)
ax.barh(labels[::-1], effects[::-1], xerr=[lows[::-1], highs[::-1]], color=colours[::-1], capsize=4)
ax.axvline(0, color="black", lw=0.8)
for i, k in enumerate(labels[::-1]):
    n = results[k]["households_tou"]
    ax.text(0.02, i + 0.28, f"{n} on dynamic tariff", transform=ax.get_yaxis_transform(), fontsize=8, color=NEUTRAL)
ax.set_xlabel("Change in daily usage vs standard-tariff homes (%), with 95% interval")
ax.set_title("Did the dynamic tariff change total electricity use? (Jul-Dec 2013 vs 2012)")
save_figure(fig, "11_smart_tariff_response")

save_metrics("smart_tariff", results)
for k, v in results.items():
    print(f"  {k:15s} effect {v['effect_pct']:+.1f}%  (95% CI {v['ci95_low_pct']:+.1f}% to {v['ci95_high_pct']:+.1f}%)  n_tou={v['households_tou']}")
print("  done")
