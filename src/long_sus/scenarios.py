from __future__ import annotations

from .config import (
    DEFAULT_ETA_FACTOR,
    DEFAULT_LAUNCH_YEAR,
    DEFAULT_PROJECTION_END_YEAR,
    DEFAULT_TARGET,
    DEFAULT_XC_FACTOR,
    ETA_FACTOR_GRID,
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


def _scheme_label(scheme_id: str) -> str:
    labels = {
        "no_one": "No one",
        "everyone": "Everyone",
        "only_elderly_65plus": "Only elderly (65+)",
        "50pct_elderly_65plus": "50% of elderly (65+)",
        "30pct_middle_40_64_plus_70pct_elderly_65plus": "30% middle age, 70% elderly",
        "half_population_adult_band": "Half of adult population",
        "prescription_bands_absolute": "Prescription bands / absolute",
        "prescription_bands_equal_probabilities": "Prescription bands / equal probabilities",
        "prescription_bands_uniform_start_age": "Prescription bands / uniform start age",
        "threshold_age_60_all_eligible": "Threshold age 60",
    }

    if scheme_id not in labels:
        raise KeyError(f"Unknown validation scheme: {scheme_id}")

    return labels[scheme_id]


def _scheme_definition(scheme_id: str) -> dict[str, object]:
    definitions: dict[str, dict[str, object]] = {
        "no_one": {
            "uptake_mode": "threshold",
            "threshold_age": None,
            "bands": (),
            "start_rule_within_band": "absolute",
        },
        "everyone": {
            "uptake_mode": "threshold",
            "threshold_age": 0,
            "bands": (),
            "start_rule_within_band": "deterministic_threshold",
        },
        "only_elderly_65plus": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "bands": ELDERLY_ONLY_BAND,
            "start_rule_within_band": "absolute",
        },
        "50pct_elderly_65plus": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "bands": HALF_ELDERLY_BAND,
            "start_rule_within_band": "absolute",
        },
        "30pct_middle_40_64_plus_70pct_elderly_65plus": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "bands": MIDDLE_AND_ELDERLY_BANDS,
            "start_rule_within_band": "absolute",
        },
        "half_population_adult_band": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "bands": HALF_ADULT_BAND,
            "start_rule_within_band": "absolute",
        },
        "prescription_bands_absolute": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "bands": USA_RX_AGE_BANDS,
            "start_rule_within_band": "absolute",
        },
        "prescription_bands_equal_probabilities": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "bands": USA_RX_AGE_BANDS,
            "start_rule_within_band": "equal_probabilities",
        },
        "prescription_bands_uniform_start_age": {
            "uptake_mode": "banded",
            "threshold_age": None,
            "bands": USA_RX_AGE_BANDS,
            "start_rule_within_band": "uniform_start_age",
        },
        "threshold_age_60_all_eligible": {
            "uptake_mode": "threshold",
            "threshold_age": 60,
            "bands": (),
            "start_rule_within_band": "deterministic_threshold",
        },
    }

    if scheme_id not in definitions:
        raise KeyError(f"Unknown validation scheme: {scheme_id}")

    return definitions[scheme_id]


def build_validation_scheme_catalog() -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []

    for scheme_id in VALIDATION_SCHEME_IDS:
        definition = _scheme_definition(scheme_id)
        catalog.append(
            {
                "id": scheme_id,
                "label": _scheme_label(scheme_id),
                "uptake_mode": definition["uptake_mode"],
                "threshold_age": definition["threshold_age"],
                "start_rule_within_band": definition["start_rule_within_band"],
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
        factor = DEFAULT_ETA_FACTOR if target == "eta" else DEFAULT_XC_FACTOR

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
        bands=tuple(definition["bands"]),
        start_rule_within_band=str(definition["start_rule_within_band"]),
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
