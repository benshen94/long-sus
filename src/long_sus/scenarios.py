from __future__ import annotations

from .config import (
    DEFAULT_ETA_FACTOR,
    DEFAULT_ETA_SHIFT_FACTOR,
    DEFAULT_LAUNCH_YEAR,
    DEFAULT_PROJECTION_END_YEAR,
    DEFAULT_ROLLOUT_CURVE,
    DEFAULT_ROLLOUT_LAUNCH_PROBABILITY,
    DEFAULT_ROLLOUT_MAX_PROBABILITY,
    DEFAULT_ROLLOUT_RAMP_YEARS,
    DEFAULT_ROLLOUT_TAKEOFF_YEARS,
    DEFAULT_TARGET,
    DEFAULT_XC_FACTOR,
    ETA_FACTOR_GRID,
    ETA_SHIFT_FACTOR_GRID,
    VALIDATION_SCHEME_IDS,
    XC_FACTOR_GRID,
)
from .intervention_assets import ANALYTIC_BRANCH, SR_BRANCH, default_analytic_preset_id
from .specs import AgeBandUptake, ScenarioSpec


USA_RX_AGE_BANDS = (
    AgeBandUptake(start_age=20, end_age=39, target_share=0.35),
    AgeBandUptake(start_age=40, end_age=64, target_share=0.65),
    AgeBandUptake(start_age=65, end_age=None, target_share=0.95),
)

ELDERLY_ONLY_BAND = (
    AgeBandUptake(start_age=65, end_age=None, target_share=1.0),
)

HALF_ELDERLY_BAND = (
    AgeBandUptake(start_age=65, end_age=None, target_share=0.50),
)

MIDDLE_AND_ELDERLY_BANDS = (
    AgeBandUptake(start_age=40, end_age=64, target_share=0.30),
    AgeBandUptake(start_age=65, end_age=None, target_share=0.70),
)

HALF_ADULT_BAND = (
    AgeBandUptake(start_age=20, end_age=None, target_share=0.50),
)

ROLLOUT_THRESHOLD_AGE = 60


def _rollout_definition(curve: str) -> dict[str, object]:
    definition = {
        "uptake_mode": "rollout",
        "threshold_age": ROLLOUT_THRESHOLD_AGE,
        "threshold_probability": 1.0,
        "bands": (),
        "start_rule_within_band": "deterministic_threshold",
        "rollout_curve": curve,
        "rollout_launch_probability": DEFAULT_ROLLOUT_LAUNCH_PROBABILITY,
        "rollout_max_probability": DEFAULT_ROLLOUT_MAX_PROBABILITY,
        "rollout_ramp_years": DEFAULT_ROLLOUT_RAMP_YEARS,
        "rollout_takeoff_years": DEFAULT_ROLLOUT_TAKEOFF_YEARS,
    }
    return definition


def _apply_rollout_defaults(definition: dict[str, object]) -> dict[str, object]:
    updated = dict(definition)
    updated.setdefault("rollout_curve", DEFAULT_ROLLOUT_CURVE)
    updated.setdefault("rollout_launch_probability", DEFAULT_ROLLOUT_LAUNCH_PROBABILITY)
    updated.setdefault("rollout_max_probability", DEFAULT_ROLLOUT_MAX_PROBABILITY)
    updated.setdefault("rollout_ramp_years", DEFAULT_ROLLOUT_RAMP_YEARS)
    updated.setdefault("rollout_takeoff_years", DEFAULT_ROLLOUT_TAKEOFF_YEARS)
    return updated


def _scheme_label(scheme_id: str) -> str:
    labels = {
        "no_one": "No treatment",
        "everyone": "Treat everyone immediately",
        "only_elderly_65plus": "Treat ages 65+",
        "50pct_elderly_65plus": "Treat 50% of ages 65+",
        "30pct_middle_40_64_plus_70pct_elderly_65plus": "Treat 30% of ages 40-64 and 70% of ages 65+",
        "half_population_adult_band": "Treat 50% of all adults 20+",
        "prescription_bands_absolute": "Age bands with immediate starts",
        "prescription_bands_equal_probabilities": "Age bands with equal yearly start chance",
        "prescription_bands_uniform_start_age": "Age bands with uniform realized start age",
        "threshold_age_60_all_eligible": "Treat everyone from age 60 onward",
        "rollout_threshold_linear": "Rollout from age 60 with a linear popularity ramp",
        "rollout_threshold_logistic": "Rollout from age 60 with an S-curve popularity ramp",
    }

    if scheme_id not in labels:
        raise KeyError(f"Unknown validation scheme: {scheme_id}")

    return labels[scheme_id]


