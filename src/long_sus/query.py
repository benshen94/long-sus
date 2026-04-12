from __future__ import annotations

from functools import lru_cache
import sqlite3
from pathlib import Path

import pandas as pd

from .catalog import build_analytic_catalog
from .config import (
    ANALYTIC_CATALOG_DB_PATH,
    ETA_FACTOR_GRID,
    ETA_SHIFT_FACTOR_GRID,
    ROLLOUT_CURVES,
    XC_FACTOR_GRID,
)
from .countries import CountrySpec, get_country_spec, list_supported_countries as _list_supported_countries
from .data_sources import download_country_wpp_bundle
from .intervention_assets import ANALYTIC_BRANCH, SR_BRANCH, select_intervention_asset
from .projection import VariantInputs, build_variant_inputs, project_scenario
from .scenarios import build_validation_scheme_catalog, build_validation_scenario
from .specs import ScenarioQuery
from .sr_intervention import build_sr_intervention_grid


SUPPORTED_QUERY_SOURCES = {"auto", "catalog", "project"}
SUPPORTED_SEXES = {"male", "female"}
SUPPORTED_TARGETS = {"none", "eta", "eta_shift", "Xc"}
CATALOG_FACTOR_GRID = {
    "none": (1.0,),
    "eta": ETA_FACTOR_GRID,
    "eta_shift": ETA_SHIFT_FACTOR_GRID,
    "Xc": XC_FACTOR_GRID,
}


def list_supported_countries() -> list[dict[str, object]]:
    return _list_supported_countries()


def list_supported_schemes() -> list[dict[str, object]]:
    return build_validation_scheme_catalog()


def _factor_matches_catalog(target: str, factor: float) -> bool:
    return any(abs(float(factor) - float(grid_factor)) < 1e-9 for grid_factor in CATALOG_FACTOR_GRID[target])


def _validate_query(query: ScenarioQuery) -> tuple[ScenarioQuery, CountrySpec]:
    country_spec = get_country_spec(query.country)
    scheme_catalog = {scheme["id"]: scheme for scheme in build_validation_scheme_catalog()}

    if query.source not in SUPPORTED_QUERY_SOURCES:
        raise ValueError(f"Unsupported source: {query.source}")

    if query.branch not in {ANALYTIC_BRANCH, SR_BRANCH}:
        raise ValueError(f"Unsupported branch: {query.branch}")

    if query.scheme_id not in scheme_catalog:
        raise ValueError(f"Unsupported scheme_id: {query.scheme_id}")
    scheme = scheme_catalog[query.scheme_id]

    if query.target not in SUPPORTED_TARGETS:
        raise ValueError(f"Unsupported target: {query.target}")

    if query.sex is not None and query.sex not in SUPPORTED_SEXES:
        raise ValueError(f"Unsupported sex: {query.sex}")

    if query.year is not None and query.year < 2024:
        raise ValueError("year must be 2024 or later")

    if query.target == "none":
        if query.scheme_id != "no_one":
            raise ValueError("target='none' is only valid with scheme_id='no_one'")
        if abs(float(query.factor) - 1.0) > 1e-9:
            raise ValueError("target='none' requires factor=1.0")

    if query.target != "none" and float(query.factor) <= 0.0:
        raise ValueError("factor must be positive")

    if query.threshold_age is not None and query.threshold_age < 0:
        raise ValueError("threshold_age must be non-negative")

    if query.threshold_probability is not None and not 0.0 <= float(query.threshold_probability) <= 1.0:
        raise ValueError("threshold_probability must be between 0.0 and 1.0")

    if query.rollout_curve is not None and query.rollout_curve not in ROLLOUT_CURVES:
        raise ValueError(f"Unsupported rollout_curve: {query.rollout_curve}")

    rollout_probabilities = (
        ("rollout_launch_probability", query.rollout_launch_probability),
        ("rollout_max_probability", query.rollout_max_probability),
    )
    for field_name, value in rollout_probabilities:
        if value is None:
            continue
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0")

    if query.rollout_ramp_years is not None and int(query.rollout_ramp_years) <= 0:
        raise ValueError("rollout_ramp_years must be positive")

    if query.rollout_takeoff_years is not None and int(query.rollout_takeoff_years) <= 0:
        raise ValueError("rollout_takeoff_years must be positive")

    if query.threshold_probability is not None and scheme["uptake_mode"] != "threshold":
        raise ValueError("threshold_probability is only valid for threshold schemes")

    if query.threshold_age is not None and scheme["uptake_mode"] not in {"threshold", "rollout"}:
        raise ValueError("threshold_age is only valid for threshold and rollout schemes")

    rollout_override_fields = (
        query.rollout_curve,
        query.rollout_launch_probability,
        query.rollout_max_probability,
        query.rollout_ramp_years,
        query.rollout_takeoff_years,
    )
    if any(value is not None for value in rollout_override_fields) and scheme["uptake_mode"] != "rollout":
        raise ValueError("rollout overrides are only valid for rollout schemes")

    rollout_launch_probability = (
        float(query.rollout_launch_probability)
        if query.rollout_launch_probability is not None
        else float(scheme["rollout_launch_probability"])
    )
    rollout_max_probability = (
        float(query.rollout_max_probability)
        if query.rollout_max_probability is not None
        else float(scheme["rollout_max_probability"])
    )
    if rollout_max_probability < rollout_launch_probability:
        raise ValueError("rollout_max_probability must be at least rollout_launch_probability")

    if query.branch == SR_BRANCH and country_spec.name != "USA":
        raise ValueError("branch='sr' is currently supported only for USA")

    if query.branch == SR_BRANCH and query.target == "eta_shift":
        raise ValueError("branch='sr' does not support target='eta_shift'")

    if query.branch == SR_BRANCH and query.target == "none" and query.scheme_id == "no_one":
        return query, country_spec

    if query.branch == SR_BRANCH and not _factor_matches_catalog(query.target, query.factor):
        raise ValueError("branch='sr' currently supports only the built-in factor grids")

    return query, country_spec


