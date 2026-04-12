from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import MAX_AGE, SEXES
from .data_sources import WppBundle
from .specs import InterventionAsset, ProjectionState, ScenarioSpec
from .uptake import (
    build_start_probability_table,
    resolve_age_bands,
    rollout_probability_for_year,
)


@dataclass
class VariantInputs:
    variant_name: str
    years: list[int]
    ages: np.ndarray
    population: dict[int, dict[str, np.ndarray]]
    mortality: dict[int, dict[str, np.ndarray]]
    fertility: dict[int, np.ndarray]
    sex_ratio_at_birth: dict[int, float]
    net_migration_total: dict[int, float]
    migration_residual: dict[int, dict[str, np.ndarray]] = field(default_factory=dict)


def _age_series_to_array(frame: pd.DataFrame, value_column: str) -> np.ndarray:
    values = np.zeros(MAX_AGE + 1, dtype=float)
    for age, value in zip(frame["age"], frame[value_column]):
        values[int(age)] = float(value)
    return values


def _tail_population_weights(mx: float, tail_length: int) -> np.ndarray:
    if tail_length <= 0:
        return np.ones(1, dtype=float)

    survival = float(np.exp(-max(mx, 0.0)))
    weights = np.ones(tail_length + 1, dtype=float)

    for index in range(1, len(weights)):
        weights[index] = weights[index - 1] * survival

    total = float(weights.sum())
    if total <= 0.0:
        return np.ones_like(weights) / len(weights)

    return weights / total


def _tail_log_hazard_slope(
    mx: np.ndarray,
    open_age: int,
    lookback_years: int = 5,
) -> float | None:
    if open_age <= 0:
        return None

    start_age = max(0, open_age - lookback_years)
    window = np.asarray(mx[start_age : open_age + 1], dtype=float)
    positive_window = window[window > 0.0]
    if positive_window.size < 2:
        return None

    return float(
        (np.log(positive_window[-1]) - np.log(positive_window[0]))
        / (positive_window.size - 1)
    )


def _is_open_age_100_bin(frame: pd.DataFrame, open_age: int) -> bool:
    if open_age != 100:
        return False

    if frame.empty:
        return False

    return int(frame["age"].max()) == 100


def _tail_population_weights_from_curve(mx_by_age: np.ndarray) -> np.ndarray:
    if len(mx_by_age) == 0:
        return np.ones(1, dtype=float)

    weights = np.ones(len(mx_by_age), dtype=float)

    for index in range(1, len(weights)):
        annual_survival = float(np.exp(-max(float(mx_by_age[index - 1]), 0.0)))
        weights[index] = weights[index - 1] * annual_survival

    total = float(weights.sum())
    if total <= 0.0:
        return np.ones_like(weights) / len(weights)

    return weights / total


def _extend_population_tail(
    population: np.ndarray,
    population_frame: pd.DataFrame,
    mortality_frame: pd.DataFrame,
) -> np.ndarray:
    if population_frame.empty:
        return population

    last_observed_age = int(population_frame["age"].max())
    if last_observed_age >= MAX_AGE:
        return population

    open_age_population = float(population[last_observed_age])
    if open_age_population <= 0.0:
        return population

    if mortality_frame.empty:
        return population

    mortality = _age_series_to_array(mortality_frame, "mx")
    mortality = _extend_mortality_tail(mortality, mortality_frame)
    tail_weights = _tail_population_weights_from_curve(mortality[last_observed_age:])
    population[last_observed_age:] = open_age_population * tail_weights
    return population


def _extend_mortality_tail(mx: np.ndarray, frame: pd.DataFrame) -> np.ndarray:
    if frame.empty:
        return mx

    last_observed_age = int(frame["age"].max())
    if last_observed_age >= MAX_AGE:
        return mx

    if not _is_open_age_100_bin(frame, last_observed_age):
        mx[last_observed_age + 1 :] = mx[last_observed_age]
        return mx

    log_slope = _tail_log_hazard_slope(mx, last_observed_age)
    if log_slope is None:
        mx[last_observed_age + 1 :] = mx[last_observed_age]
        return mx

    for age in range(last_observed_age + 1, MAX_AGE + 1):
        years_past_open_age = age - last_observed_age
        mx[age] = mx[last_observed_age] * np.exp(log_slope * years_past_open_age)

    return mx


