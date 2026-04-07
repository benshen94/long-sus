from __future__ import annotations

import json
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "outputs/plots/readme/tfr_usa_italy_south_africa_2100.png"

WPP_API_BASE = "https://population.un.org/dataportalapi/uiapi/v1"
TFR_INDICATOR_ID = 19
MEDIAN_VARIANT_ID = 4
TOTAL_AGE_ID = 188
BOTH_SEXES_ID = 3
DEFAULT_CATEGORY_ID = 0

COUNTRIES = {
    "United States": 840,
    "Italy": 380,
    "South Africa": 710,
}

COMPARISON_YEARS = list(range(2024, 2101))


plt.style.use("seaborn-v0_8-whitegrid")


def fetch_yearly_tfr(location_id: int) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []

    for year in COMPARISON_YEARS:
        path = (
            f"data/indicators/{TFR_INDICATOR_ID}/locations/{location_id}/years/{year}"
            f"/vars/{MEDIAN_VARIANT_ID}/ages/{TOTAL_AGE_ID}/sexes/{BOTH_SEXES_ID}/cats/{DEFAULT_CATEGORY_ID}"
        )
        result = subprocess.run(
            ["curl", "-ks", f"{WPP_API_BASE}/{path}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        records = json.loads(result.stdout)
        if not records:
            continue

        rows.append(
            {
                "year": int(records[0]["timeLabel"]),
                "tfr": float(records[0]["value"]),
            }
        )

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    colors = {
        "United States": "#355070",
        "Italy": "#6d597a",
        "South Africa": "#b56576",
    }

    fig, ax = plt.subplots(figsize=(11, 6))

    for country, location_id in COUNTRIES.items():
        frame = fetch_yearly_tfr(location_id)
        ax.plot(
            frame["year"],
            frame["tfr"],
            linewidth=2.6,
            color=colors[country],
            label=country,
        )

    ax.set_title("WPP median TFR projection to 2100", fontsize=15, weight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Total fertility rate")
    ax.set_xlim(2024, 2100)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=180)
    plt.close(fig)

    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
