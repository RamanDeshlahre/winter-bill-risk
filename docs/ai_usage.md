# How AI was used in this project

**Where AI helped**
- Drafting dbt SQL models, data tests and Python analysis scripts.
- Suggesting chart layouts and checking explanations were written in plain English.
- Reviewing the approach for gaps (for example, adding the fairness check and the reconciliation script).

**How I checked the work**
- **Data tests:** 36 dbt tests (unique keys, accepted values, no missing weather days, balances reconcile to the penny).
- **Independent reconciliation:** `scripts/check_reconciliation.py` compares row counts and totals from the dbt pipeline with an independent pandas calculation of the same logic.
- **Manual inspection:** reading the raw data for flagged households and plotting examples (`reports/figures/06_anomaly_examples.png`) to confirm the flags make sense.
- **Sense checks:** comparing results with known facts (e.g. winter usage above summer for every group; default rate of 22% matching the dataset documentation).

**A finding I made by checking, not trusting:** the weather data's UTC timestamps shifted every British Summer Time day back by one day. This was found by investigating 3 duplicate dates, and is now fixed and tested.

**What I would not hand to AI:** decisions about how customers are treated (the support policy, what counts as "fair", and wording that avoids accusing anyone of fraud). These were reasoned through and documented by me.
