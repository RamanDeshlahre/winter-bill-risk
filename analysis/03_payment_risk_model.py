"""Part 3 - Early warning for payment difficulty, turned into a fair support policy.

Data: UCI "Default of Credit Card Clients" (30,000 real customers). The question mirrors
an energy collections team's: who is likely to miss next month's payment, and how do
we reach them with help early, without treating any group unfairly?

Design choices
  * Protected characteristics (sex, age, marital status, education) are NOT used as
    model inputs. They are kept aside only to check fairness afterwards.
  * Two models: logistic regression (easy to explain) and gradient boosting (more
    accurate). Both are evaluated on a held-out 20% test set.
  * The output is a support policy with three tiers based on team capacity, not just
    a score.

Inputs (dbt mart): mart_credit_features
Outputs: data/outputs/credit_scored.csv, charts, reports/metrics/payment_risk.json
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, precision_recall_curve,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import (ACCENT, NEUTRAL, OUTPUTS, RANDOM_STATE, load_mart, plt,
                    save_figure, save_metrics)

# Support capacity: the team can proactively contact the top 10% of customers,
# and monitor (e.g. automated reminders, payment-date flexibility) the next 20%.
TIERS = [("1. Proactive support", 0.10), ("2. Monitor", 0.20)]

print("Part 3: payment risk model")
df = load_mart("mart_credit_features")
target = "defaulted_next_month"
protected = ["sex", "age", "age_band", "marital_status", "education"]
behaviour_features = [
    "credit_limit", "months_late_6m", "max_months_late_6m", "months_late_now", "late_trend_3m",
    "consecutive_late_months", "months_paid_in_full_6m", "utilisation_now", "avg_utilisation_6m",
    "bill_growth_3m", "pay_ratio_m1", "avg_pay_ratio_5m", "months_no_payment_5m",
    "pay_status_m1", "pay_status_m2", "pay_status_m3", "pay_status_m4", "pay_status_m5", "pay_status_m6",
]
X = df[behaviour_features].replace([np.inf, -np.inf], np.nan).fillna(0)
X = X.assign(log_credit_limit=np.log(X.credit_limit)).drop(columns="credit_limit")
y = df[target].values

X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
    X, y, df.index, test_size=0.2, stratify=y, random_state=RANDOM_STATE)

models = {
    "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "Gradient boosting": HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0,
        early_stopping=True, validation_fraction=0.15, random_state=RANDOM_STATE),
}
scores, metrics = {}, {"customers": int(len(df)), "default_rate": round(float(y.mean()), 3),
                       "test_customers": int(len(y_test))}
for name, model in models.items():
    model.fit(X_train, y_train)
    p = model.predict_proba(X_test)[:, 1]
    scores[name] = p
    metrics[name] = {"roc_auc": round(roc_auc_score(y_test, p), 3),
                     "pr_auc": round(average_precision_score(y_test, p), 3),
                     "brier": round(brier_score_loss(y_test, p), 4)}

# Does adding protected characteristics improve accuracy? (If barely, leaving them out costs little.)
X_with = X.join(pd.get_dummies(df[["sex", "marital_status", "education"]], drop_first=True).astype(int)).assign(age=df.age)
gb_with = HistGradientBoostingClassifier(**models["Gradient boosting"].get_params()).fit(X_with.loc[idx_train], y_train)
metrics["gradient_boosting_auc_if_protected_features_added"] = round(
    roc_auc_score(y_test, gb_with.predict_proba(X_with.loc[idx_test])[:, 1]), 3)

best = "Gradient boosting"
p_test = scores[best]

# ---------------------------------------------------------------- Tiers on the test set
def assign_tiers(score: np.ndarray) -> np.ndarray:
    pct = pd.Series(score).rank(ascending=False, pct=True).values
    tier = np.full(len(score), "3. Standard", dtype=object)
    upper = 0.0
    for label, share in TIERS:
        tier[(pct > upper) & (pct <= upper + share)] = label
        upper += share
    return tier

test = df.loc[idx_test, protected].copy()
test["score"] = p_test
test["defaulted"] = y_test
test["tier"] = assign_tiers(p_test)
tier_table = test.groupby("tier").agg(customers=("score", "size"), default_rate=("defaulted", "mean"),
                                      defaulters=("defaulted", "sum")).reset_index()
tier_table["share_of_all_defaulters"] = tier_table.defaulters / tier_table.defaulters.sum()
metrics["tiers_test_set"] = tier_table.round(3).to_dict(orient="records")
reached = test.tier != "3. Standard"
metrics["top_30pct_capture_of_defaulters"] = round(float(test.defaulted[reached].sum() / test.defaulted.sum()), 3)

# ---------------------------------------------------------------- Fairness checks
def fairness_by(col: str) -> pd.DataFrame:
    g = test.groupby(col)
    out = pd.DataFrame({
        "customers": g.size(),
        "actual_default_rate": g.defaulted.mean(),
        "share_offered_support": g.apply(lambda d: (d.tier == "1. Proactive support").mean(), include_groups=False),
        # Of the people who did default, what share did we reach (support or monitor)?
        "share_of_defaulters_reached": g.apply(
            lambda d: (d.tier[d.defaulted == 1] != "3. Standard").mean(), include_groups=False),
        # Of the people we offered support, what share actually needed it?
        "precision_of_support_tier": g.apply(
            lambda d: d.defaulted[d.tier == "1. Proactive support"].mean(), include_groups=False),
        "avg_predicted_risk": g.score.mean(),
    })
    out["calibration_gap"] = out.avg_predicted_risk - out.actual_default_rate
    return out.round(3)

fair_sex, fair_age = fairness_by("sex"), fairness_by("age_band")
metrics["fairness_by_sex"] = fair_sex.reset_index().to_dict(orient="records")
metrics["fairness_by_age_band"] = fair_age.reset_index().to_dict(orient="records")
for name, table in [("sex", fair_sex), ("age_band", fair_age)]:
    reach = table.share_of_defaulters_reached
    metrics[f"reach_ratio_min_over_max_{name}"] = round(float(reach.min() / reach.max()), 3)

# ---------------------------------------------------------------- Explainability
imp = permutation_importance(models[best], X_test, y_test, scoring="roc_auc",
                             n_repeats=5, random_state=RANDOM_STATE)
importance = pd.Series(imp.importances_mean, index=X_test.columns).sort_values(ascending=False)
metrics["top_features_permutation_auc_drop"] = importance.head(8).round(4).to_dict()

# ---------------------------------------------------------------- Score everyone (out-of-fold)
oof = cross_val_predict(HistGradientBoostingClassifier(**models[best].get_params()), X, y,
                        cv=StratifiedKFold(5, shuffle=True, random_state=RANDOM_STATE),
                        method="predict_proba")[:, 1]
scored = df[["customer_id"] + protected + ["credit_limit", "months_late_6m", "months_late_now",
                                          "utilisation_now", "avg_pay_ratio_5m", target]].copy()
scored["risk_score"] = oof
scored["support_tier"] = assign_tiers(oof)
scored.to_csv(OUTPUTS / "credit_scored.csv", index=False)

# ---------------------------------------------------------------- Charts
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
for (name, p), colour in zip(scores.items(), [NEUTRAL, ACCENT]):
    fpr, tpr, _ = roc_curve(y_test, p)
    axes[0].plot(fpr, tpr, color=colour, lw=2, label=f"{name} (AUC {metrics[name]['roc_auc']:.2f})")
    prec, rec, _ = precision_recall_curve(y_test, p)
    axes[1].plot(rec, prec, color=colour, lw=2, label=f"{name} (AP {metrics[name]['pr_auc']:.2f})")
axes[0].plot([0, 1], [0, 1], "k--", lw=0.8)
axes[0].set(title="ROC curve (test set)", xlabel="False positive rate", ylabel="True positive rate")
axes[1].axhline(y_test.mean(), color="black", ls="--", lw=0.8)
axes[1].set(title="Precision vs recall (test set)", xlabel="Recall", ylabel="Precision")
for a in axes:
    a.legend(loc="lower right" if a is axes[0] else "upper right", fontsize=8)
save_figure(fig, "07_model_performance")

fig, ax = plt.subplots(figsize=(8, 3.8))
t = tier_table.sort_values("tier")
bars = ax.bar(t.tier, t.default_rate * 100, color=[ACCENT, "#f4a261", "#ced4da"])
for b, (r, s, n) in zip(bars, zip(t.default_rate, t.share_of_all_defaulters, t.customers)):
    ax.text(b.get_x() + b.get_width() / 2, r * 100 + 1.5,
            f"{r:.0%} miss payment\n{s:.0%} of all who do\n({n:,} customers)", ha="center", fontsize=8.5)
ax.axhline(y_test.mean() * 100, color="black", ls="--", lw=0.8)
ax.text(-0.42, y_test.mean() * 100 + 1, f"average {y_test.mean():.0%}", fontsize=8)
ax.set_axisbelow(True)
ax.set_ylim(0, max(t.default_rate) * 100 * 1.45)
ax.set_ylabel("Missed next payment (%)")
ax.set_title("Support tiers: the top 10% are 3x more likely to miss a payment")
save_figure(fig, "08_support_tiers")

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
for ax, table, title in [(axes[0], fair_sex, "By sex"), (axes[1], fair_age, "By age band")]:
    x = np.arange(len(table))
    ax.bar(x - 0.2, table.actual_default_rate * 100, width=0.4, color="#ced4da", label="Actual default rate")
    reached_bars = ax.bar(x + 0.2, table.share_of_defaulters_reached * 100, width=0.4, color=ACCENT,
                          label="Defaulters reached (support or monitor)")
    for b, v in zip(reached_bars, table.share_of_defaulters_reached):
        ax.text(b.get_x() + b.get_width() / 2, v * 100 + 1.5, f"{v:.0%}", ha="center", fontsize=8.5)
    ax.set_ylim(0, 90)
    ax.set_xticks(x, table.index)
    ax.set_title(title)
axes[0].set_ylabel("%")
axes[0].legend(fontsize=8, loc="upper left")
fig.suptitle("Fairness check: does the policy reach people who need help equally across groups?",
             fontweight="bold", y=1.03)
save_figure(fig, "09_fairness_check")

fig, ax = plt.subplots(figsize=(7, 3.8))
top = importance.head(8)[::-1]
ax.barh(top.index, top.values, color="#2a6f97")
ax.set_xlabel("Drop in AUC when the feature is shuffled")
ax.set_title("What drives the risk score")
save_figure(fig, "10_feature_importance")

save_metrics("payment_risk", metrics)
print("  done")
