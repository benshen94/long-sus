from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.countries import list_supported_country_specs
from long_sus.intervention_assets import (
    build_analytic_preset_catalog_payload,
    require_country_analytic_preset,
    validate_supported_country_baseline_fits,
)
from long_sus.query import _validate_query
from long_sus.specs import ScenarioQuery


class CountryBaselineFitTests(unittest.TestCase):
    def test_high_age_weighting_covers_priority_countries(self) -> None:
        from scripts.build_baseline_fits import HIGH_AGE_WEIGHTING

        for slug in ("brazil", "china", "nigeria"):
            rule = HIGH_AGE_WEIGHTING.get(slug)
            self.assertIsNotNone(rule)
            self.assertEqual(rule["age_start"], 70)
            self.assertEqual(rule["age_end"], 90)
            self.assertGreaterEqual(rule["max_multiplier"], 18.0)

    def test_fit_builder_can_target_specific_countries(self) -> None:
        from scripts.build_baseline_fits import _resolve_selected_slugs

        self.assertEqual(
            _resolve_selected_slugs(["Brazil", "china", "nigeria"]),
            ["brazil", "china", "nigeria"],
        )

    def test_supported_country_baseline_fits_validate(self) -> None:
        validate_supported_country_baseline_fits()

    def test_every_supported_country_has_fit_diagnostic_png(self) -> None:
        missing_paths: list[str] = []

        for country in list_supported_country_specs():
            diagnostic_path = PROJECT_ROOT / "baseline_fits" / f"{country.slug}_fit_diagnostic.png"
            if diagnostic_path.exists():
                continue
            missing_paths.append(str(diagnostic_path))

        self.assertEqual(missing_paths, [])

    def test_every_supported_country_has_matching_dashboard_default_preset(self) -> None:
        manifest = json.loads((PROJECT_ROOT / "dashboard" / "assets" / "manifest.json").read_text())
        areas_by_slug = {area["slug"]: area for area in manifest["areas"]}

        for country in list_supported_country_specs():
            area = areas_by_slug[country.slug]
            self.assertEqual(area["default_analytic_preset_id"], country.default_analytic_preset_id)

            preset = require_country_analytic_preset(
                country=country.name,
                preset_id=country.default_analytic_preset_id,
            )
            self.assertEqual(preset["country"], country.name)
            self.assertEqual(int(preset["location_id"]), country.location_id)

            catalog = build_analytic_preset_catalog_payload(
                default_preset_id=country.default_analytic_preset_id,
                country=country.name,
                include_legacy=False,
            )
            self.assertEqual(catalog["default_preset_id"], country.default_analytic_preset_id)
            self.assertEqual([entry["id"] for entry in catalog["presets"]], [country.default_analytic_preset_id])

    def test_query_rejects_cross_country_analytic_preset(self) -> None:
        with self.assertRaisesRegex(ValueError, "belongs to China, not World"):
            _validate_query(
                ScenarioQuery(
                    country="World",
                    scheme_id="threshold_age_60_all_eligible",
                    target="eta",
                    factor=0.8,
                    branch="analytic_arm",
                    analytic_preset_id="china_period_2024_both_hazard",
                )
            )


if __name__ == "__main__":
    unittest.main()
