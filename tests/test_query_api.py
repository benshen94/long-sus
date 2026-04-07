from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
import sys

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.catalog import build_analytic_catalog
from long_sus.countries import get_country_spec
from long_sus.query import (
    get_population_pyramid,
    get_population_size,
    list_supported_countries,
    list_supported_schemes,
    project_analytic_scenario,
)
from long_sus.scenarios import build_validation_scenario
from long_sus.specs import ScenarioQuery


def _build_test_catalog(path: Path) -> Path:
    usa_baseline = build_validation_scenario(
        "no_one",
        country="USA",
        branch="analytic_arm",
        analytic_preset_id="usa_period_2024_both_hazard",
    )
    world_xc = build_validation_scenario(
        "threshold_age_60_all_eligible",
        country="World",
        target="Xc",
        factor=1.2,
        branch="analytic_arm",
        analytic_preset_id="world_period_2024_both_hazard",
    )
    world_eta = build_validation_scenario(
        "threshold_age_60_all_eligible",
        country="World",
        target="eta",
        factor=0.8,
        branch="analytic_arm",
        analytic_preset_id="world_period_2024_both_hazard",
    )

    return build_analytic_catalog(
        path=path,
        countries=["USA", "World"],
        scenarios_by_country={
            "USA": [usa_baseline],
            "World": [world_xc, world_eta],
        },
        force=True,
    )


class QueryApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.catalog_path = _build_test_catalog(Path(self.temp_dir.name) / "analytic_catalog.sqlite")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_supported_country_and_scheme_lists_are_non_empty(self) -> None:
        countries = list_supported_countries()
        schemes = list_supported_schemes()

        self.assertTrue(any(country["country"] == "World" for country in countries))
        self.assertTrue(any(scheme["id"] == "threshold_age_60_all_eligible" for scheme in schemes))

    def test_country_registry_accepts_slug_and_display_name(self) -> None:
        self.assertEqual(get_country_spec("world").name, "World")
        self.assertEqual(get_country_spec("South Africa").slug, "south_africa")

    def test_invalid_none_target_combination_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            get_population_size(
                ScenarioQuery(
                    country="USA",
                    scheme_id="threshold_age_60_all_eligible",
                    target="none",
                    factor=1.0,
                    branch="analytic_arm",
                ),
                catalog_path=self.catalog_path,
            )

    def test_catalog_population_pyramid_query_returns_rows(self) -> None:
        query = ScenarioQuery(
            country="World",
            scheme_id="threshold_age_60_all_eligible",
            target="Xc",
            factor=1.2,
            branch="analytic_arm",
            year=2050,
            source="catalog",
        )

        frame = get_population_pyramid(query, catalog_path=self.catalog_path)

        self.assertFalse(frame.empty)
        self.assertEqual(set(frame["sex"]), {"male", "female"})
        self.assertTrue((frame["year"] == 2050).all())

    def test_on_demand_projection_matches_catalog_summary(self) -> None:
        query = ScenarioQuery(
            country="World",
            scheme_id="threshold_age_60_all_eligible",
            target="eta",
            factor=0.8,
            branch="analytic_arm",
            year=2050,
        )

        catalog_summary = get_population_size(
            ScenarioQuery(
                **{
                    **query.__dict__,
                    "source": "catalog",
                }
            ),
            catalog_path=self.catalog_path,
        )
        population_frame, summary_frame = project_analytic_scenario(
            ScenarioQuery(
                **{
                    **query.__dict__,
                    "source": "project",
                }
            )
        )

        self.assertFalse(population_frame.empty)
        self.assertFalse(summary_frame.empty)

        projected_row = summary_frame[summary_frame["year"] == 2050].reset_index(drop=True)
        catalog_row = catalog_summary.reset_index(drop=True)

        self.assertAlmostEqual(
            float(projected_row.loc[0, "total_population"]),
            float(catalog_row.loc[0, "total_population"]),
        )
        self.assertAlmostEqual(
            float(projected_row.loc[0, "old_age_share_65_plus"]),
            float(catalog_row.loc[0, "old_age_share_65_plus"]),
        )

    def test_readme_world_example_runs(self) -> None:
        query = ScenarioQuery(
            country="World",
            scheme_id="threshold_age_60_all_eligible",
            target="Xc",
            factor=1.2,
            branch="analytic_arm",
            year=2050,
        )

        pyramid = get_population_pyramid(query, catalog_path=self.catalog_path)
        size = get_population_size(query, catalog_path=self.catalog_path)

        self.assertFalse(pyramid.empty)
        self.assertFalse(size.empty)
