from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.pipeline import run_usa_pipeline


class GeneratedOutputsTest(unittest.TestCase):
    def test_pipeline_generates_expected_artifacts(self) -> None:
        artifacts = run_usa_pipeline()

        self.assertTrue(artifacts.population_path.exists())
        self.assertTrue(artifacts.summary_path.exists())
        self.assertTrue(artifacts.readme_path.exists())
        self.assertTrue(artifacts.results_doc_path.exists())
        self.assertTrue(artifacts.dashboard_path.exists())
        self.assertTrue(artifacts.pipeline_doc_path.exists())
        self.assertTrue(artifacts.validation_doc_path.exists())
        self.assertGreaterEqual(len(artifacts.figures), 5)
        self.assertGreaterEqual(len(artifacts.dashboard_artifacts), 4)

        readme_text = artifacts.results_doc_path.read_text()
        image_paths = re.findall(r"!\[[^\]]+\]\(([^)]+)\)", readme_text)
        self.assertTrue(image_paths)

        for image_path in image_paths:
            full_path = artifacts.results_doc_path.parent / image_path
            self.assertTrue(full_path.exists(), image_path)


if __name__ == "__main__":
    unittest.main()
