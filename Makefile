# Run the whole project with: make all
# (Activate the virtual environment first: source .venv/bin/activate)

.PHONY: setup build export check analyse all clean

setup:          ## install Python packages
	pip install -r requirements.txt

build:          ## run dbt: build all models and run all data tests
	cd dbt && dbt build --profiles-dir .

export:         ## copy the dbt marts to CSV for Python and Tableau
	python scripts/export_marts.py

check:          ## confirm results match the reference numbers
	python scripts/check_reconciliation.py

analyse:        ## run the four analyses (charts + metrics + Tableau outputs)
	cd analysis && python 01_winter_debt.py
	cd analysis && python 02_meter_anomalies.py
	cd analysis && python 03_payment_risk_model.py
	cd analysis && python 04_smart_tariff_response.py

all: build export check analyse

clean:
	rm -rf dbt/target data/marts/*.csv data/outputs data/winter_bill_risk.duckdb
