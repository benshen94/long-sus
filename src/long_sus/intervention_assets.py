from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .config import BASELINE_FIT_CATALOG_PATH
from .specs import InterventionAsset, ScenarioSpec
from .uptake import build_lifetime_start_weights


ANALYTIC_BRANCH = "analytic_arm"
SR_BRANCH = "sr"

LEGACY_USA_ANALYTIC_PRESET_ID = "usa_period_2019_both_hazard"
DEFAULT_ANALYTIC_PRESET_ID = "world_period_2024_both_hazard"


def _slugify_country(country: str) -> str:
    safe = country.strip().lower().replace(" ", "_")
    return safe.replace("-", "_")


def _build_baseline_fit_preset_id(country: str, year: int) -> str:
    return f"{_slugify_country(country)}_period_{int(year)}_both_hazard"


def _legacy_usa_preset() -> dict[str, object]:
    return {
        "id": LEGACY_USA_ANALYTIC_PRESET_ID,
        "label": "USA 2019 Hazard Fit",
        "country": "USA",
        "gender": "both",
        "data_type": "period",
        "year": 2019,
        "fit_target": "hazard",
        "source": "Direct SRFitter hazard fit on 2026-03-31",
        "params": {
            "eta": 0.43858182758384656,
            "beta": 41.86849757284421,
            "epsilon": 37.51256801824486,
            "Xc": 23.096526094453885,
        },
        "age_start": 40,
        "age_end": 95,
        "notes": (
            "Fitted eta, beta, epsilon, and mean Xc with fixed kappa=0.5 and "
            "fixed h_ext=0.0. Xc heterogeneity is Gaussian with std=0.2*Xc_mean. "
            "Used lx weighting with a late-robust hazard objective."
        ),
    }


def _build_baseline_fit_presets() -> dict[str, dict[str, object]]:
    if not BASELINE_FIT_CATALOG_PATH.exists():
        return {}

    payload = json.loads(BASELINE_FIT_CATALOG_PATH.read_text())
    country_entries = payload.get("countries", {})
    if not isinstance(country_entries, dict):
        return {}

    presets: dict[str, dict[str, object]] = {}

    for entry in country_entries.values():
        country = str(entry.get("country", "")).strip()
        fit_year = int(entry.get("fit_year", payload.get("fit_year", 2024)))
        fit_params = entry.get("fit_params", {})
        if not country or not fit_params:
            continue

        preset_id = _build_baseline_fit_preset_id(country, fit_year)
        presets[preset_id] = {
            "id": preset_id,
            "label": f"{country} {fit_year} Hazard Fit",
            "country": country,
            "gender": "both",
            "data_type": "period",
            "year": fit_year,
            "fit_target": str(entry.get("target", "hazard")),
            "source": f"baseline_fits/{BASELINE_FIT_CATALOG_PATH.name}",
            "params": {
                "eta": float(fit_params["eta"]),
                "beta": float(fit_params["beta"]),
                "epsilon": float(fit_params["epsilon"]),
                "Xc": float(fit_params["Xc"]),
            },
            "age_start": int(entry.get("config", {}).get("age_start", 30)),
            "age_end": int(entry.get("config", {}).get("age_end", 100)),
            "location_id": int(entry.get("location_id", 0)),
            "h_ext": float(entry.get("h_ext", 0.0)),
            "notes": (
                f"Loaded from {BASELINE_FIT_CATALOG_PATH.name}. "
                f"Objective={entry.get('objective_name', 'unknown')}, "
                f"score={entry.get('score', 'unknown')}."
            ),
        }

    return presets


def _build_analytic_presets() -> dict[str, dict[str, object]]:
    presets = {
        LEGACY_USA_ANALYTIC_PRESET_ID: _legacy_usa_preset(),
    }
    presets.update(_build_baseline_fit_presets())
    return presets


ANALYTIC_PRESETS: dict[str, dict[str, object]] = _build_analytic_presets()


