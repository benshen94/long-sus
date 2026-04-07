from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import ANALYTIC_CATALOG_DB_PATH
from .countries import CountrySpec, get_country_spec, list_supported_country_specs
from .data_sources import download_country_wpp_bundle
from .intervention_assets import ANALYTIC_BRANCH, select_intervention_asset
from .projection import build_variant_inputs, project_scenario
from .scenarios import build_public_catalog_scenarios
from .specs import ScenarioSpec


def _normalize_country_specs(countries: list[str | CountrySpec] | None) -> list[CountrySpec]:
    if countries is None:
        return list_supported_country_specs()

    return [get_country_spec(country) for country in countries]


def _default_country_scenarios(country_spec: CountrySpec) -> list[ScenarioSpec]:
    return build_public_catalog_scenarios(
        country=country_spec.name,
        branch=ANALYTIC_BRANCH,
        analytic_preset_id=country_spec.default_analytic_preset_id,
    )


def _initialize_catalog_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def _write_metadata(
    conn: sqlite3.Connection,
    *,
    countries: list[CountrySpec],
    include_population: bool,
    include_summary: bool,
) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "countries": [country.name for country in countries],
        "include_population": include_population,
        "include_summary": include_summary,
    }
    conn.execute("DELETE FROM metadata")
    conn.execute(
        "INSERT INTO metadata(key, value) VALUES(?, ?)",
        ("build_info", json.dumps(payload, indent=2)),
    )


def _create_indexes(conn: sqlite3.Connection) -> None:
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }

    if "population" in tables:
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_population_lookup
            ON population (
                country,
                branch,
                scheme_id,
                target,
                factor,
                year,
                sex
            );
            """
        )

    if "summary" in tables:
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_summary_lookup
            ON summary (
                country,
                branch,
                scheme_id,
                target,
                factor,
                year
            );
            """
        )


def build_analytic_catalog(
    *,
    path: Path = ANALYTIC_CATALOG_DB_PATH,
    countries: list[str | CountrySpec] | None = None,
    scenarios_by_country: dict[str, list[ScenarioSpec]] | None = None,
    include_population: bool = True,
    include_summary: bool = True,
    force: bool = False,
) -> Path:
    if path.exists() and not force:
        return path

    if force and path.exists():
        path.unlink()

    path.parent.mkdir(parents=True, exist_ok=True)
    country_specs = _normalize_country_specs(countries)

    with sqlite3.connect(path) as conn:
        _initialize_catalog_db(conn)

        for country_spec in country_specs:
            bundle = download_country_wpp_bundle(country_spec)
            inputs = build_variant_inputs(bundle, "medium")
            scenarios = (
                scenarios_by_country[country_spec.name]
                if scenarios_by_country and country_spec.name in scenarios_by_country
                else _default_country_scenarios(country_spec)
            )

            for scenario in scenarios:
                asset = select_intervention_asset(
                    scenario=scenario,
                    inputs=inputs,
                    sr_intervention_grid=None,
                )
                population_frame, summary_frame = project_scenario(
                    scenario=scenario,
                    inputs=inputs,
                    intervention_asset=asset,
                )
                if include_population:
                    population_frame.to_sql("population", conn, if_exists="append", index=False)
                if include_summary:
                    summary_frame.to_sql("summary", conn, if_exists="append", index=False)

        _write_metadata(
            conn,
            countries=country_specs,
            include_population=include_population,
            include_summary=include_summary,
        )
        _create_indexes(conn)

    return path
