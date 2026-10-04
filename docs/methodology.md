# Methodology, assumptions and limitations

## Pipeline

1. **Staging (dbt):** read the raw CSVs, rename columns, set types, and flag complete days (all 48 half-hour readings). Fix the weather timezone issue: timestamps are UTC, so British Summer Time days are stored as 23:00 on the previous day. Adding one hour before converting to a date fixes 428 rows.
2. **Intermediate (dbt):** for each household, fit `daily kWh = a + b × heating degree days` (base 15.5°C, least squares over the household's full history). Compare actual with expected usage, plus a 14-day rolling average of that ratio.
3. **Marts (dbt):** household-month bills, the Direct Debit simulation, household winter-risk features, anomaly signals, daily usage by group, and credit features.
4. **Export:** marts are written to CSV (`scripts/export_marts.py`) and checked against reference totals (`scripts/check_reconciliation.py`).
5. **Analysis (Python):** four scripts produce charts, JSON metrics and Tableau-ready outputs.

## Key definitions

| Term | Definition |
|---|---|
| Complete day | 48 half-hourly readings and a non-null total. Partial days (~1%) are excluded from usage averages. |
| Monthly bill | Average daily kWh on complete days × days in month × 26.32p, plus 54.83p × days in month |
| Direct Debit | Total of the 12 monthly bills from Oct 2012 - Sep 2013, divided by 12 |
| Eligible household | 12 baseline months and 5 winter months present, with ≥90% complete days in each window |
| Account balance | Running total of (Direct Debit − bill) from October 2013. Negative = in debit. |
| Peak debt | Most negative month-end balance, Oct 2013 - Feb 2014 |
| At risk | Peak debt ≥ 0.5 × monthly Direct Debit |
| Heating degree days (HDD) | max(15.5 − daily mean temperature, 0) |

## Modelling choices

- **Energy early warning:** logistic regression on features known in October (winter share of usage, winter/summer ratio, kWh per HDD, monthly variability, annual kWh, tariff), evaluated with 5-fold stratified cross-validation. The in-season triggers are simple thresholds on the balance divided by the Direct Debit, which makes them easy to explain and run.
- **Anomalies:** rules plus an Isolation Forest (500 trees, standardised features, top 3% flagged). Only households with ≥180 days of data are screened.
- **Payment risk:** 80/20 stratified split. Logistic regression (scaled) and histogram gradient boosting with early stopping. Permutation importance on the test set. Tier thresholds are capacity-based (top 10%, next 20%). Tableau scores come from 5-fold out-of-fold predictions, so no customer is scored by a model that saw them in training.
- **Fairness:** the share of actual defaulters reached (equal opportunity), the share offered support, support-tier precision, and calibration gap, by sex and age band. Protected attributes are excluded from the model and used only for this check.
- **Tariff effect:** difference-in-differences on log mean daily kWh, Jul-Dec 2012 vs Jul-Dec 2013, using households with ≥5 of 6 months at ≥80% coverage in both periods. 95% intervals from 2,000 bootstrap resamples.

## Limitations (and what I'd do next)

1. **Electricity only.** Most London homes heat with gas, so real winter bills rise much more. *Next:* add gas using typical consumption profiles, or use a dual-fuel dataset.
2. **Old usage, new prices.** 2011-14 behaviour is priced at 2026 rates. Usage habits (LED lighting, heat pumps, EVs) have changed since then. Standing charges and unit rates also vary by region; the GB average is used.
3. **Small, London-only sample.** 600 households, with Affluent homes over-represented (298). Results are reported by group for this reason.
4. **Payment data is a stand-in.** The credit dataset is from Taiwanese card customers in 2005, not energy customers. The *method* transfers; the specific numbers don't.
5. **No fraud labels.** The anomaly work is screening, not detection. It can't measure precision. *Next:* validate against meter-inspection outcomes.
6. **Simple expected-usage model.** A straight line against heating degree days fits poorly for homes with electric heating or irregular occupancy (median R² is low). *Next:* a change-point or seasonal model per household.
7. **Tariff trial selection.** Dynamic-tariff households were recruited, not randomly assigned. Difference-in-differences removes fixed differences between the groups but assumes they would otherwise have followed parallel trends.
8. **Daily data only.** Load shifting between hours can't be measured. *Next:* half-hourly blocks for the dynamic-tariff households.
