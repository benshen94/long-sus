from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
DOCS_DIR = PROJECT_ROOT / "docs"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
DASHBOARD_ASSETS_DIR = DASHBOARD_DIR / "assets"
DASHBOARD_INTERVENTION_DIR = DASHBOARD_ASSETS_DIR / "interventions"
DASHBOARD_SR_INTERVENTION_DIR = DASHBOARD_INTERVENTION_DIR / "sr"

DATA_DIR = PROJECT_ROOT / "data"
BASELINE_FITS_DIR = PROJECT_ROOT / "baseline_fits"
BASELINE_FIT_CATALOG_PATH = BASELINE_FITS_DIR / "country_baseline_fits_2024.json"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CATALOG_DIR = DATA_DIR / "catalog"

RAW_WPP_DIR = RAW_DIR / "wpp"
RAW_HMD_DIR = RAW_DIR / "hmd"
RAW_HFD_DIR = RAW_DIR / "hfd"

PROCESSED_DEMO_DIR = PROCESSED_DIR / "demography"
PROCESSED_CALIBRATION_DIR = PROCESSED_DIR / "calibration"

PLOTS_DIR = OUTPUTS_DIR / "plots"
PYRAMID_PLOTS_DIR = PLOTS_DIR / "pyramids"
COMPARISON_PLOTS_DIR = PLOTS_DIR / "comparisons"
README_PLOTS_DIR = PLOTS_DIR / "readme"
DASHBOARD_PLOTS_DIR = PLOTS_DIR / "dashboard"

FORECAST_POPULATION_PATH = OUTPUTS_DIR / "forecast_population.csv"
FORECAST_SUMMARY_PATH = OUTPUTS_DIR / "forecast_summary.csv"
ANALYTIC_CATALOG_DB_PATH = CATALOG_DIR / "analytic_catalog.sqlite"
README_PATH = PROJECT_ROOT / "README.md"
PIPELINE_DOC_PATH = DOCS_DIR / "pipeline.md"
DASHBOARD_DOC_PATH = DOCS_DIR / "dashboard.md"
USA_VALIDATION_DOC_PATH = DOCS_DIR / "usa_validation.md"
RESULTS_TUTORIAL_PATH = DOCS_DIR / "results_tutorial.md"
USA_DASHBOARD_MANIFEST_PATH = DASHBOARD_ASSETS_DIR / "manifest.json"
USA_DASHBOARD_DEMOGRAPHY_PATH = DASHBOARD_ASSETS_DIR / "usa_demography.json"
USA_DASHBOARD_CALIBRATION_PATH = DASHBOARD_ASSETS_DIR / "usa_calibration.json"
USA_DASHBOARD_SCENARIO_PATH = DASHBOARD_ASSETS_DIR / "usa_validation_scenarios.json"
USA_DASHBOARD_ANALYTIC_PRESET_PATH = DASHBOARD_ASSETS_DIR / "usa_analytic_presets.json"
DASHBOARD_INDEX_PATH = DASHBOARD_DIR / "index.html"

WPP_API_BASE = "https://population.un.org/dataportalapi/uiapi/v1"
WPP_USA_LOCATION_ID = 840
WPP_WORLD_LOCATION_ID = 900

WPP_VARIANTS = {
    "medium": 4,
    "high_fertility": 9,
    "low_fertility": 10,
}

WPP_VARIANT_LABELS = {
    "medium": "Median",
    "high_fertility": "High-fertility",
    "low_fertility": "Low-fertility",
}

WPP_INDICATORS = {
    "population": 47,
    "fertility": 68,
    "mortality": 80,
    "sex_ratio_at_birth": 58,
    "net_migration": 65,
}

USA_NAME = "United States"
WORLD_NAME = "World"
DEFAULT_BASE_YEAR = 2020
DEFAULT_LAUNCH_YEAR = 2025
DEFAULT_FINAL_YEAR = 2100
MAX_AGE = 170
DEFAULT_PROJECTION_END_YEAR = DEFAULT_FINAL_YEAR

SEXES = ("male", "female")
SEX_ID_TO_NAME = {1: "male", 2: "female", 3: "both"}
SEX_NAME_TO_ID = {"male": 1, "female": 2, "both": 3}

START_RULES = (
    "absolute",
    "equal_probabilities",
    "uniform_start_age",
    "deterministic_threshold",
)

UPTAKE_RULES = START_RULES + ("banded_percentages",)

ETA_FACTOR_GRID = (1.00, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70)
XC_FACTOR_GRID = (1.00, 1.10, 1.20)
DEFAULT_TARGET = "eta"
DEFAULT_ETA_FACTOR = 0.80
DEFAULT_XC_FACTOR = 1.10
MIN_START_AGE = 0
MAX_START_AGE = MAX_AGE
VALIDATION_SCHEME_IDS = (
    "no_one",
    "everyone",
    "only_elderly_65plus",
    "50pct_elderly_65plus",
    "30pct_middle_40_64_plus_70pct_elderly_65plus",
    "half_population_adult_band",
    "prescription_bands_absolute",
    "prescription_bands_equal_probabilities",
    "prescription_bands_uniform_start_age",
    "threshold_age_60_all_eligible",
)