def _catalog_ready(path: Path) -> Path:
    if path.exists():
        return path

    return build_analytic_catalog(path=path)


def _catalog_eligible(query: ScenarioQuery) -> bool:
    if query.branch != ANALYTIC_BRANCH:
        return False

    if query.source == "project":
        return False

    if query.threshold_age is not None or query.threshold_probability is not None:
        return False

    if (
        query.rollout_curve is not None
        or query.rollout_launch_probability is not None
        or query.rollout_max_probability is not None
        or query.rollout_ramp_years is not None
        or query.rollout_takeoff_years is not None
    ):
        return False

    scheme_catalog = {scheme["id"]: scheme for scheme in build_validation_scheme_catalog()}
    if scheme_catalog[query.scheme_id]["uptake_mode"] == "rollout":
        return False

    return _factor_matches_catalog(query.target, query.factor)


def _require_catalog_support(query: ScenarioQuery) -> None:
    if query.source != "catalog":
        return

    if _catalog_eligible(query):
        return

    raise ValueError("Requested query cannot be served from the shipped analytic catalog")


@lru_cache(maxsize=16)
def _load_variant_inputs(country: str, variant_name: str) -> VariantInputs:
    bundle = download_country_wpp_bundle(country)
    return build_variant_inputs(bundle, variant_name)


@lru_cache(maxsize=1)
def _load_sr_intervention_grid() -> dict[tuple[str, str, float], object]:
    return build_sr_intervention_grid(
        eta_factors=ETA_FACTOR_GRID,
        xc_factors=XC_FACTOR_GRID,
    )


def _build_scenario(query: ScenarioQuery, country_spec: CountrySpec):
    analytic_preset_id = query.analytic_preset_id
    if query.branch == ANALYTIC_BRANCH and analytic_preset_id is None:
        analytic_preset_id = country_spec.default_analytic_preset_id

    target = None if query.target == "none" else query.target
    scenario = build_validation_scenario(
        query.scheme_id,
        country=country_spec.name,
        target=target if target is not None else "eta",
        factor=float(query.factor),
        launch_year=query.launch_year,
        projection_end_year=query.projection_end_year,
        branch=query.branch,
        analytic_preset_id=analytic_preset_id,
        hetero_mode=query.hetero_mode,
    )

    if (
        query.threshold_age is None
        and query.threshold_probability is None
        and query.rollout_curve is None
        and query.rollout_launch_probability is None
        and query.rollout_max_probability is None
        and query.rollout_ramp_years is None
        and query.rollout_takeoff_years is None
    ):
        return scenario

    updates = dict(scenario.__dict__)
    if query.threshold_age is not None:
        updates["threshold_age"] = int(query.threshold_age)
    if query.threshold_probability is not None:
        updates["threshold_probability"] = float(query.threshold_probability)
    if query.rollout_curve is not None:
        updates["rollout_curve"] = str(query.rollout_curve)
    if query.rollout_launch_probability is not None:
        updates["rollout_launch_probability"] = float(query.rollout_launch_probability)
    if query.rollout_max_probability is not None:
        updates["rollout_max_probability"] = float(query.rollout_max_probability)
    if query.rollout_ramp_years is not None:
        updates["rollout_ramp_years"] = int(query.rollout_ramp_years)
    if query.rollout_takeoff_years is not None:
        updates["rollout_takeoff_years"] = int(query.rollout_takeoff_years)

    return scenario.__class__(**updates)


