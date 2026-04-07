from .countries import list_supported_countries
from .query import (
    get_population_pyramid,
    get_population_size,
    list_supported_schemes,
    project_analytic_scenario,
)
from .specs import ScenarioQuery


def run_usa_pipeline():
    from .pipeline import run_usa_pipeline as _run_usa_pipeline

    return _run_usa_pipeline()


def build_world_analytic_dashboard_assets():
    from .pipeline import build_world_analytic_dashboard_assets as _build_world_analytic_dashboard_assets

    return _build_world_analytic_dashboard_assets()


def build_public_analytic_catalog():
    from .pipeline import build_public_analytic_catalog as _build_public_analytic_catalog

    return _build_public_analytic_catalog()


__all__ = [
    "ScenarioQuery",
    "build_public_analytic_catalog",
    "build_world_analytic_dashboard_assets",
    "get_population_pyramid",
    "get_population_size",
    "list_supported_countries",
    "list_supported_schemes",
    "project_analytic_scenario",
    "run_usa_pipeline",
]
