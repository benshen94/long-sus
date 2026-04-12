from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.scenarios import USA_RX_AGE_BANDS
from long_sus.config import MAX_AGE
from long_sus.specs import ScenarioSpec
from long_sus.uptake import (
    build_lifetime_start_weights,
    resolve_age_bands,
    start_probability_by_age,
)


class UptakeTest(unittest.TestCase):
    def test_age_band_resolution_matches_pdf_conditional_logic(self) -> None:
        resolved = resolve_age_bands(USA_RX_AGE_BANDS, max_age=MAX_AGE)

        self.assertTrue(math.isclose(resolved[0].conditional_share, 0.35))
        self.assertTrue(math.isclose(resolved[1].conditional_share, (0.65 - 0.35) / (1.0 - 0.35)))
        self.assertTrue(math.isclose(resolved[2].conditional_share, (0.95 - 0.65) / (1.0 - 0.65)))

    def test_absolute_rule_applies_at_launch_inside_band(self) -> None:
        scenario = ScenarioSpec(
            name="absolute_test",
            launch_year=2025,
            uptake_mode="banded",
            bands=USA_RX_AGE_BANDS,
            start_rule_within_band="absolute",
            target="eta",
            factor=0.80,
        )

        probability = start_probability_by_age(scenario, age=35, year=2025, max_age=MAX_AGE)
        self.assertTrue(math.isclose(probability, 0.35))

    def test_equal_probabilities_rule_uses_constant_band_probability(self) -> None:
        scenario = ScenarioSpec(
            name="equal_test",
            launch_year=2025,
            uptake_mode="banded",
            bands=USA_RX_AGE_BANDS,
            start_rule_within_band="equal_probabilities",
            target="eta",
            factor=0.80,
        )

        expected = 1.0 - (1.0 - 0.35) ** (1.0 / 20.0)
        probability = start_probability_by_age(scenario, age=20, year=2026, max_age=MAX_AGE)
        self.assertTrue(math.isclose(probability, expected))

    def test_uniform_rule_matches_pdf_formula(self) -> None:
        scenario = ScenarioSpec(
            name="uniform_test",
            launch_year=2025,
            uptake_mode="banded",
            bands=USA_RX_AGE_BANDS,
            start_rule_within_band="uniform_start_age",
            target="eta",
            factor=0.80,
        )

        probability_age_20 = start_probability_by_age(scenario, age=20, year=2026, max_age=MAX_AGE)
        probability_age_21 = start_probability_by_age(scenario, age=21, year=2026, max_age=MAX_AGE)

        self.assertTrue(math.isclose(probability_age_20, 0.35 / 20.0))
        self.assertTrue(math.isclose(probability_age_21, 0.35 / (20.0 - 0.35)))

    def test_threshold_rule_starts_current_and_future_eligible_cohorts(self) -> None:
        scenario = ScenarioSpec(
            name="threshold_test",
            launch_year=2025,
            uptake_mode="threshold",
            threshold_age=60,
            threshold_probability=0.5,
            target="eta",
            factor=0.80,
        )

        self.assertEqual(start_probability_by_age(scenario, age=75, year=2025, max_age=MAX_AGE), 0.5)
        self.assertEqual(start_probability_by_age(scenario, age=60, year=2030, max_age=MAX_AGE), 0.5)
        self.assertEqual(start_probability_by_age(scenario, age=59, year=2030, max_age=MAX_AGE), 0.0)

    def test_threshold_lifetime_weights_keep_untreated_remainder(self) -> None:
        scenario = ScenarioSpec(
            name="threshold_weights",
            launch_year=2025,
            uptake_mode="threshold",
            threshold_age=60,
            threshold_probability=0.5,
            target="eta",
            factor=0.80,
        )

        weights, untreated_share = build_lifetime_start_weights(
            scenario=scenario,
            ages=np.arange(0, MAX_AGE + 1, dtype=int),
        )

        self.assertTrue(math.isclose(weights[60], 0.5))
        self.assertTrue(math.isclose(untreated_share, 0.5))

    def test_lifetime_weights_for_absolute_bands_leave_untreated_remainder(self) -> None:
        scenario = ScenarioSpec(
            name="weights_test",
            launch_year=2025,
            uptake_mode="banded",
            bands=USA_RX_AGE_BANDS,
            start_rule_within_band="absolute",
            target="eta",
            factor=0.80,
        )

        weights, untreated_share = build_lifetime_start_weights(
            scenario=scenario,
            ages=np.arange(0, MAX_AGE + 1, dtype=int),
        )

        self.assertTrue(math.isclose(weights[20], 0.35))
        self.assertTrue(math.isclose(weights[40], 0.30))
        self.assertTrue(math.isclose(weights[65], 0.30))
        self.assertTrue(math.isclose(untreated_share, 0.05))


if __name__ == "__main__":
    unittest.main()
