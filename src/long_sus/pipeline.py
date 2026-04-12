from __future__ import annotations

from .calibration import fit_usa_mgg_benchmarks
from .catalog import build_analytic_catalog
from .config import (
    ANALYTIC_CATALOG_DB_PATH,
    CATALOG_DIR,
    DASHBOARD_ASSETS_DIR,
    DASHBOARD_DIR,
    DASHBOARD_DOC_PATH,
    DASHBOARD_INDEX_PATH,
    DASHBOARD_SR_INTERVENTION_DIR,
    DASHBOARD_PLOTS_DIR,
    DEFAULT_PROJECTION_END_YEAR,
    DOCS_DIR,
    ETA_FACTOR_GRID,
    FORECAST_POPULATION_PATH,
    FORECAST_SUMMARY_PATH,
    PIPELINE_DOC_PATH,
    PROCESSED_CALIBRATION_DIR,
    PROCESSED_DEMO_DIR,
    README_PATH,
    RESULTS_TUTORIAL_PATH,
    USA_VALIDATION_DOC_PATH,
    XC_FACTOR_GRID,
)
from .countries import list_supported_country_specs
from .dashboard_assets import write_multi_area_dashboard_assets, write_usa_dashboard_assets
from .dashboard_capture import capture_dashboard_artifacts
from .data_sources import (
    download_country_wpp_bundle,
    download_usa_wpp_bundle,
    download_world_wpp_bundle,
    load_cached_country_wpp_bundle,
)
from .documentation import (
    write_dashboard_doc,
    write_pipeline_doc,
    write_results_tutorial,
    write_validation_doc,
)
from .external_paths import validate_external_paths
from .intervention_assets import ANALYTIC_BRANCH, default_analytic_preset_id, select_intervention_asset
from .plots import create_readme_figure_registry
from .projection import build_variant_inputs, project_scenario
from .scenarios import build_readme_scenarios
from .specs import ForecastArtifacts, SRInterventionAsset
from .sr_intervention import build_sr_intervention_grid


