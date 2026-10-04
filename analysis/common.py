"""Shared paths, loading helpers and chart style for the analysis scripts."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")  # save charts to files without opening windows
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"        # written by scripts/export_marts.py (from dbt)
OUTPUTS = ROOT / "data" / "outputs"    # written by these analysis scripts (for Tableau)
FIGURES = ROOT / "reports" / "figures"
METRICS = ROOT / "reports" / "metrics"
for folder in (OUTPUTS, FIGURES, METRICS):
    folder.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

# One consistent colour per Acorn group across every chart
GROUP_ORDER = ["Affluent", "Comfortable", "Adversity"]
GROUP_COLOURS = {"Affluent": "#2a6f97", "Comfortable": "#8ab17d", "Adversity": "#e76f51"}
ACCENT = "#e76f51"
NEUTRAL = "#6c757d"

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 160,
    "savefig.bbox": "tight",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "legend.frameon": False,
})


def load_mart(name: str, date_cols=None) -> pd.DataFrame:
    """Read one exported dbt mart (CSV) from data/marts."""
    path = MARTS / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `make build` (dbt) and `make export` first."
        )
    return pd.read_csv(path, parse_dates=date_cols or [])


def save_figure(fig, name: str) -> None:
    fig.savefig(FIGURES / f"{name}.png")
    plt.close(fig)
    print(f"  saved reports/figures/{name}.png")


def save_metrics(name: str, metrics: dict) -> None:
    with open(METRICS / f"{name}.json", "w") as f:
        json.dump(metrics, f, indent=2, default=float)
    print(f"  saved reports/metrics/{name}.json")


def month_axis(ax, fmt: str = "%b %y") -> None:
    """Show one tick per month with short labels like 'Oct 12'."""
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt))


def gbp(x: float) -> str:
    return f"£{x:,.0f}"