def _build_population_map(
    frame: pd.DataFrame,
    mortality_frame: pd.DataFrame,
) -> dict[int, dict[str, np.ndarray]]:
    population_map: dict[int, dict[str, np.ndarray]] = {}
    for year, year_frame in frame.groupby("year"):
        population_map[int(year)] = {}
        for sex in SEXES:
            sex_frame = year_frame[year_frame["sex"] == sex]
            year_mortality = mortality_frame[
                (mortality_frame["year"] == int(year)) & (mortality_frame["sex"] == sex)
            ]
            population = _age_series_to_array(sex_frame, "population")
            population_map[int(year)][sex] = _extend_population_tail(
                population,
                sex_frame,
                year_mortality,
            )
    return population_map


def _build_mortality_map(frame: pd.DataFrame) -> dict[int, dict[str, np.ndarray]]:
    mortality_map: dict[int, dict[str, np.ndarray]] = {}
    for year, year_frame in frame.groupby("year"):
        mortality_map[int(year)] = {}
        for sex in SEXES:
            sex_frame = year_frame[year_frame["sex"] == sex]
            mortality = _age_series_to_array(sex_frame, "mx")
            mortality_map[int(year)][sex] = _extend_mortality_tail(mortality, sex_frame)
    return mortality_map


def _build_fertility_map(frame: pd.DataFrame) -> dict[int, np.ndarray]:
    fertility_map: dict[int, np.ndarray] = {}
    for year, year_frame in frame.groupby("year"):
        values = np.zeros(MAX_AGE + 1, dtype=float)
        for age, asfr in zip(year_frame["age"], year_frame["asfr"]):
            values[int(age)] = float(asfr) / 1000.0
        fertility_map[int(year)] = values
    return fertility_map


def _build_total_map(frame: pd.DataFrame, value_column: str) -> dict[int, float]:
    return {int(year): float(value) for year, value in zip(frame["year"], frame[value_column])}


def build_variant_inputs(bundle: WppBundle, variant_name: str) -> VariantInputs:
    population_frame = bundle.population[variant_name]
    years = sorted(int(year) for year in population_frame["year"].unique())
    ages = np.arange(0, MAX_AGE + 1, dtype=int)

    inputs = VariantInputs(
        variant_name=variant_name,
        years=years,
        ages=ages,
        mortality=_build_mortality_map(bundle.mortality),
        population=_build_population_map(population_frame, bundle.mortality),
        fertility=_build_fertility_map(bundle.fertility[variant_name]),
        sex_ratio_at_birth=_build_total_map(bundle.sex_ratio_at_birth[variant_name], "sex_ratio_at_birth"),
        net_migration_total=_build_total_map(bundle.net_migration[variant_name], "net_migration"),
    )
    inputs.migration_residual = derive_migration_residuals(inputs)
    return inputs


def annual_survival_from_mx(mx: np.ndarray) -> np.ndarray:
    return np.exp(-mx)


def compute_births(
    female_population: np.ndarray,
    asfr: np.ndarray,
    sex_ratio_at_birth: float,
) -> tuple[float, float]:
    total_births = float(np.sum(female_population * asfr))
    male_share = sex_ratio_at_birth / (1.0 + sex_ratio_at_birth)
    male_births = total_births * male_share
    female_births = total_births - male_births
    return male_births, female_births


def _age_survivors(survivors: np.ndarray) -> np.ndarray:
    aged = np.zeros_like(survivors)
    aged[1:] = survivors[:-1]
    aged[-1] += survivors[-1]
    return aged


def _age_treated_survivors(survivors: np.ndarray) -> np.ndarray:
    aged = np.zeros_like(survivors)
    aged[:, 1:] = survivors[:, :-1]
    aged[:, -1] += survivors[:, -1]
    return aged


