from __future__ import annotations

import numpy as np
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.projection import (
    VariantInputs,
    derive_migration_residuals,
    project_one_year_no_migration,
)


class ProjectionTest(unittest.TestCase):
    def test_migration_residual_restores_target_population(self) -> None:
        ages = np.arange(0, 101, dtype=int)
        current = {
            "male": np.zeros(101, dtype=float),
            "female": np.zeros(101, dtype=float),
        }
        current["male"][30] = 100.0
        current["female"][30] = 110.0

        target = {
            "male": np.zeros(101, dtype=float),
            "female": np.zeros(101, dtype=float),
        }
        target["male"][31] = 90.0
        target["female"][31] = 100.0
        target["male"][40] = 10.0
        target["female"][40] = 20.0

        zero_mortality = {
            2024: {
                "male": np.zeros(101, dtype=float),
                "female": np.zeros(101, dtype=float),
            }
        }
        zero_fertility = {2024: np.zeros(101, dtype=float)}
        srb = {2024: 1.05}
        net_migration = {2024: 0.0}

        inputs = VariantInputs(
            variant_name="toy",
            years=[2024, 2025],
            ages=ages,
            population={2024: current, 2025: target},
            mortality=zero_mortality,
            fertility=zero_fertility,
            sex_ratio_at_birth=srb,
            net_migration_total=net_migration,
        )

        projected = project_one_year_no_migration(
            current_population=current,
            mortality=zero_mortality[2024],
            fertility=zero_fertility[2024],
            sex_ratio_at_birth=srb[2024],
        )
        residual = derive_migration_residuals(inputs)[2024]

        restored_male = projected["male"] + residual["male"]
        restored_female = projected["female"] + residual["female"]

        self.assertTrue(np.allclose(restored_male, target["male"]))
        self.assertTrue(np.allclose(restored_female, target["female"]))


if __name__ == "__main__":
    unittest.main()
