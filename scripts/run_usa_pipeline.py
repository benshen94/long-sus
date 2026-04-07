from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.pipeline import run_usa_pipeline


if __name__ == "__main__":
    artifacts = run_usa_pipeline()
    print("forecast_population:", artifacts.population_path)
    print("forecast_summary:", artifacts.summary_path)
    print("readme:", artifacts.readme_path)
    print("results_doc:", artifacts.results_doc_path)
    print("dashboard:", artifacts.dashboard_path)
    print("pipeline_doc:", artifacts.pipeline_doc_path)
    print("validation_doc:", artifacts.validation_doc_path)