def _sum_treated_by_age(treated: np.ndarray) -> np.ndarray:
    return treated.sum(axis=0)


def _positive_migration_treated_share(
    *,
    age: int,
    year: int,
    scenario: ScenarioSpec,
    current_share: float,
) -> float:
    if scenario.target is None:
        return current_share

    if year < scenario.launch_year:
        return current_share

    if scenario.uptake_mode == "threshold":
        if scenario.threshold_age is None:
            return current_share
        if age < scenario.threshold_age:
            return 0.0
        return float(np.clip(scenario.threshold_probability, 0.0, 1.0))

    if scenario.uptake_mode == "rollout":
        if scenario.threshold_age is None:
            return current_share
        if age < scenario.threshold_age:
            return 0.0
        return float(np.clip(rollout_probability_for_year(scenario, year), 0.0, 1.0))

    if scenario.uptake_mode != "banded":
        return current_share

    for band in resolve_age_bands(scenario.bands, max_age=MAX_AGE):
        if age < band.start_age or age > band.end_age:
            continue

        if scenario.start_rule_within_band == "absolute":
            return band.conditional_share

        return current_share

    return current_share


def _scenario_rollout_metadata(scenario: ScenarioSpec) -> dict[str, float | int | str]:
    return {
        "rollout_curve": scenario.rollout_curve,
        "rollout_launch_probability": scenario.rollout_launch_probability,
        "rollout_max_probability": scenario.rollout_max_probability,
        "rollout_ramp_years": scenario.rollout_ramp_years,
        "rollout_takeoff_years": scenario.rollout_takeoff_years,
    }


def _add_positive_migration_to_treated(
    *,
    treated: np.ndarray,
    age: int,
    treated_delta: float,
    treated_by_age: float,
) -> None:
    if treated_delta <= 0.0:
        return

    if treated_by_age > 0.0:
        per_start_share = treated[:, age] / treated_by_age
        treated[:, age] += treated_delta * per_start_share
        return

    row_index = min(age, treated.shape[0] - 1)
    if row_index < 0:
        return

    treated[row_index, age] += treated_delta


def _blank_projection_state(
    initial_population: dict[str, np.ndarray],
    start_age_count: int,
) -> ProjectionState:
    age_count = len(initial_population["male"])
    untreated = {
        sex: initial_population[sex].copy()
        for sex in SEXES
    }
    treated = {
        sex: np.zeros((start_age_count, age_count), dtype=float)
        for sex in SEXES
    }
    return ProjectionState(untreated=untreated, treated=treated)


def project_one_year_no_migration(
    current_population: dict[str, np.ndarray],
    mortality: dict[str, np.ndarray],
    fertility: np.ndarray,
    sex_ratio_at_birth: float,
) -> dict[str, np.ndarray]:
    age_count = len(current_population["male"])
    next_population = {sex: np.zeros(age_count, dtype=float) for sex in SEXES}

    male_births, female_births = compute_births(
        female_population=current_population["female"],
        asfr=fertility,
        sex_ratio_at_birth=sex_ratio_at_birth,
    )
    next_population["male"][0] = male_births
    next_population["female"][0] = female_births

    for sex in SEXES:
        survivors = current_population[sex] * annual_survival_from_mx(mortality[sex])
        next_population[sex] += _age_survivors(survivors)

    return next_population


def derive_migration_residuals(inputs: VariantInputs) -> dict[int, dict[str, np.ndarray]]:
    residuals: dict[int, dict[str, np.ndarray]] = {}

    for year in inputs.years[:-1]:
        projected = project_one_year_no_migration(
            current_population=inputs.population[year],
            mortality=inputs.mortality[year],
            fertility=inputs.fertility[year],
            sex_ratio_at_birth=inputs.sex_ratio_at_birth[year],
        )
        target = inputs.population[year + 1]
        residuals[year] = {
            sex: target[sex] - projected[sex]
            for sex in SEXES
        }

    return residuals


