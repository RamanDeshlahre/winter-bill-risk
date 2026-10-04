# Data sources

Raw data is **not** included in this repository. Download it and place the files as shown.

| File | Source | Put it in |
|---|---|---|
| `block_0.csv`, `block_1.csv`, `block_3.csv`, `block_4.csv`, `block_5.csv`, `block_10.csv` (Affluent) · `block_62.csv`, `block_63.csv`, `block_64.csv` (Comfortable) · `block_78.csv`, `block_79.csv`, `block_106.csv` (Adversity) | Kaggle, "Smart meters in London" (jeanmidev), folder `daily_dataset` | `data/raw/smart_meters/` |
| `informations_households.csv` | Same Kaggle dataset | `data/raw/smart_meters/` |
| `weather_daily_darksky.csv` | Same Kaggle dataset | `data/raw/smart_meters/` |
| `UCI_Credit_Card.csv` | UCI Machine Learning Repository, "Default of Credit Card Clients" (also mirrored on Kaggle) | `data/raw/credit/` |

**Why these blocks?** The households file is sorted by Acorn group, so block numbers map to groups: 0-42 Affluent, 44-73 Comfortable, 75-109 Adversity. Blocks were picked to give a balanced comparison and as many dynamic-tariff homes as possible.

## Original sources and credits

- **Smart meter data:** UK Power Networks, Low Carbon London project. Energy readings for 5,567 London households, Nov 2011 - Feb 2014, originally published on the London Datastore. Check the source pages for licence terms.
- **Weather:** Dark Sky API data, as bundled in the Kaggle dataset.
- **Credit data:** Yeh, I. C., & Lien, C. H. (2009). *The comparisons of data mining techniques for the predictive accuracy of probability of default of credit card clients.* Expert Systems with Applications, 36(2), 2473-2480. Available from the UCI Machine Learning Repository.
- **Prices:** Ofgem, energy price cap 1 October - 31 December 2026: electricity 26.32p/kWh and 54.83p/day standing charge (GB average, Direct Debit, VAT removed for this period).
