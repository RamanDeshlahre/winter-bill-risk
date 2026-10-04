# Putting this project on GitHub (Mac)

## 1. One-time setup

```bash
git --version                        # if asked, install the command line developer tools
git config --global user.name "Raman D."
git config --global user.email "raman.deshlahre@outlook.com"
```

Install the GitHub command line tool. It is the easiest way to log in.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"   # Homebrew, if you don't have it
brew install gh
gh auth login          # choose: GitHub.com → HTTPS → Login with a web browser
```

## 2. Create the empty repository

On github.com: **+ → New repository**
- Name: `winter-bill-risk`
- Description: *Spotting energy customers heading into debt and helping them early: dbt, DuckDB, Python, Tableau*
- **Public**, and do **not** add a README, .gitignore or licence (the project already has them)

## 3. Check nothing private or huge will be uploaded

```bash
cd ~/projects/winter-bill-risk
git init
git status
```

`git status` must **not** list any `.csv` files from `data/`, `.venv/` or `.duckdb` files. The `.gitignore` file keeps them out. If you see them, stop and ask.

## 4. Commit in logical steps (a clean history looks professional)

```bash
git add .gitignore requirements.txt Makefile
git commit -m "Set up project: requirements, Makefile, gitignore"

git add dbt/dbt_project.yml dbt/profiles.yml dbt/models/staging
git commit -m "Add dbt staging models and tests (incl. weather timezone fix)"

git add dbt/models/intermediate dbt/models/marts dbt/tests
git commit -m "Add marts: monthly bills, Direct Debit simulation, anomaly signals, credit features"

git add scripts
git commit -m "Add mart export and reconciliation check"

git add analysis reports
git commit -m "Add analyses, charts and findings"

git add README.md docs tableau
git commit -m "Add README, methodology, data sources and Tableau spec"

git add -A && git status        # anything left? commit it
```

## 5. Push to GitHub

```bash
git branch -M main
git remote add origin https://github.com/<your-username>/winter-bill-risk.git
git push -u origin main
```

## 6. Make it look good

- On the repo page, click the gear next to **About** and add topics: `dbt` `duckdb` `sql` `python` `scikit-learn` `tableau` `credit-risk` `energy` `data-analysis`.
- On your GitHub profile: **Customize your pins**, then pin this repo.
- Replace `<your-username>` in `README.md` and add your Tableau Public and slide links. Then:

```bash
git add README.md && git commit -m "Add dashboard and slide links" && git push
```

## Everyday changes later

```bash
git add <changed files>
git commit -m "Short description of what changed"
git push
```