def _project_query_scenario(query: ScenarioQuery) -> tuple[pd.DataFrame, pd.DataFrame]:
    validated_query, country_spec = _validate_query(query)
    scenario = _build_scenario(validated_query, country_spec)
    inputs = _load_variant_inputs(country_spec.name, "medium")
    sr_intervention_grid = _load_sr_intervention_grid() if scenario.branch == SR_BRANCH else None
    intervention_asset = select_intervention_asset(
        scenario=scenario,
        inputs=inputs,
        sr_intervention_grid=sr_intervention_grid,
    )
    return project_scenario(
        scenario=scenario,
        inputs=inputs,
        intervention_asset=intervention_asset,
    )


def project_analytic_scenario(query: ScenarioQuery) -> tuple[pd.DataFrame, pd.DataFrame]:
    if query.branch != ANALYTIC_BRANCH:
        raise ValueError("project_analytic_scenario requires branch='analytic_arm'")

    return _project_query_scenario(query)


def _catalog_where(query: ScenarioQuery) -> tuple[str, list[object]]:
    clauses = [
        "country = ?",
        "branch = ?",
        "scheme_id = ?",
        "target = ?",
        "ABS(factor - ?) < 1e-9",
    ]
    params: list[object] = [
        get_country_spec(query.country).name,
        query.branch,
        query.scheme_id,
        query.target,
        float(query.factor),
    ]

    if query.year is not None:
        clauses.append("year = ?")
        params.append(int(query.year))

    if query.sex is not None:
        clauses.append("sex = ?")
        params.append(query.sex)

    return " AND ".join(clauses), params


def _query_catalog_table(
    *,
    table: str,
    query: ScenarioQuery,
    catalog_path: Path,
) -> pd.DataFrame:
    where_clause, params = _catalog_where(query)
    sql = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY year, sex, age"
    if table == "summary":
        sql = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY year"

    with sqlite3.connect(catalog_path) as conn:
        try:
            return pd.read_sql_query(sql, conn, params=params)
        except Exception as error:
            if "no such table" not in str(error):
                raise
            return pd.DataFrame()


def _maybe_use_catalog(
    *,
    table: str,
    query: ScenarioQuery,
    catalog_path: Path,
) -> pd.DataFrame | None:
    if not _catalog_eligible(query):
        return None

    path = _catalog_ready(catalog_path)
    frame = _query_catalog_table(
        table=table,
        query=query,
        catalog_path=path,
    )
    if frame.empty and query.source == "catalog":
        raise ValueError("Requested scenario is not available in the shipped analytic catalog")

    if frame.empty:
        return None

    return frame


def get_population_pyramid(
    query: ScenarioQuery,
    *,
    catalog_path: Path = ANALYTIC_CATALOG_DB_PATH,
) -> pd.DataFrame:
    validated_query, _ = _validate_query(query)
    _require_catalog_support(validated_query)
    if validated_query.year is None:
        raise ValueError("get_population_pyramid requires query.year")

    catalog_frame = _maybe_use_catalog(
        table="population",
        query=validated_query,
        catalog_path=catalog_path,
    )
    if catalog_frame is not None:
        return catalog_frame

    population_frame, _ = _project_query_scenario(validated_query)
    frame = population_frame[population_frame["year"] == int(validated_query.year)].copy()
    if validated_query.sex is not None:
        frame = frame[frame["sex"] == validated_query.sex].copy()
    return frame.reset_index(drop=True)


def get_population_size(
    query: ScenarioQuery,
    *,
    catalog_path: Path = ANALYTIC_CATALOG_DB_PATH,
) -> pd.DataFrame:
    validated_query, _ = _validate_query(query)
    _require_catalog_support(validated_query)

    catalog_frame = _maybe_use_catalog(
        table="summary",
        query=validated_query,
        catalog_path=catalog_path,
    )
    if catalog_frame is not None:
        return catalog_frame

    _, summary_frame = _project_query_scenario(validated_query)
    frame = summary_frame.copy()
    if validated_query.year is not None:
        frame = frame[frame["year"] == int(validated_query.year)].copy()
    return frame.reset_index(drop=True)
