from __future__ import annotations

from enum import Enum
from io import StringIO

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from .query import get_population_pyramid, get_population_size, list_supported_countries, list_supported_schemes
from .specs import ScenarioQuery


class OutputFormat(str, Enum):
    json = "json"
    csv = "csv"


def _build_query(
    *,
    country: str,
    scheme_id: str,
    target: str,
    factor: float,
    branch: str,
    year: int | None,
    sex: str | None,
    launch_year: int,
    projection_end_year: int | None,
    analytic_preset_id: str | None,
    threshold_age: int | None,
    threshold_probability: float | None,
    rollout_curve: str | None,
    rollout_launch_probability: float | None,
    rollout_max_probability: float | None,
    rollout_ramp_years: int | None,
    rollout_takeoff_years: int | None,
    hetero_mode: str,
    source: str,
) -> ScenarioQuery:
    return ScenarioQuery(
        country=country,
        scheme_id=scheme_id,
        target=target,
        factor=factor,
        branch=branch,
        year=year,
        sex=sex,
        launch_year=launch_year,
        projection_end_year=projection_end_year,
        analytic_preset_id=analytic_preset_id,
        threshold_age=threshold_age,
        threshold_probability=threshold_probability,
        rollout_curve=rollout_curve,
        rollout_launch_probability=rollout_launch_probability,
        rollout_max_probability=rollout_max_probability,
        rollout_ramp_years=rollout_ramp_years,
        rollout_takeoff_years=rollout_takeoff_years,
        hetero_mode=hetero_mode,
        source=source,
    )


def _frame_response(frame: pd.DataFrame, output_format: OutputFormat) -> Response:
    if output_format == OutputFormat.csv:
        buffer = StringIO()
        frame.to_csv(buffer, index=False)
        return PlainTextResponse(buffer.getvalue(), media_type="text/csv")

    return Response(
        content=frame.to_json(orient="records"),
        media_type="application/json",
    )


def _handle_query_error(error: Exception) -> None:
    raise HTTPException(status_code=400, detail=str(error)) from error


def create_app() -> FastAPI:
    app = FastAPI(
        title="Long-SUS API",
        version="0.1.0",
        description="URL-query API for Long-SUS population projections.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Long-SUS API</title>
    <style>
      body { font-family: system-ui, sans-serif; max-width: 880px; margin: 40px auto; line-height: 1.5; padding: 0 20px; }
      code, pre { background: #f4f4f4; border-radius: 4px; }
      code { padding: 2px 4px; }
      pre { padding: 12px; overflow-x: auto; }
    </style>
  </head>
  <body>
    <h1>Long-SUS API</h1>
    <p>Use <code>/population-pyramid</code> for year-age-sex population rows and <code>/population-size</code> for yearly totals.</p>
    <pre>/population-pyramid?country=World&scheme_id=threshold_age_60_all_eligible&target=Xc&factor=1.2&branch=analytic_arm&year=2050</pre>
    <p>Interactive schema: <a href="/docs">/docs</a></p>
  </body>
</html>
"""

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/countries")
    def countries() -> list[dict[str, object]]:
        return list_supported_countries()

    @app.get("/schemes")
    def schemes() -> list[dict[str, object]]:
        return list_supported_schemes()

    @app.get("/population-pyramid")
    def population_pyramid(
        country: str = Query(..., examples=["World", "USA", "Israel"]),
        scheme_id: str = Query(..., examples=["threshold_age_60_all_eligible"]),
        target: str = Query("none", examples=["none", "eta", "eta_shift", "Xc"]),
        factor: float = Query(1.0),
        branch: str = Query("analytic_arm"),
        year: int = Query(..., ge=2024),
        sex: str | None = Query(None, examples=["male", "female"]),
        launch_year: int = Query(2025),
        projection_end_year: int | None = Query(2100),
        analytic_preset_id: str | None = Query(None),
        threshold_age: int | None = Query(None),
        threshold_probability: float | None = Query(None, ge=0.0, le=1.0),
        rollout_curve: str | None = Query(None, examples=["linear", "logistic"]),
        rollout_launch_probability: float | None = Query(None, ge=0.0, le=1.0),
        rollout_max_probability: float | None = Query(None, ge=0.0, le=1.0),
        rollout_ramp_years: int | None = Query(None, gt=0),
        rollout_takeoff_years: int | None = Query(None, gt=0),
        hetero_mode: str = Query("off"),
        source: str = Query("auto", examples=["auto", "catalog", "project"]),
        format: OutputFormat = Query(OutputFormat.json),
    ) -> Response:
        query = _build_query(
            country=country,
            scheme_id=scheme_id,
            target=target,
            factor=factor,
            branch=branch,
            year=year,
            sex=sex,
            launch_year=launch_year,
            projection_end_year=projection_end_year,
            analytic_preset_id=analytic_preset_id,
            threshold_age=threshold_age,
            threshold_probability=threshold_probability,
            rollout_curve=rollout_curve,
            rollout_launch_probability=rollout_launch_probability,
            rollout_max_probability=rollout_max_probability,
            rollout_ramp_years=rollout_ramp_years,
            rollout_takeoff_years=rollout_takeoff_years,
            hetero_mode=hetero_mode,
            source=source,
        )
        try:
            frame = get_population_pyramid(query)
        except Exception as error:
            _handle_query_error(error)

        return _frame_response(frame, format)

    @app.get("/population-size")
    def population_size(
        country: str = Query(..., examples=["World", "USA", "Israel"]),
        scheme_id: str = Query(..., examples=["threshold_age_60_all_eligible"]),
        target: str = Query("none", examples=["none", "eta", "eta_shift", "Xc"]),
        factor: float = Query(1.0),
        branch: str = Query("analytic_arm"),
        year: int | None = Query(None, ge=2024),
        launch_year: int = Query(2025),
        projection_end_year: int | None = Query(2100),
        analytic_preset_id: str | None = Query(None),
        threshold_age: int | None = Query(None),
        threshold_probability: float | None = Query(None, ge=0.0, le=1.0),
        rollout_curve: str | None = Query(None, examples=["linear", "logistic"]),
        rollout_launch_probability: float | None = Query(None, ge=0.0, le=1.0),
        rollout_max_probability: float | None = Query(None, ge=0.0, le=1.0),
        rollout_ramp_years: int | None = Query(None, gt=0),
        rollout_takeoff_years: int | None = Query(None, gt=0),
        hetero_mode: str = Query("off"),
        source: str = Query("auto", examples=["auto", "catalog", "project"]),
        format: OutputFormat = Query(OutputFormat.json),
    ) -> Response:
        query = _build_query(
            country=country,
            scheme_id=scheme_id,
            target=target,
            factor=factor,
            branch=branch,
            year=year,
            sex=None,
            launch_year=launch_year,
            projection_end_year=projection_end_year,
            analytic_preset_id=analytic_preset_id,
            threshold_age=threshold_age,
            threshold_probability=threshold_probability,
            rollout_curve=rollout_curve,
            rollout_launch_probability=rollout_launch_probability,
            rollout_max_probability=rollout_max_probability,
            rollout_ramp_years=rollout_ramp_years,
            rollout_takeoff_years=rollout_takeoff_years,
            hetero_mode=hetero_mode,
            source=source,
        )
        try:
            frame = get_population_size(query)
        except Exception as error:
            _handle_query_error(error)

        return _frame_response(frame, format)

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("long_sus.api:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
