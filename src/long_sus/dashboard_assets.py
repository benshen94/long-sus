from __future__ import annotations

import json
from pathlib import Path

from .config import (
    DASHBOARD_ASSETS_DIR,
    DASHBOARD_SR_INTERVENTION_DIR,
    DEFAULT_ETA_FACTOR,
    DEFAULT_LAUNCH_YEAR,
    DEFAULT_PROJECTION_END_YEAR,
    DEFAULT_TARGET,
    DEFAULT_XC_FACTOR,
    ETA_FACTOR_GRID,
    USA_DASHBOARD_ANALYTIC_PRESET_PATH,
    USA_DASHBOARD_CALIBRATION_PATH,
    USA_DASHBOARD_DEMOGRAPHY_PATH,
    USA_DASHBOARD_MANIFEST_PATH,
    USA_DASHBOARD_SCENARIO_PATH,
    XC_FACTOR_GRID,
)
from .intervention_assets import (
    ANALYTIC_BRANCH,
    LEGACY_USA_ANALYTIC_PRESET_ID,
    SR_BRANCH,
    build_analytic_preset_catalog_payload,
    get_analytic_preset,
    build_sr_dashboard_asset_path,
    default_analytic_preset_id,
    serialize_intervention_asset,
)
from .projection import VariantInputs
from .scenarios import USA_RX_AGE_BANDS, build_validation_scheme_catalog
from .specs import DashboardArtifact, SRInterventionAsset


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _string_keyed_year_map(values: dict[int, object]) -> dict[str, object]:
    return {str(year): value for year, value in values.items()}


def _serialize_population_or_mortality(values: dict[int, dict[str, object]]) -> dict[str, dict[str, object]]:
    payload: dict[str, dict[str, object]] = {}

    for year, per_sex in values.items():
        payload[str(year)] = {
            "male": per_sex["male"].tolist(),
            "female": per_sex["female"].tolist(),
        }

    return payload


def _serialize_vector_map(values: dict[int, object]) -> dict[str, object]:
    return {str(year): vector.tolist() for year, vector in values.items()}


def _write_sr_intervention_assets(
    intervention_grid: dict[tuple[str, str, float], SRInterventionAsset],
) -> list[DashboardArtifact]:
    artifacts: list[DashboardArtifact] = []

    for (target, hetero_mode, factor), asset in intervention_grid.items():
        path = build_sr_dashboard_asset_path(
            DASHBOARD_SR_INTERVENTION_DIR,
            target=target,
            hetero_mode=hetero_mode,
            factor=factor,
        )
        _write_json(path, serialize_intervention_asset(asset))
        artifacts.append(
            DashboardArtifact(
                title=f"sr_asset_{target}_{hetero_mode}_{factor:.2f}",
                path=path,
            )
        )

    return artifacts


