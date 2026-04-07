from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.projection import VariantInputs, project_scenario
from long_sus.scenarios import build_validation_scenario
from long_sus.intervention_assets import (
    build_analytic_intervention_asset,
    build_analytic_multiplier_row,
    build_analytic_preset_catalog_payload,
    build_all_sex_wpp_hazard,
    default_analytic_preset_id,
    get_analytic_preset,
)
from long_sus.specs import SRInterventionAsset
from long_sus.sr_intervention import build_sr_intervention_asset
from long_sus.specs import UsaCalibrationPreset


def _toy_inputs() -> VariantInputs:
    ages = np.arange(0, 6, dtype=int)
    years = [2024, 2025, 2026]

    population = {
        2024: {
            "male": np.array([10.0, 9.0, 8.0, 7.0, 6.0, 5.0]),
            "female": np.array([10.0, 9.0, 8.0, 7.0, 6.0, 5.0]),
        },
        2025: {
            "male": np.array([10.0, 10.0, 9.0, 8.0, 7.0, 11.0]),
            "female": np.array([10.0, 10.0, 9.0, 8.0, 7.0, 11.0]),
        },
        2026: {
            "male": np.array([10.0, 10.0, 10.0, 9.0, 8.0, 17.0]),
            "female": np.array([10.0, 10.0, 10.0, 9.0, 8.0, 17.0]),
        },
    }
    mortality = {
        2024: {
            "male": np.array([0.02, 0.02, 0.03, 0.04, 0.05, 0.10]),
            "female": np.array([0.02, 0.02, 0.03, 0.04, 0.05, 0.10]),
        },
        2025: {
            "male": np.array([0.02, 0.02, 0.03, 0.04, 0.05, 0.10]),
            "female": np.array([0.02, 0.02, 0.03, 0.04, 0.05, 0.10]),
        },
    }
    fertility = {
        2024: np.array([0.0, 0.0, 0.05, 0.05, 0.0, 0.0]),
        2025: np.array([0.0, 0.0, 0.05, 0.05, 0.0, 0.0]),
    }
    srb = {2024: 1.05, 2025: 1.05}
    migration = {2024: 0.0, 2025: 0.0}
    residual = {
        2024: {
            "male": np.zeros(6, dtype=float),
            "female": np.zeros(6, dtype=float),
        },
        2025: {
            "male": np.zeros(6, dtype=float),
            "female": np.zeros(6, dtype=float),
        },
    }

    return VariantInputs(
        variant_name="toy",
        years=years,
        ages=ages,
        population=population,
        mortality=mortality,
        fertility=fertility,
        sex_ratio_at_birth=srb,
        net_migration_total=migration,
        migration_residual=residual,
    )


def _toy_intervention_asset(active_multiplier: float = 0.80) -> SRInterventionAsset:
    start_ages = np.arange(0, 6, dtype=int)
    ages = np.arange(0, 6, dtype=int)
    multiplier = np.ones((6, 6), dtype=float)

    for start_age in range(6):
        for age in range(start_age, 6):
            multiplier[start_age, age] = active_multiplier

    baseline_survival = np.array([1.0, 0.95, 0.90, 0.80, 0.65, 0.45, 0.25], dtype=float)
    survival_rows = np.tile(baseline_survival, (6, 1))

    return SRInterventionAsset(
        target="eta",
        factor=0.80,
        hetero_mode="off",
        start_ages=start_ages,
        ages=ages,
        annual_hazard_multiplier=multiplier,
        baseline_survival=baseline_survival,
        survival_by_start_age=survival_rows,
    )


