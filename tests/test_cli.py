from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.catalog import build_analytic_catalog
from long_sus.scenarios import build_validation_scenario


def _build_test_catalog(path: Path) -> Path:
    world_scenario = build_validation_scenario(
        "threshold_age_60_all_eligible",
        country="World",
        target="Xc",
        factor=1.2,
        branch="analytic_arm",
        analytic_preset_id="world_period_2024_both_hazard",
    )
    usa_scenario = build_validation_scenario(
        "no_one",
        country="USA",
        branch="analytic_arm",
        analytic_preset_id="usa_period_2024_both_hazard",
    )

    return build_analytic_catalog(
        path=path,
        countries=["USA", "World"],
        scenarios_by_country={
            "USA": [usa_scenario],
            "World": [world_scenario],
        },
        force=True,
    )


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.catalog_path = _build_test_catalog(Path(self.temp_dir.name) / "analytic_catalog.sqlite")
        self.env = {
            **os.environ,
            "PYTHONPATH": str(SRC_ROOT),
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, "-m", "long_sus.cli", *args],
            check=True,
            capture_output=True,
            text=True,
            env=self.env,
        )
        return result.stdout

    def test_countries_command(self) -> None:
        output = self._run("countries", "--format", "csv")
        self.assertIn("country", output)
        self.assertIn("World", output)

    def test_schemes_command(self) -> None:
        output = self._run("schemes", "--format", "csv")
        self.assertIn("threshold_age_60_all_eligible", output)

    def test_pyramid_command(self) -> None:
        output = self._run(
            "pyramid",
            "--country",
            "World",
            "--scheme-id",
            "threshold_age_60_all_eligible",
            "--target",
            "Xc",
            "--factor",
            "1.2",
            "--branch",
            "analytic_arm",
            "--year",
            "2050",
            "--catalog-path",
            str(self.catalog_path),
            "--format",
            "csv",
        )
        self.assertIn("population_count", output)
        self.assertIn("2050", output)

    def test_size_command(self) -> None:
        output = self._run(
            "size",
            "--country",
            "USA",
            "--scheme-id",
            "no_one",
            "--target",
            "none",
            "--factor",
            "1.0",
            "--branch",
            "analytic_arm",
            "--catalog-path",
            str(self.catalog_path),
            "--format",
            "csv",
        )
        self.assertIn("total_population", output)
        self.assertIn("USA", output)