def _scheme_description(scheme_id: str) -> str:
    descriptions = {
        "no_one": "Untreated baseline. No one ever starts treatment.",
        "everyone": "Everyone alive at launch starts immediately, and all later births are treated from birth.",
        "only_elderly_65plus": "Only the 65+ band is eligible. Everyone in that band starts at the lower band edge.",
        "50pct_elderly_65plus": "Only the 65+ band is eligible, and the long-run treated share in that band is 50%.",
        "30pct_middle_40_64_plus_70pct_elderly_65plus": "A middle-age band targets 30% treated and the elderly band targets 70% treated.",
        "half_population_adult_band": "One adult band covers ages 20+ and targets a 50% treated share.",
        "prescription_bands_absolute": "Three age bands use fixed treated shares. Eligible people start at the band edge instead of being spread through the band.",
        "prescription_bands_equal_probabilities": "Three age bands use fixed treated shares, and starts are spread across ages using the same yearly start chance within each band.",
        "prescription_bands_uniform_start_age": "Three age bands use fixed treated shares, and the yearly start chance is tuned so realized start ages are uniform within each band.",
        "threshold_age_60_all_eligible": "Threshold age 60 with 100% uptake. Everyone already age 60+ starts at launch, and younger cohorts start when they reach age 60.",
        "rollout_threshold_linear": "Threshold age 60 with once-on adoption that becomes more common over calendar time. The annual start chance rises linearly from 10% at launch to 50% after 12 years.",
        "rollout_threshold_logistic": "Threshold age 60 with once-on adoption that becomes more common over calendar time. The annual start chance follows an S-curve, rising from 10% at launch toward 50% with an 8-year takeoff.",
    }

    if scheme_id not in descriptions:
        raise KeyError(f"Unknown validation scheme: {scheme_id}")

    return descriptions[scheme_id]


def _scheme_definition(scheme_id: str) -> dict[str, object]:
    definitions: dict[str, dict[str, object]] = {
        "no_one": {
            "uptake_mode": "threshold",
            "threshold_age": None,
            "threshold_probability": 1.0,
            "bands": (),
            "start_rule_within_band": "absolute",
        },
        "everyone": {
            "uptake_mode": "threshold",
            "threshold_age": 0,
            "threshold_probability": 1.0,
            "bands": (),
            "start_rule_within_band": "deterministic_threshold",
        },
        "only_elderly_65plus": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "threshold_probability": 1.0,
            "bands": ELDERLY_ONLY_BAND,
            "start_rule_within_band": "absolute",
        },
        "50pct_elderly_65plus": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "threshold_probability": 1.0,
            "bands": HALF_ELDERLY_BAND,
            "start_rule_within_band": "absolute",
        },
        "30pct_middle_40_64_plus_70pct_elderly_65plus": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "threshold_probability": 1.0,
            "bands": MIDDLE_AND_ELDERLY_BANDS,
            "start_rule_within_band": "absolute",
        },
        "half_population_adult_band": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "threshold_probability": 1.0,
            "bands": HALF_ADULT_BAND,
            "start_rule_within_band": "absolute",
        },
        "prescription_bands_absolute": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "threshold_probability": 1.0,
            "bands": USA_RX_AGE_BANDS,
            "start_rule_within_band": "absolute",
        },
        "prescription_bands_equal_probabilities": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "threshold_probability": 1.0,
            "bands": USA_RX_AGE_BANDS,
            "start_rule_within_band": "equal_probabilities",
        },
        "prescription_bands_uniform_start_age": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "threshold_probability": 1.0,
            "bands": USA_RX_AGE_BANDS,
            "start_rule_within_band": "uniform_start_age",
        },
        "threshold_age_60_all_eligible": {
            "uptake_mode": "threshold",
            "threshold_age": 60,
            "threshold_probability": 1.0,
            "bands": (),
            "start_rule_within_band": "deterministic_threshold",
            "rollout_curve": DEFAULT_ROLLOUT_CURVE,
            "rollout_launch_probability": DEFAULT_ROLLOUT_LAUNCH_PROBABILITY,
            "rollout_max_probability": DEFAULT_ROLLOUT_MAX_PROBABILITY,
            "rollout_ramp_years": DEFAULT_ROLLOUT_RAMP_YEARS,
            "rollout_takeoff_years": DEFAULT_ROLLOUT_TAKEOFF_YEARS,
        },
        "rollout_threshold_linear": _rollout_definition("linear"),
        "rollout_threshold_logistic": _rollout_definition("logistic"),
    }

    if scheme_id not in definitions:
        raise KeyError(f"Unknown validation scheme: {scheme_id}")

    return _apply_rollout_defaults(definitions[scheme_id])