def _build_curve_payload_from_fit_curve(
    *,
    ages: list[float],
    curve_a: list[float],
    curve_b: list[float],
    sex: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for age, value_a, value_b in zip(ages, curve_a, curve_b):
        rows.append(
            {
                "sex": sex,
                "age": float(age),
                "curve_a": float(value_a),
                "curve_b": float(value_b),
            }
        )

    return rows


def build_analytic_calibration_payload(
    *,
    preset_id: str,
) -> dict[str, object]:
    preset = get_analytic_preset(preset_id)
    source = str(preset.get("source", ""))
    if not source.startswith("baseline_fits/"):
        return {
            "country": preset["country"],
            "curve_a_label": "Reference curve",
            "curve_b_label": "Analytic fit",
            "curves": [],
        }

    fit_path = Path("baseline_fits") / source.split("/", 1)[1]
    payload = json.loads(fit_path.read_text())
    country_entries = payload.get("countries", {})
    location_id = int(preset.get("location_id", 0))

    fit_entry = None
    for entry in country_entries.values():
        if int(entry.get("location_id", 0)) == location_id:
            fit_entry = entry
            break

    if fit_entry is None:
        return {
            "country": preset["country"],
            "curve_a_label": "Reference curve",
            "curve_b_label": "Analytic fit",
            "curves": [],
        }

    target_curve = fit_entry.get("target_curve", {})
    fitted_curve = fit_entry.get("fitted_curve", {})
    ages = list(target_curve.get("times", []))
    target_values = list(target_curve.get("values", []))
    fitted_values = list(fitted_curve.get("values", []))

    return {
        "country": preset["country"],
        "curve_a_label": "WPP hazard",
        "curve_b_label": "Analytic fit",
        "curves": _build_curve_payload_from_fit_curve(
            ages=ages,
            curve_a=target_values,
            curve_b=fitted_values,
            sex="both",
        ),
    }


def write_dashboard_assets(
    *,
    inputs: VariantInputs,
    intervention_grid: dict[tuple[str, str, float], SRInterventionAsset],
    calibration_curves=None,
    calibration_parameters=None,
    country: str,
    country_label: str,
    title: str,
    branch_options: list[str],
    default_branch: str,
    analytic_preset_id: str,
) -> list[DashboardArtifact]:
    DASHBOARD_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    demography_payload = {
        "country": country,
        "variant_name": inputs.variant_name,
        "years": list(inputs.years),
        "ages": inputs.ages.astype(int).tolist(),
        "population": _serialize_population_or_mortality(inputs.population),
        "mortality": _serialize_population_or_mortality(inputs.mortality),
        "fertility": _serialize_vector_map(inputs.fertility),
        "sex_ratio_at_birth": _string_keyed_year_map(inputs.sex_ratio_at_birth),
        "net_migration_total": _string_keyed_year_map(inputs.net_migration_total),
        "migration_residual": _serialize_population_or_mortality(inputs.migration_residual),
    }
    _write_json(USA_DASHBOARD_DEMOGRAPHY_PATH, demography_payload)

    sr_artifacts = _write_sr_intervention_assets(intervention_grid)

    analytic_preset_payload = build_analytic_preset_catalog_payload(
        default_preset_id=analytic_preset_id,
    )
    _write_json(USA_DASHBOARD_ANALYTIC_PRESET_PATH, analytic_preset_payload)

    if calibration_curves is not None and calibration_parameters is not None:
        calibration_payload = {
            "country": country,
            "parameters": calibration_parameters.to_dict(orient="records"),
            "curves": calibration_curves.to_dict(orient="records"),
        }
    else:
        calibration_payload = build_analytic_calibration_payload(
            preset_id=analytic_preset_id,
        )
    _write_json(USA_DASHBOARD_CALIBRATION_PATH, calibration_payload)

    scenario_payload = {
        "country": country,
        "branch_options": branch_options,
        "target_options": ["eta", "Xc"],
        "factor_grids": {
            "eta": list(ETA_FACTOR_GRID),
            "Xc": list(XC_FACTOR_GRID),
        },
        "default_branch": default_branch,
        "default_target": DEFAULT_TARGET,
        "default_eta_factor": DEFAULT_ETA_FACTOR,
        "default_xc_factor": DEFAULT_XC_FACTOR,
        "default_analytic_preset_id": analytic_preset_id,
        "launch_year": DEFAULT_LAUNCH_YEAR,
        "projection_end_year": DEFAULT_PROJECTION_END_YEAR,
        "default_threshold_age": 60,
        "default_start_rule": "absolute",
        "default_bands": [
            {
                "start_age": band.start_age,
                "end_age": band.end_age,
                "target_share": band.target_share,
            }
            for band in USA_RX_AGE_BANDS
        ],
        "presets": build_validation_scheme_catalog(),
    }
    _write_json(USA_DASHBOARD_SCENARIO_PATH, scenario_payload)

    manifest_payload = {
        "title": title,
        "country": country,
        "country_label": country_label,
        "branch_options": branch_options,
        "default_branch": default_branch,
        "default_target": DEFAULT_TARGET,
        "default_eta_factor": DEFAULT_ETA_FACTOR,
        "default_xc_factor": DEFAULT_XC_FACTOR,
        "default_analytic_preset_id": analytic_preset_id,
        "default_launch_year": DEFAULT_LAUNCH_YEAR,
        "default_projection_end_year": DEFAULT_PROJECTION_END_YEAR,
        "default_preset_id": "threshold_age_60_all_eligible",
        "default_compare_preset_id": "no_one",
        "target_options": ["eta", "Xc"],
        "factor_grids": {
            "eta": list(ETA_FACTOR_GRID),
            "Xc": list(XC_FACTOR_GRID),
        },
        "paths": {
            "demography": f"./{USA_DASHBOARD_DEMOGRAPHY_PATH.relative_to(USA_DASHBOARD_MANIFEST_PATH.parent).as_posix()}",
            "sr_interventions_root": f"./{DASHBOARD_SR_INTERVENTION_DIR.relative_to(USA_DASHBOARD_MANIFEST_PATH.parent).as_posix()}",
            "analytic_presets": f"./{USA_DASHBOARD_ANALYTIC_PRESET_PATH.relative_to(USA_DASHBOARD_MANIFEST_PATH.parent).as_posix()}",
            "calibration": f"./{USA_DASHBOARD_CALIBRATION_PATH.relative_to(USA_DASHBOARD_MANIFEST_PATH.parent).as_posix()}",
            "scenario_catalog": f"./{USA_DASHBOARD_SCENARIO_PATH.relative_to(USA_DASHBOARD_MANIFEST_PATH.parent).as_posix()}",
        },
    }
    _write_json(USA_DASHBOARD_MANIFEST_PATH, manifest_payload)

    return [
        DashboardArtifact(title="manifest", path=USA_DASHBOARD_MANIFEST_PATH),
        DashboardArtifact(title="demography", path=USA_DASHBOARD_DEMOGRAPHY_PATH),
        DashboardArtifact(title="analytic_presets", path=USA_DASHBOARD_ANALYTIC_PRESET_PATH),
        DashboardArtifact(title="calibration", path=USA_DASHBOARD_CALIBRATION_PATH),
        DashboardArtifact(title="scenario_catalog", path=USA_DASHBOARD_SCENARIO_PATH),
        *sr_artifacts,
    ]


def write_usa_dashboard_assets(
    *,
    inputs: VariantInputs,
    intervention_grid: dict[tuple[str, str, float], SRInterventionAsset],
    calibration_curves,
    calibration_parameters,
) -> list[DashboardArtifact]:
    return write_dashboard_assets(
        inputs=inputs,
        intervention_grid=intervention_grid,
        calibration_curves=calibration_curves,
        calibration_parameters=calibration_parameters,
        country="USA",
        country_label="United States",
        title="USA SR Validation Dashboard",
        branch_options=[SR_BRANCH, ANALYTIC_BRANCH],
        default_branch=SR_BRANCH,
        analytic_preset_id=LEGACY_USA_ANALYTIC_PRESET_ID,
    )
