from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .specs import AgeBandUptake, ScenarioSpec


@dataclass(frozen=True)
class ResolvedBand:
    start_age: int
    end_age: int
    target_share: float
    conditional_share: float


def _clamped_probability(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def rollout_probability_for_year(
    scenario: ScenarioSpec,
    year: int,
) -> float:
    if year < scenario.launch_year:
        return 0.0

    launch_probability = _clamped_probability(scenario.rollout_launch_probability)
    max_probability = _clamped_probability(max(scenario.rollout_max_probability, launch_probability))
    if max_probability <= launch_probability:
        return launch_probability

    years_since_launch = year - scenario.launch_year

    if scenario.rollout_curve == "linear":
        ramp_years = max(int(scenario.rollout_ramp_years), 1)
        progress = min(years_since_launch / ramp_years, 1.0)
        return launch_probability + ((max_probability - launch_probability) * progress)

    if scenario.rollout_curve == "logistic":
        takeoff_years = max(int(scenario.rollout_takeoff_years), 1)
        baseline = 1.0 / (1.0 + math.exp(0.5 * takeoff_years))
        current = 1.0 / (1.0 + math.exp(-0.5 * (years_since_launch - takeoff_years)))
        scaled = (current - baseline) / (1.0 - baseline)
        scaled = float(np.clip(scaled, 0.0, 1.0))
        return launch_probability + ((max_probability - launch_probability) * scaled)

    raise ValueError(f"Unsupported rollout curve: {scenario.rollout_curve}")


def resolve_age_bands(
    bands: tuple[AgeBandUptake, ...],
    max_age: int,
) -> list[ResolvedBand]:
    resolved: list[ResolvedBand] = []
    treated_before = 0.0

    for band in bands:
        end_age = max_age if band.end_age is None else band.end_age
        target_share = float(np.clip(band.target_share, 0.0, 1.0))

        if treated_before >= 1.0:
            conditional_share = 0.0
        elif target_share <= treated_before:
            conditional_share = 0.0
        else:
            conditional_share = (target_share - treated_before) / (1.0 - treated_before)

        resolved.append(
            ResolvedBand(
                start_age=band.start_age,
                end_age=end_age,
                target_share=target_share,
                conditional_share=float(np.clip(conditional_share, 0.0, 1.0)),
            )
        )
        treated_before = target_share

    return resolved


def _threshold_probability(age: int, year: int, scenario: ScenarioSpec) -> float:
    threshold_probability = _clamped_probability(scenario.threshold_probability)
    if scenario.threshold_age is None:
        return 0.0
    if year < scenario.launch_year:
        return 0.0
    if age < scenario.threshold_age:
        return 0.0
    if year == scenario.launch_year:
        return threshold_probability
    if age == scenario.threshold_age:
        return threshold_probability
    return 0.0


def _rollout_probability(age: int, year: int, scenario: ScenarioSpec) -> float:
    if scenario.threshold_age is None:
        return 0.0
    if year < scenario.launch_year:
        return 0.0
    if age < scenario.threshold_age:
        return 0.0
    return rollout_probability_for_year(scenario, year)


def _absolute_probability(age: int, year: int, scenario: ScenarioSpec, band: ResolvedBand) -> float:
    if year < scenario.launch_year:
        return 0.0
    if age < band.start_age or age > band.end_age:
        return 0.0
    if year == scenario.launch_year:
        return band.conditional_share
    if age == band.start_age:
        return band.conditional_share
    return 0.0


def _equal_probability(age: int, year: int, scenario: ScenarioSpec, band: ResolvedBand) -> float:
    if year < scenario.launch_year:
        return 0.0
    if age < band.start_age or age > band.end_age:
        return 0.0

    band_length = band.end_age - band.start_age + 1
    if band_length <= 0:
        return 0.0
    if band.conditional_share <= 0.0:
        return 0.0

    return 1.0 - (1.0 - band.conditional_share) ** (1.0 / band_length)


def _uniform_probability(age: int, year: int, scenario: ScenarioSpec, band: ResolvedBand) -> float:
    if year < scenario.launch_year:
        return 0.0
    if age < band.start_age or age > band.end_age:
        return 0.0

    band_length = band.end_age - band.start_age + 1
    if band_length <= 0:
        return 0.0
    if band.conditional_share <= 0.0:
        return 0.0

    age_index = age - band.start_age
    denominator = band_length - (band.conditional_share * age_index)
    if denominator <= 0.0:
        return 0.0

    return band.conditional_share / denominator


def start_probability_by_age(
    scenario: ScenarioSpec,
    age: int,
    year: int,
    max_age: int,
) -> float:
    if scenario.target is None:
        return 0.0

    if scenario.uptake_mode == "threshold":
        return _threshold_probability(age, year, scenario)

    if scenario.uptake_mode == "rollout":
        return _rollout_probability(age, year, scenario)

    if scenario.uptake_mode != "banded":
        raise ValueError(f"Unsupported uptake mode: {scenario.uptake_mode}")

    resolved_bands = resolve_age_bands(scenario.bands, max_age=max_age)
    for band in resolved_bands:
        if age < band.start_age or age > band.end_age:
            continue

        if scenario.start_rule_within_band == "absolute":
            return _absolute_probability(age, year, scenario, band)
        if scenario.start_rule_within_band == "equal_probabilities":
            return _equal_probability(age, year, scenario, band)
        if scenario.start_rule_within_band == "uniform_start_age":
            return _uniform_probability(age, year, scenario, band)
        raise ValueError(f"Unsupported start rule: {scenario.start_rule_within_band}")

    return 0.0


def build_start_probability_table(
    scenario: ScenarioSpec,
    years: list[int],
    ages: np.ndarray,
) -> np.ndarray:
    table = np.zeros((len(years), len(ages)), dtype=float)
    max_age = int(ages.max())

    for year_index, year in enumerate(years):
        for age_index, age in enumerate(ages):
            table[year_index, age_index] = start_probability_by_age(
                scenario=scenario,
                age=int(age),
                year=int(year),
                max_age=max_age,
            )

    return np.clip(table, 0.0, 1.0)


def build_lifetime_start_weights(
    scenario: ScenarioSpec,
    ages: np.ndarray,
) -> tuple[np.ndarray, float]:
    weights = np.zeros(len(ages), dtype=float)
    untreated_share = 1.0
    max_age = int(ages.max())

    if scenario.target is None:
        return weights, 1.0

    if scenario.uptake_mode == "threshold":
        if scenario.threshold_age is None:
            return weights, 1.0
        if scenario.threshold_age > max_age:
            return weights, 1.0
        threshold_probability = _clamped_probability(scenario.threshold_probability)
        weights[int(scenario.threshold_age)] = threshold_probability
        return weights, 1.0 - threshold_probability

    if scenario.uptake_mode == "rollout":
        if scenario.threshold_age is None:
            return weights, 1.0
        if scenario.threshold_age > max_age:
            return weights, 1.0

        for age in range(int(scenario.threshold_age), max_age + 1):
            if untreated_share <= 0.0:
                return weights, 0.0

            year = scenario.launch_year + age
            probability = rollout_probability_for_year(scenario, year)
            start_share = untreated_share * probability
            weights[age] += start_share
            untreated_share -= start_share

        untreated_share = float(np.clip(untreated_share, 0.0, 1.0))
        return weights, untreated_share

    resolved_bands = resolve_age_bands(scenario.bands, max_age=max_age)
    for band in resolved_bands:
        if untreated_share <= 0.0:
            return weights, 0.0

        if scenario.start_rule_within_band == "absolute":
            start_share = untreated_share * band.conditional_share
            weights[band.start_age] += start_share
            untreated_share -= start_share
            continue

        if scenario.start_rule_within_band == "equal_probabilities":
            yearly_probability = _equal_probability(
                age=band.start_age,
                year=scenario.launch_year + 1,
                scenario=scenario,
                band=band,
            )
        elif scenario.start_rule_within_band == "uniform_start_age":
            yearly_probability = None
        else:
            raise ValueError(f"Unsupported start rule: {scenario.start_rule_within_band}")

        for age in range(band.start_age, band.end_age + 1):
            if untreated_share <= 0.0:
                return weights, 0.0

            if scenario.start_rule_within_band == "equal_probabilities":
                probability = yearly_probability
            else:
                probability = _uniform_probability(
                    age=age,
                    year=scenario.launch_year + 1,
                    scenario=scenario,
                    band=band,
                )

            start_share = untreated_share * probability
            weights[age] += start_share
            untreated_share -= start_share

    untreated_share = float(np.clip(untreated_share, 0.0, 1.0))
    return weights, untreated_share