def build_validation_scheme_catalog() -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []

    for scheme_id in VALIDATION_SCHEME_IDS:
        definition = _scheme_definition(scheme_id)
        catalog.append(
            {
                "id": scheme_id,
                "label": _scheme_label(scheme_id),
                "description": _scheme_description(scheme_id),
                "uptake_mode": definition["uptake_mode"],
                "threshold_age": definition["threshold_age"],
                "threshold_probability": definition["threshold_probability"],
                "start_rule_within_band": definition["start_rule_within_band"],
                "rollout_curve": definition["rollout_curve"],
                "rollout_launch_probability": definition["rollout_launch_probability"],
                "rollout_max_probability": definition["rollout_max_probability"],
                "rollout_ramp_years": definition["rollout_ramp_years"],
                "rollout_takeoff_years": definition["rollout_takeoff_years"],
                "bands": [
                    {
                        "start_age": band.start_age,
                        "end_age": band.end_age,
                        "target_share": band.target_share,
                    }
                    for band in definition["bands"]
                ],
            }
        )

    return catalog


def build_validation_scenario(
    scheme_id: str,
    *,
    country: str = "USA",
    target: str = DEFAULT_TARGET,
    factor: float | None = None,
    launch_year: int = DEFAULT_LAUNCH_YEAR,
    projection_end_year: int = DEFAULT_PROJECTION_END_YEAR,
    branch: str = SR_BRANCH,
    analytic_preset_id: str | None = None,
    hetero_mode: str = "off",
) -> ScenarioSpec:
    definition = _scheme_definition(scheme_id)

    if factor is None:
        if target == "eta":
            factor = DEFAULT_ETA_FACTOR
        elif target == "eta_shift":
            factor = DEFAULT_ETA_SHIFT_FACTOR
        else:
            factor = DEFAULT_XC_FACTOR

    if scheme_id == "no_one":
        if branch == ANALYTIC_BRANCH and analytic_preset_id is None:
            analytic_preset_id = default_analytic_preset_id()

        scenario_name = "no_one"
        if branch == ANALYTIC_BRANCH:
            scenario_name = f"no_one_{branch}_{analytic_preset_id}"
        elif hetero_mode == "on":
            scenario_name = "no_one_hetero"

        return ScenarioSpec(
            name=scenario_name,
            label=_scheme_label(scheme_id),
            scheme_id=scheme_id,
            country=country,
            launch_year=launch_year,
            projection_end_year=projection_end_year,
            uptake_mode="threshold",
            threshold_age=None,
            threshold_probability=1.0,
            rollout_curve=DEFAULT_ROLLOUT_CURVE,
            rollout_launch_probability=DEFAULT_ROLLOUT_LAUNCH_PROBABILITY,
            rollout_max_probability=DEFAULT_ROLLOUT_MAX_PROBABILITY,
            rollout_ramp_years=DEFAULT_ROLLOUT_RAMP_YEARS,
            rollout_takeoff_years=DEFAULT_ROLLOUT_TAKEOFF_YEARS,
            target=None,
            factor=1.0,
            branch=branch,
            analytic_preset_id=analytic_preset_id,
            hetero_mode=hetero_mode if branch == SR_BRANCH else "off",
        )

    if branch == ANALYTIC_BRANCH and analytic_preset_id is None:
        analytic_preset_id = default_analytic_preset_id()

    scenario_name = f"{scheme_id}_{target}_{factor:.2f}x"
    if branch == ANALYTIC_BRANCH:
        scenario_name = f"{scheme_id}_{branch}_{analytic_preset_id}_{target}_{factor:.2f}x"
    elif hetero_mode == "on":
        scenario_name = f"{scenario_name}_hetero"

    return ScenarioSpec(
        name=scenario_name,
        label=_scheme_label(scheme_id),
        scheme_id=scheme_id,
        country=country,
        launch_year=launch_year,
        projection_end_year=projection_end_year,
        uptake_mode=str(definition["uptake_mode"]),
        threshold_age=definition["threshold_age"],
        threshold_probability=float(definition["threshold_probability"]),
        bands=tuple(definition["bands"]),
        start_rule_within_band=str(definition["start_rule_within_band"]),
        rollout_curve=str(definition["rollout_curve"]),
        rollout_launch_probability=float(definition["rollout_launch_probability"]),
        rollout_max_probability=float(definition["rollout_max_probability"]),
        rollout_ramp_years=int(definition["rollout_ramp_years"]),
        rollout_takeoff_years=int(definition["rollout_takeoff_years"]),
        target=target,
        factor=float(factor),
        branch=branch,
        analytic_preset_id=analytic_preset_id,
        hetero_mode=hetero_mode if branch == SR_BRANCH else "off",
    )