def _apply_migration_residual(
    state: ProjectionState,
    residual: dict[str, np.ndarray] | None,
    scenario: ScenarioSpec,
    year: int,
) -> ProjectionState:
    if residual is None:
        return state

    updated_untreated = {sex: state.untreated[sex].copy() for sex in SEXES}
    updated_treated = {sex: state.treated[sex].copy() for sex in SEXES}

    for sex in SEXES:
        delta = residual[sex]
        treated_by_age = _sum_treated_by_age(updated_treated[sex])

        for age in range(len(delta)):
            total = updated_untreated[sex][age] + treated_by_age[age]

            if delta[age] >= 0.0:
                current_share = treated_by_age[age] / total if total > 0.0 else 0.0
                treated_share = _positive_migration_treated_share(
                    age=age,
                    year=year + 1,
                    scenario=scenario,
                    current_share=current_share,
                )
                treated_share = float(np.clip(treated_share, 0.0, 1.0))
                treated_delta = delta[age] * treated_share
                untreated_delta = delta[age] - treated_delta

                updated_untreated[sex][age] += untreated_delta
                _add_positive_migration_to_treated(
                    treated=updated_treated[sex],
                    age=age,
                    treated_delta=treated_delta,
                    treated_by_age=treated_by_age[age],
                )
                continue

            if total <= 0.0:
                continue

            untreated_share = updated_untreated[sex][age] / total
            treated_share = treated_by_age[age] / total

            updated_untreated[sex][age] += delta[age] * untreated_share
            updated_untreated[sex][age] = max(updated_untreated[sex][age], 0.0)

            treated_delta = delta[age] * treated_share
            if treated_by_age[age] <= 0.0:
                continue

            per_start_share = updated_treated[sex][:, age] / treated_by_age[age]
            updated_treated[sex][:, age] += treated_delta * per_start_share
            updated_treated[sex][:, age] = np.clip(updated_treated[sex][:, age], 0.0, None)

    return ProjectionState(
        untreated=updated_untreated,
        treated=updated_treated,
    )


def _weighted_median_age(total_population: np.ndarray) -> float:
    if total_population.sum() <= 0.0:
        return 0.0

    cumulative = np.cumsum(total_population)
    midpoint = total_population.sum() / 2.0
    return float(np.searchsorted(cumulative, midpoint))


def _select_projection_years(
    available_years: list[int],
    projection_end_year: int | None,
) -> list[int]:
    if projection_end_year is None:
        return list(available_years)

    selected = [year for year in available_years if year <= projection_end_year]
    if len(selected) < 2:
        raise ValueError("Projection requires at least two years of input data")
    return selected


