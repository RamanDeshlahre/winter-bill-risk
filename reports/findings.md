# Findings: Winter Bill Risk

**Question:** which households are likely to fall into energy debt this winter, why, and what should a supplier do about it?

**Data:** 600 London households' smart meter readings (Nov 2011 - Feb 2014, Low Carbon London trial), daily London weather, and 30,000 credit customers' payment histories (UCI). Bills are re-priced at the Ofgem price cap for 1 Oct - 31 Dec 2026 (electricity: 26.32p/kWh, 54.83p/day standing charge, GB Direct Debit average).

---

## 1. Winter turns a fixed Direct Debit into debt

Suppliers usually set a fixed monthly Direct Debit from the last 12 months of usage. I simulated this for 545 households with near-complete data: the Direct Debit was set from Oct 2012 - Sep 2013 usage, and their account balance was tracked through winter 2013/14.

| | Affluent | Comfortable | Adversity |
|---|---|---|---|
| Households | 265 | 145 | 135 |
| Winter use vs summer (median) | +41% | +35% | +28% |
| Median peak debt | £37 | £21 | £21 |
| At risk (≥ ½ month behind) | 36% | 27% | 24% |

- The average Direct Debit is **£113/month** (electricity only).
- The share of households in debit rises from 45% at the end of October to **80% at the end of January**, when the average balance is **-£41**.
- Winter 2013/14 bills were 3% *lower* than the winter before (a milder winter). Even so, most households fell behind: the debt comes from **seasonality**, not unusual weather.

**So what:** winter debit is normal and predictable for most customers. The collections challenge is telling apart *temporary seasonal debit* from *customers who are genuinely struggling*.

## 2. When can we tell who will fall behind?

I compared five ways of identifying the 31% of households who end up at least half a month behind (ROC AUC, where 0.5 = random and 1.0 = perfect):

| Method | AUC |
|---|---|
| Treat "Adversity" areas as at-risk | **0.46** (worse than random) |
| October prediction from last year's usage (logistic regression, 5-fold CV) | 0.64 |
| Account balance at end of October | 0.73 |
| **Account balance at end of November** | **0.86** |
| Account balance at end of December | 0.95 |

- **Area is a poor proxy for risk.** In this data, homes in wealthier areas build *larger* winter debts, because they use more electricity and it rises more in winter. Area-based targeting would miss most people who fall behind and contact many who don't.
- **Prediction in advance is limited.** Next winter's usage depends on weather and life changes that last year's data can't see.
- **Monitoring beats prediction.** By the end of November the account itself tells us most of what we need to know, and there are still 2-3 months to act before the debt peaks. December is more accurate but leaves less time to help.

**Recommended trigger:** at the end of November, contact customers whose account is behind by ≥10% of a monthly payment.

| Threshold (end Nov) | Customers contacted | Of those, truly at risk | At-risk customers caught |
|---|---|---|---|
| ≥0% behind | 59% | 46% | 88% |
| **≥10% behind** | **33%** | **71%** | **77%** |
| ≥20% behind | 19% | 92% | 55% |

## 3. A support policy, not just a score

The trigger decides *who* to contact; area (a vulnerability signal) only changes *how*:

| Segment | Households | At risk | Action |
|---|---|---|---|
| 1. Priority support (triggered, Adversity area) | 43 | 60% | Personal call, payment plan into spring, check support-scheme eligibility, record vulnerability |
| 2. Direct Debit review (triggered, other areas) | 139 | 75% | Automated message suggesting an updated amount |
| 3. Light-touch information (not triggered, Adversity) | 92 | 8% | Winter tips and where to get help |
| 4. No action | 271 | 11% | Standard service |

## 4. Unusual meter readings (fraud, faults and empty homes)

There are no confirmed fraud labels in public data, so this is a **screening** exercise, not a fraud model. Each household's daily usage was compared with what the weather predicts for that home, then screened with:

- **Rules:** 14+ days at near-zero use; 28+ days below 35% of expected; 14+ days above 2.5x expected; 14+ days with no data.
- **An Isolation Forest** (unsupervised machine learning) ranking how unusual each household's overall pattern is. The top 3% are flagged.

**Result:** 34 of 597 households (5.7%) go to a ranked review list. 14 were flagged by both methods, and 4 by the model alone (cases the rules would miss).

| Likely explanation | Households |
|---|---|
| Sudden drop to near zero | 12 |
| Sustained drop vs weather | 8 |
| Likely empty home | 5 |
| Communications fault | 4 |
| Unusual pattern (model only) | 4 |
| Sustained increase | 1 |

**So what:** most flags have innocent explanations (holidays, moving out, faulty meters). The process should check the least intrusive explanation first, and only consider a meter inspection afterwards. That matters for customer trust and for vulnerable customers.

## 5. Payment-risk early warning (30,000 real customers)

- **Models** (80/20 stratified split): gradient boosting reaches test AUC **0.776** (PR-AUC 0.55) and logistic regression 0.748. The baseline default rate is 22%.
- **Protected characteristics are excluded.** Sex, age, marital status and education are not model inputs. Adding them would raise AUC by only **0.001**, so leaving them out costs almost nothing.
- **Strongest signals:** being late right now, the number of late months in the last six, credit limit, and how much of the limit is used.

**Capacity-based tiers** (test set):

| Tier | Customers | Miss next payment | Share of all who miss |
|---|---|---|---|
| 1. Proactive support (top 10%) | 600 | 69% | 31% |
| 2. Monitor (next 20%) | 1,200 | 34% | 31% |
| 3. Standard | 4,200 | 12% | 38% |

**Fairness:** I compared how many of the people who *did* miss a payment were reached (support or monitor tiers) in each group.

- **By sex:** women 61.5%, men 63.1% (ratio 0.98). Predicted and actual default rates agree within 1 point in both groups.
- **By age:** 21-29: 66% · 30-39: 62% · 40-49: 58% · 50+: 60% (ratio 0.89). The 40-49 gap is worth monitoring as the policy runs.

## 6. Bonus: did the dynamic tariff change usage?

Using a difference-in-differences design (the same households, Jul-Dec 2012 vs Jul-Dec 2013, compared with standard-tariff homes), households on the dynamic time-of-use tariff used **5.0% less electricity** (95% bootstrap interval: -8.8% to -1.4%; 111 dynamic-tariff households). By group the estimates are -7% (Affluent), -4% (Comfortable) and -5% (Adversity), but each group's interval is wide.

## Limitations

See [`docs/methodology.md`](../docs/methodology.md). The main ones are: electricity only (no gas, so winter bills are understated); 2011-14 usage re-priced at 2026 rates; a London-only sample of 600 homes; a lending dataset standing in for energy payment data; and no confirmed fraud labels.