def default_analytic_preset_id() -> str:
    if DEFAULT_ANALYTIC_PRESET_ID not in ANALYTIC_PRESETS:
        return LEGACY_USA_ANALYTIC_PRESET_ID
    return DEFAULT_ANALYTIC_PRESET_ID


def list_analytic_presets() -> list[dict[str, object]]:
    return [ANALYTIC_PRESETS[preset_id] for preset_id in sorted(ANALYTIC_PRESETS)]


def build_analytic_preset_catalog_payload(
    default_preset_id: str | None = None,
) -> dict[str, object]:
    safe_default_preset_id = default_preset_id or default_analytic_preset_id()
    default_preset = get_analytic_preset(safe_default_preset_id)
    return {
        "country": default_preset["country"],
        "default_preset_id": safe_default_preset_id,
        "presets": list_analytic_presets(),
    }


def get_analytic_preset(preset_id: str | None) -> dict[str, object]:
    safe_preset_id = preset_id or default_analytic_preset_id()
    if safe_preset_id not in ANALYTIC_PRESETS:
        raise KeyError(f"Unknown analytic preset: {safe_preset_id}")
    return ANALYTIC_PRESETS[safe_preset_id]


def resolve_intervention_target(target: str | None) -> str:
    if target in (None, "none"):
        return "eta"
    if target not in {"eta", "Xc"}:
        raise ValueError(f"Unsupported target: {target}")
    return target


def factor_key(factor: float) -> str:
    return f"{float(factor):.2f}"


def sr_target_slug(target: str) -> str:
    return "xc" if target == "Xc" else "eta"


def build_sr_dashboard_asset_path(
    root: Path,
    *,
    target: str,
    hetero_mode: str,
    factor: float,
) -> Path:
    return root / sr_target_slug(target) / hetero_mode / f"{factor_key(factor)}.json"


def serialize_intervention_asset(asset: InterventionAsset) -> dict[str, object]:
    return {
        "target": asset.target,
        "factor": float(asset.factor),
        "hetero_mode": asset.hetero_mode,
        "start_ages": asset.start_ages.astype(int).tolist(),
        "ages": asset.ages.astype(int).tolist(),
        "annual_hazard_multiplier": asset.annual_hazard_multiplier.astype(float).tolist(),
        "baseline_survival": asset.baseline_survival.astype(float).tolist(),
        "survival_by_start_age": asset.survival_by_start_age.astype(float).tolist(),
    }


def build_all_sex_wpp_hazard(
    *,
    inputs,
    year: int,
) -> np.ndarray:
    if year not in inputs.mortality:
        raise KeyError(f"Missing mortality inputs for year {year}")
    if year not in inputs.population:
        raise KeyError(f"Missing population inputs for year {year}")

    male_population = inputs.population[year]["male"]
    female_population = inputs.population[year]["female"]
    total_population = male_population + female_population

    weighted_hazard = (
        inputs.mortality[year]["male"] * male_population
        + inputs.mortality[year]["female"] * female_population
    )

    hazard = np.zeros_like(total_population, dtype=float)
    nonzero_mask = total_population > 0.0
    if np.any(nonzero_mask):
        hazard[nonzero_mask] = weighted_hazard[nonzero_mask] / total_population[nonzero_mask]
        last_observed_age = int(np.flatnonzero(nonzero_mask)[-1])
        # Analytic-arm tail assumption:
        # beyond the last observed WPP age, keep the final observed hazard flat.
        hazard[last_observed_age + 1 :] = hazard[last_observed_age]

    return hazard


def survival_from_hazard_curve(hazard: np.ndarray) -> np.ndarray:
    survival = np.ones(len(hazard) + 1, dtype=float)

    for age, value in enumerate(hazard):
        survival[age + 1] = survival[age] * np.exp(-float(value))

    return survival


def _analytic_multiplier_exponent(
    *,
    target: str,
    factor: float,
    attained_ages: np.ndarray,
    start_age: int,
    params: dict[str, float],
) -> np.ndarray:
    eta = float(params["eta"])
    beta = float(params["beta"])
    epsilon = float(params["epsilon"])
    xc = float(params["Xc"])

    if target == "Xc":
        return -(((factor - 1.0) * xc) / epsilon) * (beta - (eta * attained_ages))

    if target == "eta":
        delta_age = attained_ages - float(start_age)
        return -((xc / epsilon) * (eta - (factor * eta)) * delta_age)

    raise ValueError(f"Unsupported target: {target}")


