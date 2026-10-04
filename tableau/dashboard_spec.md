# Tableau Public dashboard: design spec

Build in **Tableau Public (Mac)**. After running `make all`, connect to these CSVs:

| Data source | File | Grain |
|---|---|---|
| Balance | `data/marts/mart_dd_winter_balance.csv` | household × month |
| Triggers | `data/outputs/energy_debt_triggers.csv` | household |
| Trade-off | `data/outputs/energy_trigger_trade_off.csv` | threshold |
| Daily usage | `data/marts/mart_daily_usage_by_group.csv` | day × group × tariff |
| Review queue | `data/outputs/meter_review_queue.csv` | flagged household |
| Credit | `data/outputs/credit_scored.csv` | customer |

**Style:** use the same colours as the Python charts: Affluent `#2a6f97`, Comfortable `#8ab17d`, Adversity `#e76f51`, neutral `#6c757d`. Use one font throughout, and put a footnote on every dashboard: *"Electricity only. 2011-14 usage priced at Oct-Dec 2026 Ofgem cap rates."*

---

## Dashboard 1: Winter Debt Monitor (for the Collections team)

**Top row, KPI cards**
- Households monitored = `COUNTD([Household Id])`
- Average Direct Debit = `AVG([Direct Debit Gbp])`
- % in debit (end of selected month) = `AVG(IIF([Is In Debit], 1, 0))`
- % triggered at end of November = `AVG(IIF([Triggered], 1, 0))` (Triggers source)

**Middle left: balance path.** Line chart of `AVG([Account Balance Gbp])` by `MONTH([Month Start])`, colour = Acorn Group, with a reference line at £0.

**Middle right: usage vs temperature.** Dual axis: `AVG([Avg Daily Kwh])` (line, coloured by Acorn Group) and `AVG([Temp Mean C])` (bars, light grey) by week.

**Bottom left: trigger trade-off.** Line chart from the Trade-off source: Share Contacted and Share Of At Risk Caught against Behind Share Threshold. Highlight 0.10 as the recommended threshold.

**Bottom right: support segments.** Bar chart of households by Support Segment, with a tooltip showing the recommended action.

**Filters:** Acorn Group, Tariff Group, Support Segment.
**Action:** clicking a segment filters a hidden household table listing ID, balance at end of November, peak debt and action.

## Dashboard 2: Meter Review Queue (for the Revenue Protection team)

- **Table:** Review Rank, Household Id, Explanation Category, Reasons, Likely Explanation, Mean Daily Kwh. Sorted by rank.
- **Bar:** count of households by Explanation Category.
- **Highlight table:** rules triggered by household (near-zero / drop / rise / data gap).
- **Text box:** *"A flag is a reason to check, not proof. Confirm occupancy and meter health first."*

## Dashboard 3: Payment Risk & Fairness (for Risk and Compliance)

- **Tier bars:** customers and actual default rate by Support Tier.
- **Calibration:** bin `[Risk Score]` into 10 groups (`ROUND([Risk Score]*10)/10`), and plot average score against average `[Defaulted Next Month]` with a diagonal reference line.
- **Fairness:** for defaulters only (filter Defaulted = 1), the share reached = `AVG(IIF([Support Tier] != "3. Standard", 1, 0))` by Sex and by Age Band.
- **Parameter:** "Support capacity %" (5-30%) with the calculated field `IIF(RANK_PERCENTILE(SUM([Risk Score])) >= 1 - [Support capacity %], "Support", "Other")`. This lets a manager see how capacity changes reach.

## Publishing

1. In Tableau Public: **File → Save to Tableau Public**.
2. Copy the public link into the README (under "Key findings") and onto your CV.
3. Take a screenshot of each dashboard, save it to `reports/figures/tableau_*.png`, and embed it in the README.
