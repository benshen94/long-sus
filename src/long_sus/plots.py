from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import README_PLOTS_DIR
from .intervention_assets import build_all_sex_wpp_hazard, build_cohort_survival_curve, survival_from_hazard_curve
from .scenarios import build_validation_scenario
from .specs import FigureArtifact, SRInterventionAsset
from .sr_intervention import get_baseline_simulation


plt.style.use("seaborn-v0_8-whitegrid")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _pyramid_arrays(
    population_frame: pd.DataFrame,
    scenario: str,
    year: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sample = population_frame[
        (population_frame["scenario"] == scenario)
        & (population_frame["year"] == year)
    ].copy()
    sample = sample.sort_values(["sex", "age"])

    ages = np.arange(sample["age"].min(), sample["age"].max() + 1)
    male = sample[sample["sex"] == "male"]["population_count"].to_numpy()
    female = sample[sample["sex"] == "female"]["population_count"].to_numpy()
    return ages, male, female


def plot_multi_scenario_pyramids(
    population_frame: pd.DataFrame,
    scenarios: list[str],
    titles: list[str],
    year: int,
    path: Path,
    title: str,
) -> None:
    _ensure_parent(path)
    fig, axes = plt.subplots(1, len(scenarios), figsize=(18, 9), sharey=True)
    max_value = 0.0
    arrays: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []

    for scenario in scenarios:
        ages, male, female = _pyramid_arrays(population_frame, scenario, year)
        arrays.append((ages, male, female))
        max_value = max(max_value, male.max(), female.max())

    for ax, panel_title, values in zip(axes, titles, arrays):
        ages, male, female = values
        ax.barh(ages, -(male / 1_000_000), color="#3b5b92", alpha=0.92)
        ax.barh(ages, female / 1_000_000, color="#df6d57", alpha=0.92)
        ax.axvline(0.0, color="#1b1b1b", linewidth=0.8)
        ax.set_title(panel_title)
        ax.set_xlabel("Millions")

    axes[0].set_ylabel("Age")
    x_limit = (max_value / 1_000_000) * 1.15
    for ax in axes:
        ax.set_xlim(-x_limit, x_limit)
        ticks = ax.get_xticks()
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{abs(tick):.1f}" for tick in ticks])

    fig.suptitle(title, fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_scenario_comparison_pyramid(
    population_frame: pd.DataFrame,
    left_scenario: str,
    right_scenario: str,
    year: int,
    path: Path,
    title: str,
) -> None:
    _ensure_parent(path)
    fig, axes = plt.subplots(1, 2, figsize=(12, 9), sharey=True)
    scenarios = [left_scenario, right_scenario]
    max_value = 0.0
    arrays: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []

    for scenario in scenarios:
        ages, male, female = _pyramid_arrays(population_frame, scenario, year)
        arrays.append((ages, male, female))
        max_value = max(max_value, male.max(), female.max())

    for ax, scenario, values in zip(axes, scenarios, arrays):
        ages, male, female = values
        ax.barh(ages, -(male / 1_000_000), color="#456990", alpha=0.9)
        ax.barh(ages, female / 1_000_000, color="#ef767a", alpha=0.9)
        ax.axvline(0.0, color="black", linewidth=0.8)
        ax.set_title(scenario)
        ax.set_xlabel("Millions")

    axes[0].set_ylabel("Age")
    x_limit = (max_value / 1_000_000) * 1.15
    for ax in axes:
        ax.set_xlim(-x_limit, x_limit)
        ticks = ax.get_xticks()
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{abs(tick):.1f}" for tick in ticks])

    fig.suptitle(title, fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_total_population(
    summary_frame: pd.DataFrame,
    scenario_names: list[str],
    path: Path,
    title: str,
) -> None:
    _ensure_parent(path)
    sample = summary_frame[summary_frame["scenario"].isin(scenario_names)].copy()

    fig, ax = plt.subplots(figsize=(10, 6))
    for scenario in scenario_names:
        curve = sample[sample["scenario"] == scenario].sort_values("year")
        ax.plot(curve["year"], curve["total_population"] / 1_000_000, linewidth=2.5, label=scenario)

    ax.set_title(title, fontsize=14, weight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Population (millions)")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_old_age_share(
    summary_frame: pd.DataFrame,
    scenario_names: list[str],
    path: Path,
    title: str,
) -> None:
    _ensure_parent(path)
    sample = summary_frame[summary_frame["scenario"].isin(scenario_names)].copy()

    fig, ax = plt.subplots(figsize=(10, 6))
    for scenario in scenario_names:
        curve = sample[sample["scenario"] == scenario].sort_values("year")
        ax.plot(curve["year"], curve["old_age_share_65_plus"] * 100.0, linewidth=2.5, label=scenario)

    ax.set_title(title, fontsize=14, weight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Population age 65+ (%)")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_treated_share_heatmap(
    population_frame: pd.DataFrame,
    scenario: str,
    path: Path,
    title: str,
) -> None:
    _ensure_parent(path)
    sample = population_frame[population_frame["scenario"] == scenario].copy()
    grouped = (
        sample.groupby(["year", "age"], as_index=False)[["population_count", "treated_population_count"]]
        .sum()
    )
    grouped["treated_share"] = np.where(
        grouped["population_count"] > 0.0,
        grouped["treated_population_count"] / grouped["population_count"],
        0.0,
    )
    heatmap = grouped.pivot(index="age", columns="year", values="treated_share").sort_index(ascending=False)

    fig, ax = plt.subplots(figsize=(12, 8))
    image = ax.imshow(heatmap, aspect="auto", cmap="viridis", vmin=0.0, vmax=1.0)
    ax.set_title(title, fontsize=14, weight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Age")

    year_labels = heatmap.columns.to_list()
    if len(year_labels) > 12:
        step = max(1, len(year_labels) // 10)
        tick_positions = list(range(0, len(year_labels), step))
        ax.set_xticks(tick_positions)
        ax.set_xticklabels([year_labels[position] for position in tick_positions], rotation=45)
    else:
        ax.set_xticks(range(len(year_labels)))
        ax.set_xticklabels(year_labels, rotation=45)

    age_labels = heatmap.index.to_list()
    ax.set_yticks(range(0, len(age_labels), 10))
    ax.set_yticklabels([age_labels[position] for position in range(0, len(age_labels), 10)])

    fig.colorbar(image, ax=ax, label="Treated share")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_calibration_curves(
    calibration_curves: pd.DataFrame,
    path: Path,
    title: str,
) -> None:
    _ensure_parent(path)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    for ax, sex in zip(axes, ("male", "female")):
        sample = calibration_curves[calibration_curves["sex"] == sex]
        ax.plot(sample["age"], sample["hmd_mx"], linewidth=2.5, label="HMD 2019")
        ax.plot(sample["age"], sample["mgg_mx"], linewidth=2.5, linestyle="--", label="MGG fit")
        ax.set_yscale("log")
        ax.set_title(sex.title())
        ax.set_xlabel("Age")
        ax.grid(True, which="both", alpha=0.3)

    axes[0].set_ylabel("Mortality rate (log scale)")
    axes[1].legend(loc="best")
    fig.suptitle(title, fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_survival_curves(
    curves: dict[str, np.ndarray],
    path: Path,
    title: str,
) -> None:
    _ensure_parent(path)
    fig, ax = plt.subplots(figsize=(10, 6))
    ages = np.arange(0, len(next(iter(curves.values()))), dtype=int)

    for label, survival in curves.items():
        ax.plot(ages, survival * 1000.0, linewidth=2.5, label=label)

    ax.set_title(title, fontsize=14, weight="bold")
    ax.set_xlabel("Age")
    ax.set_ylabel("People alive per 1000")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_wpp_sr_reference_curves(
    *,
    inputs,
    path: Path,
    title: str,
    comparison_years: tuple[int, ...] = (2024, 2040, 2060, 2080, 2100),
) -> None:
    _ensure_parent(path)

    missing_years = [year for year in comparison_years if year not in inputs.years]
    if missing_years:
        raise ValueError(f"Missing WPP years for reference plot: {missing_years}")

    baseline = get_baseline_simulation(
        preset_name="usa_2019",
        use_heterogeneity=False,
        heterogeneity_std=0.2,
    )

    colors = ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    baseline_ages = np.arange(0, len(baseline.survival), dtype=int)
    axes[0].plot(
        baseline_ages,
        baseline.survival * 1000.0,
        color="#111111",
        linewidth=2.8,
        label="SR baseline (usa_2019)",
    )

    hazard_ages = np.arange(0, len(baseline.annual_hazard), dtype=int)
    axes[1].plot(
        hazard_ages,
        baseline.annual_hazard,
        color="#111111",
        linewidth=2.8,
        label="SR baseline (usa_2019)",
    )

    for year, color in zip(comparison_years, colors):
        wpp_hazard = build_all_sex_wpp_hazard(
            inputs=inputs,
            year=year,
        )
        wpp_survival = survival_from_hazard_curve(wpp_hazard)
        wpp_survival_ages = np.arange(0, len(wpp_survival), dtype=int)
        wpp_hazard_ages = np.arange(0, len(wpp_hazard), dtype=int)

        axes[0].plot(
            wpp_survival_ages,
            wpp_survival * 1000.0,
            color=color,
            linewidth=2.1,
            label=f"WPP {year}",
        )
        axes[1].plot(
            wpp_hazard_ages,
            wpp_hazard,
            color=color,
            linewidth=2.1,
            label=f"WPP {year}",
        )

    axes[0].set_title("Survival")
    axes[0].set_xlabel("Age")
    axes[0].set_ylabel("People alive per 1000")
    axes[0].set_xlim(0, len(baseline.survival) - 1)

    axes[1].set_title("Annual hazard")
    axes[1].set_xlabel("Age")
    axes[1].set_ylabel("Hazard")
    axes[1].set_xlim(0, len(baseline.annual_hazard) - 1)
    axes[1].set_yscale("log")

    for ax in axes:
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(loc="best")

    fig.suptitle(title, fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_readme_figure_registry(
    population_frame: pd.DataFrame,
    summary_frame: pd.DataFrame,
    calibration_curves: pd.DataFrame,
    intervention_grid: dict[tuple[str, str, float], SRInterventionAsset],
    inputs,
) -> list[FigureArtifact]:
    README_PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    artifacts: list[FigureArtifact] = []

    calibration_path = README_PLOTS_DIR / "calibration_hmd_vs_mgg.png"
    plot_calibration_curves(calibration_curves, calibration_path, "USA adult mortality benchmark")
    artifacts.append(
        FigureArtifact(
            title="Calibration benchmark",
            path=calibration_path,
            caption="Adult USA HMD 2019 hazards compared with the fitted Gamma-Gompertz-Makeham benchmark.",
        )
    )

    reference_path = README_PLOTS_DIR / "wpp_vs_sr_reference_curves.png"
    plot_wpp_sr_reference_curves(
        inputs=inputs,
        path=reference_path,
        title="Untreated SR baseline vs WPP mortality backbone",
    )
    artifacts.append(
        FigureArtifact(
            title="WPP vs SR reference curves",
            path=reference_path,
            caption="Untreated usa_2019 SR curves compared with all-sex WPP-implied curves for 2020, 2040, 2060, 2080, and 2100.",
        )
    )

    scheme_compare_path = README_PLOTS_DIR / "scheme_comparison_eta_0_80x_2075.png"
    plot_multi_scenario_pyramids(
        population_frame=population_frame,
        scenarios=[
            "threshold_age_60_all_eligible_eta_0.80x",
            "prescription_bands_absolute_eta_0.80x",
            "prescription_bands_equal_probabilities_eta_0.80x",
            "prescription_bands_uniform_start_age_eta_0.80x",
        ],
        titles=[
            "Threshold 60",
            "Bands / absolute",
            "Bands / equal p",
            "Bands / uniform",
        ],
        year=2075,
        path=scheme_compare_path,
        title="One eta factor, different drug-start schemes",
    )
    artifacts.append(
        FigureArtifact(
            title="Scheme comparison at eta 0.80x",
            path=scheme_compare_path,
            caption="At a fixed eta factor of 0.80x, the start mechanism still changes the late-life population shape.",
        )
    )

    factor_compare_path = README_PLOTS_DIR / "eta_factor_comparison_threshold_60_2075.png"
    plot_multi_scenario_pyramids(
        population_frame=population_frame,
        scenarios=[
            "threshold_age_60_all_eligible_eta_1.00x",
            "threshold_age_60_all_eligible_eta_0.90x",
            "threshold_age_60_all_eligible_eta_0.80x",
            "threshold_age_60_all_eligible_eta_0.70x",
        ],
        titles=[
            "1.00x",
            "0.90x",
            "0.80x",
            "0.70x",
        ],
        year=2075,
        path=factor_compare_path,
        title="One start rule, multiple eta factors",
    )
    artifacts.append(
        FigureArtifact(
            title="Eta factor comparison for threshold age 60",
            path=factor_compare_path,
            caption="Holding the threshold-60 start rule fixed isolates how the eta factor changes the long-run pyramid.",
        )
    )

    intervention_compare_path = README_PLOTS_DIR / "baseline_vs_threshold60_eta_0_80x_2075.png"
    plot_scenario_comparison_pyramid(
        population_frame=population_frame,
        left_scenario="no_one",
        right_scenario="threshold_age_60_all_eligible_eta_0.80x",
        year=2075,
        path=intervention_compare_path,
        title="Baseline vs age-60 intervention in 2075",
    )
    artifacts.append(
        FigureArtifact(
            title="Baseline vs intervention in 2075",
            path=intervention_compare_path,
            caption="Untreated baseline compared with the threshold-age-60 eta 0.80x scenario.",
        )
    )

    total_population_path = README_PLOTS_DIR / "eta_factor_total_population_over_time.png"
    plot_total_population(
        summary_frame=summary_frame,
        scenario_names=[
            "no_one",
            "threshold_age_60_all_eligible_eta_0.90x",
            "threshold_age_60_all_eligible_eta_0.80x",
            "threshold_age_60_all_eligible_eta_0.70x",
        ],
        path=total_population_path,
        title="Total population across the eta grid",
    )
    artifacts.append(
        FigureArtifact(
            title="Total population",
            path=total_population_path,
            caption="At fixed uptake, stronger eta reductions produce larger long-run population divergence.",
        )
    )

    age_share_path = README_PLOTS_DIR / "eta_start_rule_share_age_65_plus.png"
    plot_old_age_share(
        summary_frame=summary_frame,
        scenario_names=[
            "no_one",
            "prescription_bands_absolute_eta_0.80x",
            "prescription_bands_equal_probabilities_eta_0.80x",
            "prescription_bands_uniform_start_age_eta_0.80x",
        ],
        path=age_share_path,
        title="Population share age 65+ across start schemes",
    )
    artifacts.append(
        FigureArtifact(
            title="Older-age share",
            path=age_share_path,
            caption="At fixed eta, different start rules reshape how much population mass accumulates above age 65.",
        )
    )

    heatmap_path = README_PLOTS_DIR / "treated_share_heatmap.png"
    plot_treated_share_heatmap(
        population_frame=population_frame,
        scenario="prescription_bands_equal_probabilities_eta_0.80x",
        path=heatmap_path,
        title="Treated share by age and year",
    )
    artifacts.append(
        FigureArtifact(
            title="Treated share heatmap",
            path=heatmap_path,
            caption="The heatmap shows who starts immediately, who ages into treatment later, and how probabilistic uptake fills cohorts over time.",
        )
    )

    survival_asset = intervention_grid[("eta", "off", 0.80)]
    survival_curves = {
        "No one": build_cohort_survival_curve(
            survival_asset,
            build_validation_scenario("no_one"),
        ),
        "50% elderly": build_cohort_survival_curve(
            survival_asset,
            build_validation_scenario("50pct_elderly_65plus", target="eta", factor=0.80),
        ),
        "30% middle, 70% elderly": build_cohort_survival_curve(
            survival_asset,
            build_validation_scenario("30pct_middle_40_64_plus_70pct_elderly_65plus", target="eta", factor=0.80),
        ),
        "All elderly": build_cohort_survival_curve(
            survival_asset,
            build_validation_scenario("only_elderly_65plus", target="eta", factor=0.80),
        ),
        "Half of adults": build_cohort_survival_curve(
            survival_asset,
            build_validation_scenario("half_population_adult_band", target="eta", factor=0.80),
        ),
        "Everyone": build_cohort_survival_curve(
            survival_asset,
            build_validation_scenario("everyone", target="eta", factor=0.80),
        ),
    }
    survival_path = README_PLOTS_DIR / "sr_survival_curves_absolute_model.png"
    plot_survival_curves(
        curves=survival_curves,
        path=survival_path,
        title="Survival curves under different intervention schemes",
    )
    artifacts.append(
        FigureArtifact(
            title="SR survival curves",
            path=survival_path,
            caption="Start-age-conditioned SR surfaces are mixed into paper-style cohort survival curves before the demographic projection layer.",
        )
    )

    return artifacts
