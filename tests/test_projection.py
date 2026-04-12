from __future__ import annotations

import numpy as np
import pandas as pd
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.projection import (
    VariantInputs,
    build_variant_inputs,
    derive_migration_residuals,
    project_one_year_no_migration,
)
from long_sus.data_sources import WppBundle


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

    def test_build_variant_inputs_extends_population_tail_beyond_open_age_bin(self) -> None:
        bundle = WppBundle(
            population={
                "medium": pd.DataFrame(
                    [
                        {"year": 2024, "sex": "male", "age": 99, "population": 20.0},
                        {"year": 2024, "sex": "male", "age": 100, "population": 10.0},
                        {"year": 2024, "sex": "female", "age": 99, "population": 24.0},
                        {"year": 2024, "sex": "female", "age": 100, "population": 12.0},
                        {"year": 2025, "sex": "male", "age": 99, "population": 18.0},
                        {"year": 2025, "sex": "male", "age": 100, "population": 11.0},
                        {"year": 2025, "sex": "female", "age": 99, "population": 22.0},
                        {"year": 2025, "sex": "female", "age": 100, "population": 13.0},
                    ]
                )
            },
            fertility={
                "medium": pd.DataFrame(
                    [
                        {"year": 2024, "age": 30, "asfr": 0.0},
                        {"year": 2025, "age": 30, "asfr": 0.0},
                    ]
                )
            },
            mortality=pd.DataFrame(
                [
                    {"year": 2024, "sex": "male", "age": 99, "mx": 0.2},
                    {"year": 2024, "sex": "male", "age": 100, "mx": 0.2},
                    {"year": 2024, "sex": "female", "age": 99, "mx": 0.2},
                    {"year": 2024, "sex": "female", "age": 100, "mx": 0.2},
                    {"year": 2025, "sex": "male", "age": 99, "mx": 0.2},
                    {"year": 2025, "sex": "male", "age": 100, "mx": 0.2},
                    {"year": 2025, "sex": "female", "age": 99, "mx": 0.2},
                    {"year": 2025, "sex": "female", "age": 100, "mx": 0.2},
                ]
            ),
            sex_ratio_at_birth={
                "medium": pd.DataFrame(
                    [
                        {"year": 2024, "sex_ratio_at_birth": 1.05},
                        {"year": 2025, "sex_ratio_at_birth": 1.05},
                    ]
                )
            },
            net_migration={
                "medium": pd.DataFrame(
                    [
                        {"year": 2024, "net_migration": 0.0},
                        {"year": 2025, "net_migration": 0.0},
                    ]
                )
            },
            metadata={},
        )

        inputs = build_variant_inputs(bundle, "medium")

        self.assertGreater(inputs.population[2024]["male"][101], 0.0)
        self.assertGreater(inputs.population[2024]["female"][101], 0.0)
        self.assertAlmostEqual(inputs.population[2024]["male"][100:].sum(), 10.0)
        self.assertAlmostEqual(inputs.population[2024]["female"][100:].sum(), 12.0)

    def test_build_variant_inputs_extrapolates_mortality_after_open_age_100(self) -> None:
        bundle = WppBundle(
            population={
                "medium": pd.DataFrame(
                    [
                        {"year": 2024, "sex": "male", "age": 100, "population": 10.0},
                        {"year": 2024, "sex": "female", "age": 100, "population": 12.0},
                        {"year": 2025, "sex": "male", "age": 100, "population": 11.0},
                        {"year": 2025, "sex": "female", "age": 100, "population": 13.0},
                    ]
                )
            },
            fertility={
                "medium": pd.DataFrame(
                    [
                        {"year": 2024, "age": 30, "asfr": 0.0},
                        {"year": 2025, "age": 30, "asfr": 0.0},
                    ]
                )
            },
            mortality=pd.DataFrame(
                [
                    {"year": 2024, "sex": "male", "age": 95, "mx": 0.25},
                    {"year": 2024, "sex": "male", "age": 96, "mx": 0.28},
                    {"year": 2024, "sex": "male", "age": 97, "mx": 0.31},
                    {"year": 2024, "sex": "male", "age": 98, "mx": 0.34},
                    {"year": 2024, "sex": "male", "age": 99, "mx": 0.38},
                    {"year": 2024, "sex": "male", "age": 100, "mx": 0.45},
                    {"year": 2024, "sex": "female", "age": 95, "mx": 0.22},
                    {"year": 2024, "sex": "female", "age": 96, "mx": 0.24},
                    {"year": 2024, "sex": "female", "age": 97, "mx": 0.27},
                    {"year": 2024, "sex": "female", "age": 98, "mx": 0.30},
                    {"year": 2024, "sex": "female", "age": 99, "mx": 0.34},
                    {"year": 2024, "sex": "female", "age": 100, "mx": 0.40},
                    {"year": 2025, "sex": "male", "age": 95, "mx": 0.25},
                    {"year": 2025, "sex": "male", "age": 96, "mx": 0.28},
                    {"year": 2025, "sex": "male", "age": 97, "mx": 0.31},
                    {"year": 2025, "sex": "male", "age": 98, "mx": 0.34},
                    {"year": 2025, "sex": "male", "age": 99, "mx": 0.38},
                    {"year": 2025, "sex": "male", "age": 100, "mx": 0.45},
                    {"year": 2025, "sex": "female", "age": 95, "mx": 0.22},
                    {"year": 2025, "sex": "female", "age": 96, "mx": 0.24},
                    {"year": 2025, "sex": "female", "age": 97, "mx": 0.27},
                    {"year": 2025, "sex": "female", "age": 98, "mx": 0.30},
                    {"year": 2025, "sex": "female", "age": 99, "mx": 0.34},
                    {"year": 2025, "sex": "female", "age": 100, "mx": 0.40},
                ]
            ),
            sex_ratio_at_birth={
                "medium": pd.DataFrame(
                    [
                        {"year": 2024, "sex_ratio_at_birth": 1.05},
                        {"year": 2025, "sex_ratio_at_birth": 1.05},
                    ]
                )
            },
            net_migration={
                "medium": pd.DataFrame(
                    [
                        {"year": 2024, "net_migration": 0.0},
                        {"year": 2025, "net_migration": 0.0},
                    ]
                )
            },
            metadata={},
        )

        inputs = build_variant_inputs(bundle, "medium")

        self.assertGreater(inputs.mortality[2024]["male"][101], inputs.mortality[2024]["male"][100])
        self.assertGreater(inputs.mortality[2024]["female"][101], inputs.mortality[2024]["female"][100])
        self.assertGreater(inputs.mortality[2024]["male"][110], inputs.mortality[2024]["male"][101])
        self.assertGreater(inputs.mortality[2024]["female"][110], inputs.mortality[2024]["female"][101])


if __name__ == "__main__":
    unittest.main()
