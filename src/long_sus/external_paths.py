from __future__ import annotations

import sys
from pathlib import Path


AGING_ROOT = Path(
    "/Users/benshenhar/Library/CloudStorage/GoogleDrive-benshenhar@gmail.com/"
    "My Drive/Weizmann/Alon Lab/Aging"
)
AGING_PYTHON_ROOT = AGING_ROOT / "python"
AGING_DATASETS_ROOT = AGING_ROOT / "datasets"

USA_2019_RESULTS_PATH = (
    AGING_PYTHON_ROOT
    / "notebooks/thresholds, noise/saved_results/param_variation_results_usa_2019.pkl"
)
USA_2019_HETERO_RESULTS_PATH = (
    AGING_PYTHON_ROOT
    / "notebooks/thresholds, noise/saved_results/param_variation_results_usa_2019_with_hetero.pkl"
)

USA_2019_NOTEBOOK_PATHS = {
    "steepness_longevity": AGING_PYTHON_ROOT / "notebooks/thresholds, noise/steepness_longevity.ipynb",
    "nhanes_sandbox": AGING_PYTHON_ROOT / "notebooks/thresholds, noise/nhanes sandbox.ipynb",
    "figures": AGING_PYTHON_ROOT / "notebooks/thresholds, noise/Figures.ipynb",
}

HMD_DATA_DIR = AGING_DATASETS_ROOT / "HMD_datasets"

HMD_PERIOD_FILES = {
    "male": HMD_DATA_DIR / "mortality.org_File_GetDocument_hmd.v6_USA_STATS_mltper_1x1.txt",
    "female": HMD_DATA_DIR / "mortality.org_File_GetDocument_hmd.v6_USA_STATS_fltper_1x1.txt",
    "both": HMD_DATA_DIR / "mortality.org_File_GetDocument_hmd.v6_USA_STATS_bltper_1x1.txt",
}


def ensure_ageing_python_path() -> None:
    ageing_path = str(AGING_PYTHON_ROOT)
    if ageing_path in sys.path:
        return

    sys.path.insert(0, ageing_path)


def validate_external_paths() -> None:
    required_paths = [
        USA_2019_RESULTS_PATH,
        USA_2019_HETERO_RESULTS_PATH,
        *USA_2019_NOTEBOOK_PATHS.values(),
        *HMD_PERIOD_FILES.values(),
    ]

    missing = [path for path in required_paths if not path.exists()]
    if not missing:
        return

    lines = ["Missing external files:"]
    lines.extend(f"- {path}" for path in missing)
    raise FileNotFoundError("\n".join(lines))
