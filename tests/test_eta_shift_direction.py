from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.intervention_assets import build_analytic_intervention_asset
from long_sus.projection import VariantInputs

import numpy as np


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


class EtaShiftDirectionTest(unittest.TestCase):
    def test_eta_shift_factor_below_one_improves_survival(self) -> None:
        inputs = _toy_inputs()

        better = build_analytic_intervention_asset(
            inputs=inputs,
            target="eta_shift",
            factor=0.8,
            launch_year=2024,
            analytic_preset_id="usa_period_2019_both_hazard",
        )
        baseline = build_analytic_intervention_asset(
            inputs=inputs,
            target="eta_shift",
            factor=1.0,
            launch_year=2024,
            analytic_preset_id="usa_period_2019_both_hazard",
        )
        worse = build_analytic_intervention_asset(
            inputs=inputs,
            target="eta_shift",
            factor=1.2,
            launch_year=2024,
            analytic_preset_id="usa_period_2019_both_hazard",
        )

        row_index = 3
        self.assertGreater(
            better.survival_by_start_age[row_index, 5],
            baseline.survival_by_start_age[row_index, 5],
        )
        self.assertLess(
            worse.survival_by_start_age[row_index, 5],
            baseline.survival_by_start_age[row_index, 5],
        )


if __name__ == "__main__":
    unittest.main()
