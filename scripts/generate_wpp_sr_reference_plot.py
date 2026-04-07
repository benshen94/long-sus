from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.data_sources import download_usa_wpp_bundle


OUTPUT_PATH = PROJECT_ROOT / "outputs/plots/readme/wpp_vs_sr_reference_curves.png"
INTERVENTION_ASSET_PATH = PROJECT_ROOT / "dashboard/assets/usa_sr_interventions.json"
COMPARISON_YEARS = (2024, 2040, 2060, 2080, 2100)


plt.style.use("seaborn-v0_8-whitegrid")


def _load_baseline_sr_curves() -> tuple[np.ndarray, np.ndarray]:
    payload = json.loads(INTERVENTION_ASSET_PATH.read_text())
    baseline_survival = np.asarray(
        payload["targets"]["eta"]["hetero_modes"]["off"]["1.00"]["baseline_survival"],
        dtype=float,
    )

    baseline_hazard = np.ones(len(baseline_survival) - 1, dtype=float)
    for age in range(len(baseline_hazard)):
        current = max(float(baseline_survival[age]), 1e-9)
        next_value = max(float(baseline_survival[age + 1]), 1e-9)
        baseline_hazard[age] = -np.log(np.clip(next_value / current, 1e-9, 1.0))

    return baseline_survival, baseline_hazard


def _build_population_map(frame) -> dict[int, dict[str, np.ndarray]]:
    population_map: dict[int, dict[str, np.ndarray]] = {}
    max_age = int(frame["age"].max())

    for year, year_frame in frame.groupby("year"):
        population_map[int(year)] = {}
        for sex in ("male", "female"):
            values = np.full(max_age + 1, np.nan, dtype=float)
            sex_frame = year_frame[year_frame["sex"] == sex]
            for age, value in zip(sex_frame["age"], sex_frame["population"]):
                values[int(age)] = float(value)
            population_map[int(year)][sex] = values

    return population_map


def _build_mortality_map(frame) -> dict[int, dict[str, np.ndarray]]:
    mortality_map: dict[int, dict[str, np.ndarray]] = {}
    max_age = int(frame["age"].max())

    for year, year_frame in frame.groupby("year"):
        mortality_map[int(year)] = {}
        for sex in ("male", "female"):
            values = np.full(max_age + 1, np.nan, dtype=float)
            sex_frame = year_frame[year_frame["sex"] == sex]
            for age, value in zip(sex_frame["age"], sex_frame["mx"]):
                values[int(age)] = float(value)
            values[int(sex_frame["age"].max()) + 1 :] = values[int(sex_frame["age"].max())]
            mortality_map[int(year)][sex] = values

    return mortality_map


def _all_sex_wpp_hazard(
    *,
    year: int,
    population: dict[int, dict[str, np.ndarray]],
    mortality: dict[int, dict[str, np.ndarray]],
) -> np.ndarray:
    male_population = population[year]["male"]
    female_population = population[year]["female"]
    total_population = male_population + female_population

    weighted_hazard = (
        mortality[year]["male"] * male_population
        + mortality[year]["female"] * female_population
    )

    hazard = np.full_like(total_population, np.nan, dtype=float)
    nonzero_mask = total_population > 0.0
    hazard[nonzero_mask] = weighted_hazard[nonzero_mask] / total_population[nonzero_mask]
    if np.any(nonzero_mask):
        last_populated_age = int(np.flatnonzero(nonzero_mask)[-1])
        hazard[last_populated_age + 1 :] = hazard[last_populated_age]
    return hazard


def _survival_from_hazard(hazard: np.ndarray) -> np.ndarray:
    survival = np.full(len(hazard) + 1, np.nan, dtype=float)
    survival[0] = 1.0

    for age, value in enumerate(hazard):
        survival[age + 1] = survival[age] * np.exp(-float(value))

    return survival


def main() -> None:
    bundle = download_usa_wpp_bundle(start_year=2020, end_year=2100, force=False)
    population = _build_population_map(bundle.population["medium"])
    mortality = _build_mortality_map(bundle.mortality)
    baseline_survival, baseline_hazard = _load_baseline_sr_curves()

    colors = ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    baseline_survival_ages = np.arange(0, len(baseline_survival), dtype=int)
    baseline_hazard_ages = np.arange(0, len(baseline_hazard), dtype=int)

    axes[0].plot(
        baseline_survival_ages,
        baseline_survival * 1000.0,
        color="#111111",
        linewidth=2.8,
        label="Vanilla SR baseline",
    )
    axes[1].plot(
        baseline_hazard_ages,
        baseline_hazard,
        color="#111111",
        linewidth=2.8,
        label="Vanilla SR baseline",
    )

    for year, color in zip(COMPARISON_YEARS, colors):
        wpp_hazard = _all_sex_wpp_hazard(
            year=year,
            population=population,
            mortality=mortality,
        )
        wpp_survival = _survival_from_hazard(wpp_hazard)
        axes[0].plot(
            np.arange(0, len(wpp_survival), dtype=int),
            wpp_survival * 1000.0,
            color=color,
            linewidth=2.1,
            label=f"WPP {year}",
        )
        axes[1].plot(
            np.arange(0, len(wpp_hazard), dtype=int),
            wpp_hazard,
            color=color,
            linewidth=2.1,
            label=f"WPP {year}",
        )

    axes[0].set_title("Survival")
    axes[0].set_xlabel("Age")
    axes[0].set_ylabel("People alive per 1000")
    axes[0].set_xlim(0, len(baseline_survival) - 1)

    axes[1].set_title("Annual hazard")
    axes[1].set_xlabel("Age")
    axes[1].set_ylabel("Hazard")
    axes[1].set_xlim(0, len(baseline_hazard) - 1)
    axes[1].set_yscale("log")

    for ax in axes:
        ax.axvline(100, color="#666666", linewidth=1.0, linestyle=":")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(loc="best")

    fig.suptitle("Vanilla SR baseline vs WPP projected mortality backbone", fontsize=16, weight="bold")
    fig.tight_layout()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=180)
    plt.close(fig)

    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