def _record_population_rows(
    scenario: ScenarioSpec,
    year: int,
    state: ProjectionState,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    rollout_metadata = _scenario_rollout_metadata(scenario)

    for sex in SEXES:
        treated_by_age = _sum_treated_by_age(state.treated[sex])
        total = state.untreated[sex] + treated_by_age

        for age in range(len(total)):
            rows.append(
                {
                    "scenario": scenario.name,
                    "scenario_label": scenario.label or scenario.name,
                    "scheme_id": scenario.scheme_id or scenario.name,
                    "country": scenario.country,
                    "mode": scenario.mode,
                    "variant": scenario.demo_variant,
                    "year": year,
                    "sex": sex,
                    "age": age,
                    "launch_year": scenario.launch_year,
                    "uptake_mode": scenario.uptake_mode,
                    "threshold_age": scenario.threshold_age if scenario.threshold_age is not None else -1,
                    "threshold_probability": scenario.threshold_probability,
                    "start_rule_within_band": scenario.start_rule_within_band,
                    "target": scenario.target or "none",
                    "factor": scenario.factor,
                    "branch": scenario.branch,
                    "analytic_preset_id": scenario.analytic_preset_id or "",
                    "hetero_mode": scenario.hetero_mode,
                    "migration_mode": scenario.migration_mode,
                    "population_count": float(total[age]),
                    "treated_population_count": float(treated_by_age[age]),
                    "untreated_population_count": float(state.untreated[sex][age]),
                    **rollout_metadata,
                }
            )

    return rows


def _record_summary_row(
    scenario: ScenarioSpec,
    year: int,
    state: ProjectionState,
    births: float,
    deaths: float,
) -> dict[str, float | int | str]:
    rollout_metadata = _scenario_rollout_metadata(scenario)
    male_total = state.untreated["male"] + _sum_treated_by_age(state.treated["male"])
    female_total = state.untreated["female"] + _sum_treated_by_age(state.treated["female"])
    combined = male_total + female_total

    total_population = float(combined.sum())
    treated_population = float(
        _sum_treated_by_age(state.treated["male"]).sum()
        + _sum_treated_by_age(state.treated["female"]).sum()
    )

    old_age_share_60 = float(combined[60:].sum() / total_population) if total_population else 0.0
    old_age_share_65 = float(combined[65:].sum() / total_population) if total_population else 0.0

    return {
        "scenario": scenario.name,
        "scenario_label": scenario.label or scenario.name,
        "scheme_id": scenario.scheme_id or scenario.name,
        "country": scenario.country,
        "mode": scenario.mode,
        "variant": scenario.demo_variant,
        "year": year,
        "launch_year": scenario.launch_year,
        "uptake_mode": scenario.uptake_mode,
        "threshold_age": scenario.threshold_age if scenario.threshold_age is not None else -1,
        "threshold_probability": scenario.threshold_probability,
        "start_rule_within_band": scenario.start_rule_within_band,
        "target": scenario.target or "none",
        "factor": scenario.factor,
        "branch": scenario.branch,
        "analytic_preset_id": scenario.analytic_preset_id or "",
        "hetero_mode": scenario.hetero_mode,
        "migration_mode": scenario.migration_mode,
        "total_population": total_population,
        "treated_population": treated_population,
        "treated_share": treated_population / total_population if total_population else 0.0,
        "births": births,
        "deaths": deaths,
        "median_age": _weighted_median_age(combined),
        "old_age_share_60_plus": old_age_share_60,
        "old_age_share_65_plus": old_age_share_65,
        **rollout_metadata,
    }


def _assign_new_treated(
    state: ProjectionState,
    start_probabilities: np.ndarray,
    start_age_lookup: dict[int, int],
    ages: np.ndarray,
) -> ProjectionState:
    updated_untreated = {sex: state.untreated[sex].copy() for sex in SEXES}
    updated_treated = {sex: state.treated[sex].copy() for sex in SEXES}

    for sex in SEXES:
        for age_index, age in enumerate(ages):
            start_probability = float(start_probabilities[age_index])
            if start_probability <= 0.0:
                continue

            start_age_index = start_age_lookup.get(int(age))
            if start_age_index is None:
                continue

            new_treated = updated_untreated[sex][age_index] * start_probability
            updated_untreated[sex][age_index] -= new_treated
            updated_treated[sex][start_age_index, age_index] += new_treated

    return ProjectionState(
        untreated=updated_untreated,
        treated=updated_treated,
    )


def materialize_transition_operator(
    inputs: VariantInputs,
    scenario: ScenarioSpec,
    intervention_asset: InterventionAsset,
    year: int,
) -> dict[str, np.ndarray]:
    start_age_lookup = {int(age): index for index, age in enumerate(intervention_asset.start_ages)}
    start_probabilities = build_start_probability_table(
        scenario=scenario,
        years=[year],
        ages=inputs.ages,
    )[0]

    age_count = len(inputs.ages)
    start_age_count = len(intervention_asset.start_ages)
    untreated_to_untreated = np.zeros((age_count, age_count), dtype=float)
    untreated_to_treated = np.zeros((start_age_count * age_count, age_count), dtype=float)
    treated_to_treated = np.zeros((start_age_count * age_count, start_age_count * age_count), dtype=float)

    untreated_survival = annual_survival_from_mx(inputs.mortality[year]["female"])
    treated_survival = annual_survival_from_mx(
        inputs.mortality[year]["female"][None, :] * intervention_asset.annual_hazard_multiplier
    )

    for age in range(age_count):
        destination_age = min(age + 1, age_count - 1)
        start_probability = float(start_probabilities[age])

        untreated_to_untreated[destination_age, age] = (1.0 - start_probability) * untreated_survival[age]

        start_age_index = start_age_lookup.get(age)
        if start_age_index is None:
            continue

        treated_row = start_age_index * age_count + destination_age
        untreated_to_treated[treated_row, age] = start_probability * treated_survival[start_age_index, age]

    for start_age_index in range(start_age_count):
        for age in range(age_count):
            destination_age = min(age + 1, age_count - 1)
            source = start_age_index * age_count + age
            destination = start_age_index * age_count + destination_age
            treated_to_treated[destination, source] = treated_survival[start_age_index, age]

    return {
        "untreated_to_untreated": untreated_to_untreated,
        "untreated_to_treated": untreated_to_treated,
        "treated_to_treated": treated_to_treated,
        "female_birth_fertility": inputs.fertility[year].copy(),
    }


def project_scenario(
    scenario: ScenarioSpec,
    inputs: VariantInputs,
    intervention_asset: InterventionAsset,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = _select_projection_years(
        available_years=inputs.years,
        projection_end_year=scenario.projection_end_year,
    )
    ages = inputs.ages
    start_probability_table = build_start_probability_table(scenario, years, ages)
    start_age_lookup = {
        int(start_age): index
        for index, start_age in enumerate(intervention_asset.start_ages)
    }

    state = _blank_projection_state(
        initial_population=inputs.population[years[0]],
        start_age_count=len(intervention_asset.start_ages),
    )

    population_rows = _record_population_rows(scenario, years[0], state)
    summary_rows = [_record_summary_row(scenario, years[0], state, births=0.0, deaths=0.0)]

    for year_index, year in enumerate(years[:-1]):
        state_after_start = _assign_new_treated(
            state=state,
            start_probabilities=start_probability_table[year_index],
            start_age_lookup=start_age_lookup,
            ages=ages,
        )

        female_total = (
            state.untreated["female"]
            + _sum_treated_by_age(state.treated["female"])
        )
        male_births, female_births = compute_births(
            female_population=female_total,
            asfr=inputs.fertility[year],
            sex_ratio_at_birth=inputs.sex_ratio_at_birth[year],
        )
        births = male_births + female_births

        next_state = ProjectionState(
            untreated={sex: np.zeros(len(ages), dtype=float) for sex in SEXES},
            treated={sex: np.zeros_like(state_after_start.treated[sex]) for sex in SEXES},
        )

        deaths = 0.0
        for sex in SEXES:
            untreated_survival = annual_survival_from_mx(inputs.mortality[year][sex])
            treated_survival = annual_survival_from_mx(
                inputs.mortality[year][sex][None, :] * intervention_asset.annual_hazard_multiplier
            )

            untreated_survivors = state_after_start.untreated[sex] * untreated_survival
            treated_survivors = state_after_start.treated[sex] * treated_survival

            deaths += float(state_after_start.untreated[sex].sum() - untreated_survivors.sum())
            deaths += float(state_after_start.treated[sex].sum() - treated_survivors.sum())

            next_state.untreated[sex] += _age_survivors(untreated_survivors)
            next_state.treated[sex] += _age_treated_survivors(treated_survivors)

        next_state.untreated["male"][0] += male_births
        next_state.untreated["female"][0] += female_births

        if scenario.migration_mode == "on":
            next_state = _apply_migration_residual(
                state=next_state,
                residual=inputs.migration_residual.get(year),
                scenario=scenario,
                year=year,
            )

        state = next_state
        next_year = year + 1

        population_rows.extend(_record_population_rows(scenario, next_year, state))
        summary_rows.append(
            _record_summary_row(
                scenario=scenario,
                year=next_year,
                state=state,
                births=births,
                deaths=deaths,
            )
        )

    return pd.DataFrame(population_rows), pd.DataFrame(summary_rows)