def _toy_demography_payload(inputs: VariantInputs) -> dict[str, object]:
    return {
        "variant_name": inputs.variant_name,
        "years": inputs.years,
        "ages": inputs.ages.astype(int).tolist(),
        "population": {
            str(year): {
                "male": values["male"].tolist(),
                "female": values["female"].tolist(),
            }
            for year, values in inputs.population.items()
        },
        "mortality": {
            str(year): {
                "male": values["male"].tolist(),
                "female": values["female"].tolist(),
            }
            for year, values in inputs.mortality.items()
        },
        "fertility": {str(year): values.tolist() for year, values in inputs.fertility.items()},
        "sex_ratio_at_birth": {str(year): value for year, value in inputs.sex_ratio_at_birth.items()},
        "net_migration_total": {str(year): value for year, value in inputs.net_migration_total.items()},
        "migration_residual": {
            str(year): {
                "male": values["male"].tolist(),
                "female": values["female"].tolist(),
            }
            for year, values in inputs.migration_residual.items()
        },
    }


class ValidationDashboardTest(unittest.TestCase):
    def test_world_analytic_preset_is_default(self) -> None:
        preset = get_analytic_preset(default_analytic_preset_id())
        catalog = build_analytic_preset_catalog_payload()

        self.assertEqual(preset["country"], "World")
        self.assertEqual(catalog["default_preset_id"], default_analytic_preset_id())

    def test_eta_factor_one_reproduces_baseline_surface(self) -> None:
        asset = build_sr_intervention_asset(
            preset=UsaCalibrationPreset(name="usa_2019", use_heterogeneity=False),
            target="eta",
            factor=1.0,
        )
        self.assertTrue(np.allclose(asset.annual_hazard_multiplier, 1.0))

    def test_xc_factor_one_reproduces_baseline_surface(self) -> None:
        asset = build_sr_intervention_asset(
            preset=UsaCalibrationPreset(name="usa_2019", use_heterogeneity=False),
            target="Xc",
            factor=1.0,
        )
        self.assertTrue(np.allclose(asset.annual_hazard_multiplier, 1.0))

    def test_effect_surface_is_identity_before_start_age(self) -> None:
        asset = build_sr_intervention_asset(
            preset=UsaCalibrationPreset(name="usa_2019", use_heterogeneity=False),
            target="eta",
            factor=0.8,
        )

        for start_age in (20, 40, 60):
            self.assertTrue(np.allclose(asset.annual_hazard_multiplier[start_age, :start_age], 1.0))
            self.assertAlmostEqual(asset.survival_by_start_age[start_age, start_age], asset.baseline_survival[start_age])

    def test_analytic_eta_factor_one_reproduces_identity_surface(self) -> None:
        inputs = _toy_inputs()
        asset = build_analytic_intervention_asset(
            inputs=inputs,
            target="eta",
            factor=1.0,
            launch_year=2024,
            analytic_preset_id="usa_period_2019_both_hazard",
        )

        self.assertTrue(np.allclose(asset.annual_hazard_multiplier, 1.0))

    def test_analytic_xc_factor_one_reproduces_identity_surface(self) -> None:
        inputs = _toy_inputs()
        asset = build_analytic_intervention_asset(
            inputs=inputs,
            target="Xc",
            factor=1.0,
            launch_year=2024,
            analytic_preset_id="usa_period_2019_both_hazard",
        )

        self.assertTrue(np.allclose(asset.annual_hazard_multiplier, 1.0))

    def test_analytic_effect_surface_is_identity_before_start_age(self) -> None:
        inputs = _toy_inputs()
        asset = build_analytic_intervention_asset(
            inputs=inputs,
            target="eta",
            factor=0.8,
            launch_year=2024,
            analytic_preset_id="usa_period_2019_both_hazard",
        )

        for start_age in (1, 3, 5):
            self.assertTrue(np.allclose(asset.annual_hazard_multiplier[start_age, :start_age], 1.0))

    def test_analytic_wpp_hazard_tail_stays_flat_after_last_observed_age(self) -> None:
        inputs = _toy_inputs()
        hazard = build_all_sex_wpp_hazard(inputs=inputs, year=2024)

        self.assertAlmostEqual(hazard[5], 0.10)

        extended_inputs = inputs.__class__(
            **{
                **inputs.__dict__,
                "ages": np.arange(0, 9, dtype=int),
                "population": {
                    2024: {
                        "male": np.array([10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 0.0, 0.0, 0.0]),
                        "female": np.array([10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 0.0, 0.0, 0.0]),
                    },
                    2025: {
                        "male": np.array([10.0, 10.0, 9.0, 8.0, 7.0, 11.0, 0.0, 0.0, 0.0]),
                        "female": np.array([10.0, 10.0, 9.0, 8.0, 7.0, 11.0, 0.0, 0.0, 0.0]),
                    },
                    2026: {
                        "male": np.array([10.0, 10.0, 10.0, 9.0, 8.0, 17.0, 0.0, 0.0, 0.0]),
                        "female": np.array([10.0, 10.0, 10.0, 9.0, 8.0, 17.0, 0.0, 0.0, 0.0]),
                    },
                },
                "mortality": {
                    2024: {
                        "male": np.array([0.02, 0.02, 0.03, 0.04, 0.05, 0.10, 0.0, 0.0, 0.0]),
                        "female": np.array([0.02, 0.02, 0.03, 0.04, 0.05, 0.10, 0.0, 0.0, 0.0]),
                    },
                    2025: {
                        "male": np.array([0.02, 0.02, 0.03, 0.04, 0.05, 0.10, 0.0, 0.0, 0.0]),
                        "female": np.array([0.02, 0.02, 0.03, 0.04, 0.05, 0.10, 0.0, 0.0, 0.0]),
                    },
                },
            }
        )
        extended_hazard = build_all_sex_wpp_hazard(inputs=extended_inputs, year=2024)

        self.assertTrue(np.allclose(extended_hazard[6:], extended_hazard[5]))

    def test_analytic_xc_multiplier_depends_on_attained_age_only(self) -> None:
        preset = get_analytic_preset("usa_period_2019_both_hazard")
        ages = np.arange(0, 8, dtype=int)

        row_age_2 = build_analytic_multiplier_row(
            target="Xc",
            factor=1.5,
            start_age=2,
            ages=ages,
            preset=preset,
        )
        row_age_4 = build_analytic_multiplier_row(
            target="Xc",
            factor=1.5,
            start_age=4,
            ages=ages,
            preset=preset,
        )

        self.assertTrue(np.allclose(row_age_2[4:], row_age_4[4:]))

    def test_analytic_eta_multiplier_depends_on_elapsed_time_only(self) -> None:
        preset = get_analytic_preset("usa_period_2019_both_hazard")
        ages = np.arange(0, 10, dtype=int)

        row_age_2 = build_analytic_multiplier_row(
            target="eta",
            factor=0.8,
            start_age=2,
            ages=ages,
            preset=preset,
        )
        row_age_4 = build_analytic_multiplier_row(
            target="eta",
            factor=0.8,
            start_age=4,
            ages=ages,
            preset=preset,
        )

        self.assertAlmostEqual(row_age_2[5], row_age_4[7])
        self.assertAlmostEqual(row_age_2[6], row_age_4[8])

    def test_no_one_matches_factor_one_threshold_projection(self) -> None:
        inputs = _toy_inputs()
        intervention_asset = _toy_intervention_asset(active_multiplier=1.0)

        baseline = build_validation_scenario("no_one")
        treated = build_validation_scenario(
            "threshold_age_60_all_eligible",
            target="eta",
            factor=1.00,
            projection_end_year=2026,
        )
        treated = treated.__class__(**{**treated.__dict__, "threshold_age": 3, "projection_end_year": 2026})

        baseline_population, _ = project_scenario(baseline, inputs, intervention_asset)
        treated_population, _ = project_scenario(treated, inputs, intervention_asset)

        self.assertTrue(
            np.allclose(
                baseline_population["population_count"].to_numpy(),
                treated_population["population_count"].to_numpy(),
            )
        )

    def test_different_start_schemes_diverge_when_effect_is_active(self) -> None:
        inputs = _toy_inputs()
        intervention_asset = _toy_intervention_asset()

        absolute = build_validation_scenario(
            "prescription_bands_absolute",
            target="eta",
            factor=0.80,
            projection_end_year=2026,
        )
        equal_prob = build_validation_scenario(
            "prescription_bands_equal_probabilities",
            target="eta",
            factor=0.80,
            projection_end_year=2026,
        )

        absolute = absolute.__class__(
            **{
                **absolute.__dict__,
                "bands": (
                    absolute.bands[0].__class__(start_age=1, end_age=2, target_share=0.50),
                    absolute.bands[1].__class__(start_age=3, end_age=5, target_share=0.90),
                ),
            }
        )
        equal_prob = equal_prob.__class__(
            **{
                **equal_prob.__dict__,
                "bands": absolute.bands,
            }
        )

        _, absolute_summary = project_scenario(absolute, inputs, intervention_asset)
        _, equal_summary = project_scenario(equal_prob, inputs, intervention_asset)

        absolute_2026 = absolute_summary[absolute_summary["year"] == 2026]["treated_share"].iloc[0]
        equal_2026 = equal_summary[equal_summary["year"] == 2026]["treated_share"].iloc[0]
        self.assertNotAlmostEqual(absolute_2026, equal_2026)

    def test_js_runtime_matches_python_projection(self) -> None:
        inputs = _toy_inputs()
        intervention_asset = _toy_intervention_asset()
        scenario = build_validation_scenario(
            "threshold_age_60_all_eligible",
            target="eta",
            factor=0.80,
            projection_end_year=2026,
        )
        scenario = scenario.__class__(
            **{
                **scenario.__dict__,
                "threshold_age": 3,
                "projection_end_year": 2026,
            }
        )

        python_population, python_summary = project_scenario(scenario, inputs, intervention_asset)

        payload = {
            "inputs": _toy_demography_payload(inputs),
            "scenario": scenario.__dict__,
            "interventionAsset": {
                "target": intervention_asset.target,
                "factor": intervention_asset.factor,
                "hetero_mode": intervention_asset.hetero_mode,
                "start_ages": intervention_asset.start_ages.astype(int).tolist(),
                "ages": intervention_asset.ages.astype(int).tolist(),
                "annual_hazard_multiplier": intervention_asset.annual_hazard_multiplier.tolist(),
                "baseline_survival": intervention_asset.baseline_survival.tolist(),
                "survival_by_start_age": intervention_asset.survival_by_start_age.tolist(),
            },
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            payload_path = Path(handle.name)
            handle.write(json.dumps(payload))

        try:
            result = subprocess.run(
                ["node", "tests/js_helpers/run_projection_parity.mjs", str(payload_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            payload_path.unlink(missing_ok=True)

        js_output = json.loads(result.stdout)
        js_population = js_output["populationRows"]
        js_summary = js_output["summaryRows"]

        self.assertEqual(len(js_population), len(python_population))
        self.assertEqual(len(js_summary), len(python_summary))

        python_population_counts = python_population["population_count"].round(8).tolist()
        js_population_counts = [round(row["population_count"], 8) for row in js_population]
        self.assertEqual(python_population_counts, js_population_counts)

        python_treated = python_population["treated_population_count"].round(8).tolist()
        js_treated = [round(row["treated_population_count"], 8) for row in js_population]
        self.assertEqual(python_treated, js_treated)

        python_summary_totals = python_summary["total_population"].round(8).tolist()
        js_summary_totals = [round(row["total_population"], 8) for row in js_summary]
        self.assertEqual(python_summary_totals, js_summary_totals)

    def test_js_analytic_asset_matches_python_asset(self) -> None:
        inputs = _toy_inputs()
        python_asset = build_analytic_intervention_asset(
            inputs=inputs,
            target="eta",
            factor=0.8,
            launch_year=2024,
            analytic_preset_id="usa_period_2019_both_hazard",
        )

        payload = {
            "demography": _toy_demography_payload(inputs),
            "target": "eta",
            "factor": 0.8,
            "launchYear": 2024,
            "analyticPreset": get_analytic_preset("usa_period_2019_both_hazard"),
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            payload_path = Path(handle.name)
            handle.write(json.dumps(payload))

        try:
            result = subprocess.run(
                ["node", "tests/js_helpers/build_analytic_asset.mjs", str(payload_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            payload_path.unlink(missing_ok=True)

        js_asset = json.loads(result.stdout)

        self.assertTrue(np.allclose(python_asset.annual_hazard_multiplier, np.asarray(js_asset["annual_hazard_multiplier"])))
        self.assertTrue(np.allclose(python_asset.baseline_survival, np.asarray(js_asset["baseline_survival"])))
        self.assertTrue(np.allclose(python_asset.survival_by_start_age, np.asarray(js_asset["survival_by_start_age"])))

    def test_js_projection_parity_with_analytic_asset(self) -> None:
        inputs = _toy_inputs()
        scenario = build_validation_scenario(
            "threshold_age_60_all_eligible",
            target="eta",
            factor=0.80,
            projection_end_year=2026,
            branch="analytic_arm",
            analytic_preset_id="usa_period_2019_both_hazard",
        )
        scenario = scenario.__class__(
            **{
                **scenario.__dict__,
                "threshold_age": 3,
                "projection_end_year": 2026,
            }
        )
        intervention_asset = build_analytic_intervention_asset(
            inputs=inputs,
            target="eta",
            factor=0.8,
            launch_year=2024,
            analytic_preset_id="usa_period_2019_both_hazard",
        )

        python_population, python_summary = project_scenario(scenario, inputs, intervention_asset)

        payload = {
            "inputs": _toy_demography_payload(inputs),
            "scenario": scenario.__dict__,
            "interventionAsset": {
                "target": intervention_asset.target,
                "factor": intervention_asset.factor,
                "hetero_mode": intervention_asset.hetero_mode,
                "start_ages": intervention_asset.start_ages.astype(int).tolist(),
                "ages": intervention_asset.ages.astype(int).tolist(),
                "annual_hazard_multiplier": intervention_asset.annual_hazard_multiplier.tolist(),
                "baseline_survival": intervention_asset.baseline_survival.tolist(),
                "survival_by_start_age": intervention_asset.survival_by_start_age.tolist(),
            },
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            payload_path = Path(handle.name)
            handle.write(json.dumps(payload))

        try:
            result = subprocess.run(
                ["node", "tests/js_helpers/run_projection_parity.mjs", str(payload_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            payload_path.unlink(missing_ok=True)

        js_output = json.loads(result.stdout)

        self.assertEqual(
            python_population["population_count"].round(8).tolist(),
            [round(row["population_count"], 8) for row in js_output["populationRows"]],
        )
        self.assertEqual(
            python_summary["total_population"].round(8).tolist(),
            [round(row["total_population"], 8) for row in js_output["summaryRows"]],
        )

    def test_intervention_store_lazy_loads_sr_and_caches_results(self) -> None:
        inputs = _toy_inputs()
        payload = {
            "manifest": {
                "default_analytic_preset_id": default_analytic_preset_id(),
                "paths": {
                    "sr_interventions_root": "https://example.test/interventions/sr",
                },
            },
            "demography": _toy_demography_payload(inputs),
            "analyticPresets": build_analytic_preset_catalog_payload(),
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            payload_path = Path(handle.name)
            handle.write(json.dumps(payload))

        try:
            result = subprocess.run(
                ["node", "tests/js_helpers/check_intervention_store.mjs", str(payload_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            payload_path.unlink(missing_ok=True)

        checks = json.loads(result.stdout)
        self.assertEqual(checks["fetchCount"], 1)
        self.assertEqual(checks["srUrl"], "https://example.test/interventions/sr/eta/off/0.80.json")
        self.assertEqual(checks["analyticFetchCount"], 1)


if __name__ == "__main__":
    unittest.main()