def build_analytic_multiplier_row(
    *,
    target: str,
    factor: float,
    start_age: int,
    ages: np.ndarray,
    preset: dict[str, object],
) -> np.ndarray:
    row = np.ones(len(ages), dtype=float)
    if np.isclose(factor, 1.0):
        return row

    active_mask = ages >= start_age
    if not np.any(active_mask):
        return row

    params = preset["params"]
    exponent = _analytic_multiplier_exponent(
        target=target,
        factor=float(factor),
        attained_ages=ages[active_mask].astype(float),
        start_age=int(start_age),
        params=params,
    )
    row[active_mask] = np.exp(np.clip(exponent, -60.0, 60.0))
    return row


def build_analytic_intervention_asset(
    *,
    inputs,
    target: str,
    factor: float,
    launch_year: int,
    analytic_preset_id: str | None,
    start_ages: np.ndarray | None = None,
) -> InterventionAsset:
    safe_target = resolve_intervention_target(target)
    preset = get_analytic_preset(analytic_preset_id)
    ages = np.asarray(inputs.ages, dtype=int)

    if start_ages is None:
        start_ages = ages.copy()

    baseline_hazard = build_all_sex_wpp_hazard(inputs=inputs, year=launch_year)
    baseline_survival = survival_from_hazard_curve(baseline_hazard)

    multiplier_rows: list[np.ndarray] = []
    survival_rows: list[np.ndarray] = []

    for start_age in start_ages:
        row = build_analytic_multiplier_row(
            target=safe_target,
            factor=float(factor),
            start_age=int(start_age),
            ages=ages,
            preset=preset,
        )
        treated_hazard = baseline_hazard * row
        treated_survival = survival_from_hazard_curve(treated_hazard)
        multiplier_rows.append(row)
        survival_rows.append(treated_survival)

    return InterventionAsset(
        target=safe_target,
        factor=float(factor),
        hetero_mode="off",
        start_ages=np.asarray(start_ages, dtype=int),
        ages=ages,
        annual_hazard_multiplier=np.vstack(multiplier_rows),
        baseline_survival=baseline_survival,
        survival_by_start_age=np.vstack(survival_rows),
    )


def select_intervention_asset(
    *,
    scenario: ScenarioSpec,
    inputs,
    sr_intervention_grid: dict[tuple[str, str, float], InterventionAsset] | None = None,
) -> InterventionAsset:
    safe_target = resolve_intervention_target(scenario.target)
    safe_factor = 1.0 if scenario.target is None else float(scenario.factor)

    if scenario.branch == ANALYTIC_BRANCH:
        return build_analytic_intervention_asset(
            inputs=inputs,
            target=safe_target,
            factor=safe_factor,
            launch_year=scenario.launch_year,
            analytic_preset_id=scenario.analytic_preset_id,
        )

    if scenario.branch != SR_BRANCH:
        raise ValueError(f"Unsupported branch: {scenario.branch}")

    if sr_intervention_grid is None:
        raise ValueError("SR intervention grid is required for the sr branch")

    return sr_intervention_grid[(safe_target, scenario.hetero_mode, safe_factor)]


def build_cohort_survival_curve(
    asset: InterventionAsset,
    scenario: ScenarioSpec,
) -> np.ndarray:
    start_weights, untreated_share = build_lifetime_start_weights(
        scenario=scenario,
        ages=asset.start_ages,
    )

    curve = untreated_share * asset.baseline_survival.copy()
    start_age_lookup = {
        int(start_age): index
        for index, start_age in enumerate(asset.start_ages)
    }

    for start_age, weight in zip(asset.start_ages, start_weights):
        if weight <= 0.0:
            continue

        row_index = start_age_lookup[int(start_age)]
        curve += weight * asset.survival_by_start_age[row_index]

    return curve
