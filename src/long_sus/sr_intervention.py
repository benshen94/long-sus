from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .config import MAX_AGE, MAX_START_AGE, MIN_START_AGE
from .external_paths import ensure_ageing_python_path
from .specs import SRInterventionAsset, ScenarioSpec, UsaCalibrationPreset
from .uptake import build_lifetime_start_weights


USA_2019_MULTIPLIERS = {
    "Xc": 0.97,
    "epsilon": 1.05,
    "eta": 0.96,
}

SR_AGENT_COUNT = 6_000
SR_DT = 0.025
SR_SIM_MAX_AGE = MAX_AGE + 1
SR_SEED = 17_291
HAZARD_FLOOR = 1e-9


@dataclass(frozen=True)
class SRSimulationSnapshot:
    params: dict[str, np.ndarray]
    saved_ages: np.ndarray
    paths: np.ndarray
    death_times: np.ndarray
    survival: np.ndarray
    annual_hazard: np.ndarray


def _load_sr_tools():
    ensure_ageing_python_path()
    from ageing_packages.utils.sr_utils import create_sr_simulation, load_baseline_human_params_dict  # type: ignore

    return create_sr_simulation, load_baseline_human_params_dict


def build_usa_2019_scalar_params() -> dict[str, float]:
    _, load_baseline_human_params_dict = _load_sr_tools()
    baseline = load_baseline_human_params_dict()

    params: dict[str, float] = {}
    for key, value in baseline.items():
        scalar_value = float(np.asarray(value, dtype=float).reshape(-1)[0])
        params[key] = scalar_value * USA_2019_MULTIPLIERS.get(key, 1.0)

    return params


def _expand_scalar_params(
    scalar_params: dict[str, float],
    n_agents: int,
) -> dict[str, np.ndarray]:
    return {
        key: np.full(n_agents, float(value), dtype=float)
        for key, value in scalar_params.items()
    }


