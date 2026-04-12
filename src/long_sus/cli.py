from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .query import (
    get_population_pyramid,
    get_population_size,
    list_supported_countries,
    list_supported_schemes,
    project_analytic_scenario,
)
from .specs import ScenarioQuery


def _frame_to_text(frame: pd.DataFrame, output_format: str) -> str:
    if output_format == "json":
        return frame.to_json(orient="records", indent=2)

    if output_format == "csv":
        return frame.to_csv(index=False)

    return frame.to_string(index=False)


def _build_query(args: argparse.Namespace) -> ScenarioQuery:
    return ScenarioQuery(
        country=args.country,
        scheme_id=args.scheme_id,
        target=args.target,
        factor=args.factor,
        branch=args.branch,
        year=args.year,
        sex=getattr(args, "sex", None),
        threshold_age=getattr(args, "threshold_age", None),
        threshold_probability=getattr(args, "threshold_probability", None),
        rollout_curve=getattr(args, "rollout_curve", None),
        rollout_launch_probability=getattr(args, "rollout_launch_probability", None),
        rollout_max_probability=getattr(args, "rollout_max_probability", None),
        rollout_ramp_years=getattr(args, "rollout_ramp_years", None),
        rollout_takeoff_years=getattr(args, "rollout_takeoff_years", None),
        source=args.source,
    )


def _add_query_args(parser: argparse.ArgumentParser, *, require_year: bool) -> None:
    parser.add_argument("--country", required=True)
    parser.add_argument("--scheme-id", required=True)
    parser.add_argument("--target", default="none")
    parser.add_argument("--factor", type=float, default=1.0)
    parser.add_argument("--branch", default="analytic_arm")
    parser.add_argument("--source", default="auto")
    parser.add_argument("--year", type=int, required=require_year)
    parser.add_argument("--threshold-age", type=int)
    parser.add_argument("--threshold-probability", type=float)
    parser.add_argument("--rollout-curve")
    parser.add_argument("--rollout-launch-probability", type=float)
    parser.add_argument("--rollout-max-probability", type=float)
    parser.add_argument("--rollout-ramp-years", type=int)
    parser.add_argument("--rollout-takeoff-years", type=int)


def _print_frame(frame: pd.DataFrame, output_format: str) -> None:
    print(_frame_to_text(frame, output_format))


def _handle_countries(args: argparse.Namespace) -> int:
    frame = pd.DataFrame(list_supported_countries())
    _print_frame(frame, args.format)
    return 0


def _handle_schemes(args: argparse.Namespace) -> int:
    frame = pd.DataFrame(list_supported_schemes())
    _print_frame(frame, args.format)
    return 0


def _handle_pyramid(args: argparse.Namespace) -> int:
    query = _build_query(args)
    if args.catalog_path:
        frame = get_population_pyramid(query, catalog_path=Path(args.catalog_path))
    else:
        frame = get_population_pyramid(query)
    _print_frame(frame, args.format)
    return 0


def _handle_size(args: argparse.Namespace) -> int:
    query = _build_query(args)
    if args.catalog_path:
        frame = get_population_size(query, catalog_path=Path(args.catalog_path))
    else:
        frame = get_population_size(query)
    _print_frame(frame, args.format)
    return 0


def _handle_project(args: argparse.Namespace) -> int:
    query = _build_query(args)
    population_frame, summary_frame = project_analytic_scenario(query)

    if args.population_out:
        population_path = Path(args.population_out)
        population_path.parent.mkdir(parents=True, exist_ok=True)
        population_frame.to_csv(population_path, index=False)

    if args.summary_out:
        summary_path = Path(args.summary_out)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_frame.to_csv(summary_path, index=False)

    _print_frame(summary_frame, args.format)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="long-sus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    countries_parser = subparsers.add_parser("countries")
    countries_parser.add_argument("--format", default="table", choices=("table", "csv", "json"))
    countries_parser.set_defaults(handler=_handle_countries)

    schemes_parser = subparsers.add_parser("schemes")
    schemes_parser.add_argument("--format", default="table", choices=("table", "csv", "json"))
    schemes_parser.set_defaults(handler=_handle_schemes)

    pyramid_parser = subparsers.add_parser("pyramid")
    _add_query_args(pyramid_parser, require_year=True)
    pyramid_parser.add_argument("--sex")
    pyramid_parser.add_argument("--catalog-path")
    pyramid_parser.add_argument("--format", default="table", choices=("table", "csv", "json"))
    pyramid_parser.set_defaults(handler=_handle_pyramid)

    size_parser = subparsers.add_parser("size")
    _add_query_args(size_parser, require_year=False)
    size_parser.add_argument("--catalog-path")
    size_parser.add_argument("--format", default="table", choices=("table", "csv", "json"))
    size_parser.set_defaults(handler=_handle_size)

    project_parser = subparsers.add_parser("project")
    _add_query_args(project_parser, require_year=False)
    project_parser.add_argument("--format", default="table", choices=("table", "csv", "json"))
    project_parser.add_argument("--population-out")
    project_parser.add_argument("--summary-out")
    project_parser.set_defaults(handler=_handle_project)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