def _ensure_output_dirs() -> None:
    for path in [
        PROCESSED_DEMO_DIR,
        PROCESSED_CALIBRATION_DIR,
        CATALOG_DIR,
        FORECAST_POPULATION_PATH.parent,
        DASHBOARD_ASSETS_DIR,
        DASHBOARD_SR_INTERVENTION_DIR,
        DASHBOARD_PLOTS_DIR,
        DOCS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def _write_processed_demography(bundle) -> None:
    for variant_name, frame in bundle.population.items():
        frame.to_csv(PROCESSED_DEMO_DIR / f"usa_population_{variant_name}.csv", index=False)

    for variant_name, frame in bundle.fertility.items():
        frame.to_csv(PROCESSED_DEMO_DIR / f"usa_fertility_{variant_name}.csv", index=False)

    for variant_name, frame in bundle.sex_ratio_at_birth.items():
        frame.to_csv(PROCESSED_DEMO_DIR / f"usa_srb_{variant_name}.csv", index=False)

    for variant_name, frame in bundle.net_migration.items():
        frame.to_csv(PROCESSED_DEMO_DIR / f"usa_net_migration_{variant_name}.csv", index=False)

    bundle.mortality.to_csv(PROCESSED_DEMO_DIR / "usa_mortality_medium.csv", index=False)


def _build_validation_outputs(
    *,
    inputs,
    intervention_grid: dict[tuple[str, str, float], SRInterventionAsset],
) -> tuple:
    population_frames = []
    summary_frames = []

    for scenario in build_readme_scenarios():
        intervention_asset = select_intervention_asset(
            scenario=scenario,
            inputs=inputs,
            sr_intervention_grid=intervention_grid,
        )
        population_frame, summary_frame = project_scenario(
            scenario=scenario,
            inputs=inputs,
            intervention_asset=intervention_asset,
        )
        population_frames.append(population_frame)
        summary_frames.append(summary_frame)

    return (
        population_frames,
        summary_frames,
    )


def _concat_outputs(population_frames, summary_frames):
    import pandas as pd

    return (
        pd.concat(population_frames, ignore_index=True),
        pd.concat(summary_frames, ignore_index=True),
    )


def _validate_outputs(
    population_frame,
    summary_frame,
    figures,
    dashboard_artifacts,
) -> None:
    if population_frame.empty:
        raise ValueError("Population output is empty")

    if summary_frame.empty:
        raise ValueError("Summary output is empty")

    required_scenarios = {
        "no_one",
        "threshold_age_60_all_eligible_eta_1.00x",
        "threshold_age_60_all_eligible_eta_0.80x",
        "prescription_bands_absolute_eta_0.80x",
        "prescription_bands_equal_probabilities_eta_0.80x",
        "prescription_bands_uniform_start_age_eta_0.80x",
    }
    actual_scenarios = set(summary_frame["scenario"].unique())
    missing = required_scenarios - actual_scenarios
    if missing:
        raise ValueError(f"Missing scenario outputs: {sorted(missing)}")

    for figure in figures:
        if not figure.path.exists():
            raise FileNotFoundError(f"Missing figure: {figure.path}")

    for artifact in dashboard_artifacts:
        if not artifact.path.exists():
            raise FileNotFoundError(f"Missing dashboard artifact: {artifact.path}")

    for required_path in [
        README_PATH,
        RESULTS_TUTORIAL_PATH,
        PIPELINE_DOC_PATH,
        DASHBOARD_DOC_PATH,
        USA_VALIDATION_DOC_PATH,
        DASHBOARD_INDEX_PATH,
    ]:
        if not required_path.exists():
            raise FileNotFoundError(f"Missing required output: {required_path}")


def run_usa_pipeline() -> ForecastArtifacts:
    validate_external_paths()
    _ensure_output_dirs()

    bundle = download_usa_wpp_bundle()
    _write_processed_demography(bundle)

    calibration = fit_usa_mgg_benchmarks()
    inputs = build_variant_inputs(bundle, "medium")
    intervention_grid = build_sr_intervention_grid(
        eta_factors=ETA_FACTOR_GRID,
        xc_factors=XC_FACTOR_GRID,
    )

    population_frames, summary_frames = _build_validation_outputs(
        inputs=inputs,
        intervention_grid=intervention_grid,
    )
    population_output, summary_output = _concat_outputs(population_frames, summary_frames)
    population_output.to_csv(FORECAST_POPULATION_PATH, index=False)
    summary_output.to_csv(FORECAST_SUMMARY_PATH, index=False)

    dashboard_artifacts = write_usa_dashboard_assets(
        inputs=inputs,
        intervention_grid=intervention_grid,
        calibration_curves=calibration.curves,
        calibration_parameters=calibration.parameters,
    )

    figures = create_readme_figure_registry(
        population_frame=population_output,
        summary_frame=summary_output,
        calibration_curves=calibration.curves,
        intervention_grid=intervention_grid,
        inputs=inputs,
    )

    dashboard_shots = capture_dashboard_artifacts(
        base_url_path="dashboard/index.html",
        overview_path=DASHBOARD_PLOTS_DIR / "dashboard_overview.png",
        comparison_path=DASHBOARD_PLOTS_DIR / "dashboard_comparison.png",
    )

    write_results_tutorial(
        path=RESULTS_TUTORIAL_PATH,
        figures=figures,
        dashboard_artifacts=dashboard_shots,
    )
    write_pipeline_doc(PIPELINE_DOC_PATH)
    write_dashboard_doc(DASHBOARD_DOC_PATH)
    write_validation_doc(USA_VALIDATION_DOC_PATH)

    all_dashboard_artifacts = [*dashboard_artifacts, *dashboard_shots]
    _validate_outputs(
        population_frame=population_output,
        summary_frame=summary_output,
        figures=figures,
        dashboard_artifacts=all_dashboard_artifacts,
    )

    return ForecastArtifacts(
        population_path=FORECAST_POPULATION_PATH,
        summary_path=FORECAST_SUMMARY_PATH,
        readme_path=README_PATH,
        results_doc_path=RESULTS_TUTORIAL_PATH,
        dashboard_path=DASHBOARD_INDEX_PATH,
        pipeline_doc_path=PIPELINE_DOC_PATH,
        validation_doc_path=USA_VALIDATION_DOC_PATH,
        figures=figures,
        dashboard_artifacts=all_dashboard_artifacts,
    )


def build_world_analytic_dashboard_assets() -> None:
    _ensure_output_dirs()

    area_specs = list_supported_country_specs()
    area_inputs = {}

    for area_spec in area_specs:
        try:
            bundle = load_cached_country_wpp_bundle(area_spec)
        except FileNotFoundError:
            bundle = download_country_wpp_bundle(area_spec)
        area_inputs[area_spec.slug] = build_variant_inputs(bundle, "medium")

    write_multi_area_dashboard_assets(
        area_inputs=area_inputs,
        area_specs=area_specs,
        intervention_grid={},
        title="Analytic Longevity Dashboard",
        default_area_slug="world",
    )


def build_public_analytic_catalog():
    supported_countries = [country.name for country in list_supported_country_specs()]
    return build_analytic_catalog(
        path=ANALYTIC_CATALOG_DB_PATH,
        countries=supported_countries,
        include_population=False,
    )