def build_preset_params(
    preset: UsaCalibrationPreset,
    n_agents: int,
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(SR_SEED + (100 if preset.use_heterogeneity else 0))
    params = _expand_scalar_params(build_usa_2019_scalar_params(), n_agents=n_agents)

    if not preset.use_heterogeneity:
        return params

    if preset.heterogeneity_param != "Xc":
        raise ValueError("This validation pass only supports heterogeneity on Xc")

    params["Xc"] = np.clip(
        rng.normal(loc=params["Xc"], scale=preset.heterogeneity_std, size=n_agents),
        0.25,
        None,
    )
    return params


def _pad_paths_to_full_age_grid(
    paths: np.ndarray,
    saved_ages: np.ndarray,
    max_age: int,
) -> np.ndarray:
    full_paths = np.zeros((paths.shape[0], max_age + 1), dtype=float)
    full_paths[:, : paths.shape[1]] = paths

    if paths.shape[1] == 0:
        return full_paths

    last_column = paths[:, [-1]]
    for age in range(paths.shape[1], max_age + 1):
        full_paths[:, age : age + 1] = last_column

    return full_paths


def _survival_from_death_times(
    death_times: np.ndarray,
    ages: np.ndarray,
) -> np.ndarray:
    survival = np.zeros(len(ages), dtype=float)

    for age_index, age in enumerate(ages):
        survival[age_index] = np.count_nonzero(death_times > age) / max(len(death_times), 1)

    return survival


def _annual_hazard_from_survival(survival: np.ndarray) -> np.ndarray:
    hazard = np.ones(len(survival) - 1, dtype=float)

    for age in range(len(hazard)):
        current = max(float(survival[age]), HAZARD_FLOOR)
        next_value = max(float(survival[age + 1]), HAZARD_FLOOR)
        ratio = np.clip(next_value / current, HAZARD_FLOOR, 1.0)
        hazard[age] = -np.log(ratio)

    kernel = np.array([0.25, 0.5, 0.25], dtype=float)
    padded = np.pad(hazard, (1, 1), mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")
    return np.clip(smoothed, HAZARD_FLOOR, None)


def _run_sr_simulation(
    *,
    params: dict[str, np.ndarray],
    tmax: int,
    x0: np.ndarray | float,
    seed: int,
    drift_expr: str | None = None,
    extra_params: dict[str, np.ndarray | float] | None = None,
) -> SRSimulationSnapshot:
    create_sr_simulation, _ = _load_sr_tools()

    np.random.seed(seed)
    simulation = create_sr_simulation(
        params_dict=params,
        n=len(params["eta"]),
        tmax=tmax,
        dt=SR_DT,
        save_times=1,
        parallel=False,
        break_early=True,
        use_fast_kernel=drift_expr is None,
        x0=x0,
        drift_expr=drift_expr,
        drift_mode="replace",
        extra_params=extra_params,
    )

    saved_ages = np.rint(simulation.tspan).astype(int)
    full_ages = np.arange(0, tmax + 1, dtype=int)
    padded_paths = _pad_paths_to_full_age_grid(
        paths=np.asarray(simulation.paths, dtype=float),
        saved_ages=saved_ages,
        max_age=tmax,
    )
    survival = _survival_from_death_times(
        death_times=np.asarray(simulation.death_times, dtype=float),
        ages=full_ages,
    )
    annual_hazard = _annual_hazard_from_survival(survival)

    return SRSimulationSnapshot(
        params=params,
        saved_ages=full_ages,
        paths=padded_paths,
        death_times=np.asarray(simulation.death_times, dtype=float),
        survival=survival,
        annual_hazard=annual_hazard,
    )


def _build_baseline_simulation(preset: UsaCalibrationPreset) -> SRSimulationSnapshot:
    params = build_preset_params(preset, n_agents=SR_AGENT_COUNT)
    x0 = np.full(SR_AGENT_COUNT, 1e-6, dtype=float)
    return _run_sr_simulation(
        params=params,
        tmax=SR_SIM_MAX_AGE,
        x0=x0,
        seed=SR_SEED + (100 if preset.use_heterogeneity else 0),
    )


@lru_cache(maxsize=4)
def get_baseline_simulation(
    preset_name: str,
    use_heterogeneity: bool,
    heterogeneity_std: float,
) -> SRSimulationSnapshot:
    preset = UsaCalibrationPreset(
        name=preset_name,
        use_heterogeneity=use_heterogeneity,
        heterogeneity_param="Xc",
        heterogeneity_std=heterogeneity_std,
    )
    return _build_baseline_simulation(preset)


def _build_eta_continuation_params(
    baseline_params: dict[str, np.ndarray],
    factor: float,
    start_age: int,
) -> tuple[dict[str, np.ndarray], str, dict[str, np.ndarray]]:
    treated_params = {
        key: value.copy()
        for key, value in baseline_params.items()
    }
    treated_params["eta"] = treated_params["eta"] * factor

    drift_expr = "base_production + eta * t - X * (beta / (X + kappa))"
    extra_params = {
        "base_production": baseline_params["eta"] * start_age,
    }
    return treated_params, drift_expr, extra_params


def _build_xc_continuation_params(
    baseline_params: dict[str, np.ndarray],
    factor: float,
) -> tuple[dict[str, np.ndarray], None, None]:
    treated_params = {
        key: value.copy()
        for key, value in baseline_params.items()
    }
    treated_params["Xc"] = treated_params["Xc"] * factor
    return treated_params, None, None


def _build_continuation_simulation(
    baseline: SRSimulationSnapshot,
    *,
    start_age: int,
    target: str,
    factor: float,
    hetero_mode: str,
) -> SRSimulationSnapshot:
    if np.isclose(factor, 1.0):
        return baseline

    alive_mask = baseline.death_times > start_age
    x_at_start = baseline.paths[:, start_age]
    x0 = x_at_start[alive_mask]

    if x0.size == 0:
        return baseline

    baseline_params = {
        key: value[alive_mask].copy()
        for key, value in baseline.params.items()
    }

    if target == "eta":
        treated_params, drift_expr, extra_params = _build_eta_continuation_params(
            baseline_params=baseline_params,
            factor=factor,
            start_age=start_age,
        )
    elif target == "Xc":
        treated_params, drift_expr, extra_params = _build_xc_continuation_params(
            baseline_params=baseline_params,
            factor=factor,
        )
    else:
        raise ValueError(f"Unsupported target: {target}")

    factor_key = int(round(factor * 100))
    hetero_key = 1 if hetero_mode == "on" else 0
    seed = SR_SEED + start_age * 101 + factor_key * 17 + hetero_key * 1_000 + (0 if target == "eta" else 5_000)

    return _run_sr_simulation(
        params=treated_params,
        tmax=SR_SIM_MAX_AGE - start_age,
        x0=x0,
        seed=seed,
        drift_expr=drift_expr,
        extra_params=extra_params,
    )


def _stitch_survival_curve(
    baseline: SRSimulationSnapshot,
    continuation: SRSimulationSnapshot,
    start_age: int,
) -> np.ndarray:
    full_survival = baseline.survival.copy()

    for attained_age in range(start_age, SR_SIM_MAX_AGE + 1):
        local_age = attained_age - start_age
        full_survival[attained_age] = baseline.survival[start_age] * continuation.survival[local_age]

    return full_survival


def build_sr_intervention_asset(
    *,
    preset: UsaCalibrationPreset,
    target: str,
    factor: float,
    start_ages: np.ndarray | None = None,
) -> SRInterventionAsset:
    if target not in {"eta", "Xc"}:
        raise ValueError(f"Unsupported target: {target}")

    baseline = get_baseline_simulation(
        preset_name=preset.name,
        use_heterogeneity=preset.use_heterogeneity,
        heterogeneity_std=preset.heterogeneity_std,
    )
    hetero_mode = "on" if preset.use_heterogeneity else "off"

    if start_ages is None:
        start_ages = np.arange(MIN_START_AGE, MAX_START_AGE + 1, dtype=int)

    if np.isclose(factor, 1.0):
        baseline_rows = np.repeat(
            baseline.survival[None, :],
            repeats=len(start_ages),
            axis=0,
        )
        identity_rows = np.ones((len(start_ages), MAX_AGE + 1), dtype=float)
        return SRInterventionAsset(
            target=target,
            factor=float(factor),
            hetero_mode=hetero_mode,
            start_ages=np.asarray(start_ages, dtype=int),
            ages=np.arange(0, MAX_AGE + 1, dtype=int),
            annual_hazard_multiplier=identity_rows,
            baseline_survival=baseline.survival.copy(),
            survival_by_start_age=baseline_rows,
        )

    multiplier_rows: list[np.ndarray] = []
    survival_rows: list[np.ndarray] = []

    for start_age in start_ages:
        continuation = _build_continuation_simulation(
            baseline=baseline,
            start_age=int(start_age),
            target=target,
            factor=float(factor),
            hetero_mode=hetero_mode,
        )
        full_survival = _stitch_survival_curve(
            baseline=baseline,
            continuation=continuation,
            start_age=int(start_age),
        )
        treated_hazard = _annual_hazard_from_survival(full_survival)
        multiplier = treated_hazard / np.maximum(baseline.annual_hazard, HAZARD_FLOOR)
        multiplier[: int(start_age)] = 1.0
        multiplier = np.clip(multiplier, 0.05, 2.50)

        survival_rows.append(full_survival.copy())
        multiplier_rows.append(multiplier.astype(float))

    return SRInterventionAsset(
        target=target,
        factor=float(factor),
        hetero_mode=hetero_mode,
        start_ages=np.asarray(start_ages, dtype=int),
        ages=np.arange(0, MAX_AGE + 1, dtype=int),
        annual_hazard_multiplier=np.vstack(multiplier_rows),
        baseline_survival=baseline.survival.copy(),
        survival_by_start_age=np.vstack(survival_rows),
    )


def build_sr_intervention_grid(
    *,
    eta_factors: tuple[float, ...],
    xc_factors: tuple[float, ...],
) -> dict[tuple[str, str, float], SRInterventionAsset]:
    base_preset = UsaCalibrationPreset(name="usa_2019", use_heterogeneity=False)
    hetero_preset = UsaCalibrationPreset(name="usa_2019_with_hetero", use_heterogeneity=True)

    grid: dict[tuple[str, str, float], SRInterventionAsset] = {}

    for preset in (base_preset, hetero_preset):
        hetero_mode = "on" if preset.use_heterogeneity else "off"

        for factor in eta_factors:
            grid[("eta", hetero_mode, factor)] = build_sr_intervention_asset(
                preset=preset,
                target="eta",
                factor=factor,
            )

        for factor in xc_factors:
            grid[("Xc", hetero_mode, factor)] = build_sr_intervention_asset(
                preset=preset,
                target="Xc",
                factor=factor,
            )

    return grid


def build_cohort_survival_curve(
    asset: SRInterventionAsset,
    scenario: ScenarioSpec,
) -> np.ndarray:
    start_age_lookup = {
        int(start_age): index
        for index, start_age in enumerate(asset.start_ages)
    }
    start_weights, untreated_share = build_lifetime_start_weights(
        scenario=scenario,
        ages=asset.start_ages,
    )

    curve = untreated_share * asset.baseline_survival.copy()
    for start_age, weight in zip(asset.start_ages, start_weights):
        if weight <= 0.0:
            continue
        row_index = start_age_lookup[int(start_age)]
        curve += weight * asset.survival_by_start_age[row_index]

    return curve