def build_readme_scenarios() -> list[ScenarioSpec]:
    scenarios: list[ScenarioSpec] = [
        build_validation_scenario("no_one"),
        build_validation_scenario("threshold_age_60_all_eligible", target="eta", factor=1.00),
        build_validation_scenario("threshold_age_60_all_eligible", target="eta", factor=0.95),
        build_validation_scenario("threshold_age_60_all_eligible", target="eta", factor=0.90),
        build_validation_scenario("threshold_age_60_all_eligible", target="eta", factor=0.85),
        build_validation_scenario("threshold_age_60_all_eligible", target="eta", factor=0.80),
        build_validation_scenario("threshold_age_60_all_eligible", target="eta", factor=0.75),
        build_validation_scenario("threshold_age_60_all_eligible", target="eta", factor=0.70),
        build_validation_scenario("threshold_age_60_all_eligible", target="Xc", factor=1.00),
        build_validation_scenario("threshold_age_60_all_eligible", target="Xc", factor=1.10),
        build_validation_scenario("threshold_age_60_all_eligible", target="Xc", factor=1.20),
        build_validation_scenario("threshold_age_60_all_eligible", target="eta", factor=0.80, hetero_mode="on"),
        build_validation_scenario("everyone", target="eta", factor=0.80),
        build_validation_scenario("only_elderly_65plus", target="eta", factor=0.80),
        build_validation_scenario("50pct_elderly_65plus", target="eta", factor=0.80),
        build_validation_scenario("30pct_middle_40_64_plus_70pct_elderly_65plus", target="eta", factor=0.80),
        build_validation_scenario("half_population_adult_band", target="eta", factor=0.80),
        build_validation_scenario("prescription_bands_absolute", target="eta", factor=0.80),
        build_validation_scenario("prescription_bands_equal_probabilities", target="eta", factor=0.80),
        build_validation_scenario("prescription_bands_uniform_start_age", target="eta", factor=0.80),
    ]
    return scenarios


def build_dashboard_factor_grid() -> dict[str, tuple[float, ...]]:
    return {
        "eta": ETA_FACTOR_GRID,
        "eta_shift": ETA_SHIFT_FACTOR_GRID,
        "Xc": XC_FACTOR_GRID,
    }


def build_public_catalog_scenarios(
    *,
    country: str,
    branch: str = ANALYTIC_BRANCH,
    analytic_preset_id: str | None = None,
    launch_year: int = DEFAULT_LAUNCH_YEAR,
    projection_end_year: int = DEFAULT_PROJECTION_END_YEAR,
) -> list[ScenarioSpec]:
    scenarios: list[ScenarioSpec] = [
        build_validation_scenario(
            "no_one",
            country=country,
            branch=branch,
            analytic_preset_id=analytic_preset_id,
            launch_year=launch_year,
            projection_end_year=projection_end_year,
        )
    ]

    for scheme_id in VALIDATION_SCHEME_IDS:
        if scheme_id == "no_one":
            continue

        for factor in ETA_FACTOR_GRID:
            scenarios.append(
                build_validation_scenario(
                    scheme_id,
                    country=country,
                    target="eta",
                    factor=float(factor),
                    branch=branch,
                    analytic_preset_id=analytic_preset_id,
                    launch_year=launch_year,
                    projection_end_year=projection_end_year,
                )
            )

        for factor in ETA_SHIFT_FACTOR_GRID:
            scenarios.append(
                build_validation_scenario(
                    scheme_id,
                    country=country,
                    target="eta_shift",
                    factor=float(factor),
                    branch=branch,
                    analytic_preset_id=analytic_preset_id,
                    launch_year=launch_year,
                    projection_end_year=projection_end_year,
                )
            )

        for factor in XC_FACTOR_GRID:
            scenarios.append(
                build_validation_scenario(
                    scheme_id,
                    country=country,
                    target="Xc",
                    factor=float(factor),
                    branch=branch,
                    analytic_preset_id=analytic_preset_id,
                    launch_year=launch_year,
                    projection_end_year=projection_end_year,
                )
            )

    return scenarios
