from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib
import json
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_sus.config import WPP_API_BASE
from long_sus.countries import list_supported_country_specs
from long_sus.data_sources import WppApiClient

from render_baseline_fit_diagnostics import render_all_fit_diagnostics


AGEING_PACKAGES_ROOT = Path(
    "/Users/benshenhar/Library/CloudStorage/GoogleDrive-benshenhar@gmail.com/"
    "My Drive/Weizmann/Alon Lab/Aging/python/ageing_packages"
)
USA_BASELINE_JSON_PATH = Path(
    "/Users/benshenhar/Library/CloudStorage/GoogleDrive-benshenhar@gmail.com/"
    "My Drive/Weizmann/Alon Lab/Aging/python/saved_results/"
    "sr_fitter_full_2026_04_01/usa_period_2019_both_hazard_age30_100_xc18.json"
)

OUTPUT_DIR = PROJECT_ROOT / "baseline_fits"
OUTPUT_JSON_PATH = OUTPUT_DIR / "country_baseline_fits_2024.json"

POPULATION_INDICATOR_ID = 47
MORTALITY_INDICATOR_ID = 80
MEDIAN_VARIANT_ID = 4
FIT_YEAR = 2024
FIRST_AVAILABLE_YEAR = 1950

COUNTRIES = {
    country.slug: {
        "label": country.name,
        "location_id": country.location_id,
        "default_analytic_preset_id": country.default_analytic_preset_id,
    }
    for country in list_supported_country_specs()
}

HIGH_AGE_WEIGHTING = {
    "usa": {
        "age_start": 70,
        "age_end": 100,
        "max_multiplier": 14.0,
        "power": 2.0,
    },
    "brazil": {
        "age_start": 70,
        "age_end": 90,
        "max_multiplier": 18.0,
        "power": 2.2,
    },
    "china": {
        "age_start": 70,
        "age_end": 90,
        "max_multiplier": 18.0,
        "power": 2.2,
    },
    "nigeria": {
        "age_start": 70,
        "age_end": 90,
        "max_multiplier": 18.0,
        "power": 2.2,
    },
    "south_africa": {
        "age_start": 70,
        "age_end": 100,
        "max_multiplier": 14.0,
        "power": 2.0,
    },
}

FIT_CONFIG = {
    "age_start": 30,
    "age_end": 100,
    "dt": 0.025,
    "tmax": 110.0,
    "fit_params": ("eta", "beta", "epsilon", "Xc"),
    "fit_kappa": False,
    "xc_std_frac": 0.18,
    "fit_xc_std": False,
    "h_ext_mode": "fixed_from_mgg",
    "stage1_screen_size": 10,
    "stage1_hazard_n": 8_000,
    "stage1_survival_n": 3_000,
    "stage3_hazard_n": 15_000,
    "stage3_survival_n": 6_000,
    "stage2_top_k": 2,
    "stage3_top_k": 1,
    "stage2_step_sizes": (0.5, 0.25, 0.125),
    "stage4_step_sizes": (0.125, 0.0625),
    "hazard_objective": "log_rmse",
    "survival_objective": "linear_rmse",
    "parallel_simulation": False,
}


def _load_sr_fitter():
    if "ageing_packages" not in sys.modules:
        pkg = types.ModuleType("ageing_packages")
        pkg.__path__ = [str(AGEING_PACKAGES_ROOT)]
        sys.modules["ageing_packages"] = pkg

    if "ageing_packages.utils" not in sys.modules:
        pkg = types.ModuleType("ageing_packages.utils")
        pkg.__path__ = [str(AGEING_PACKAGES_ROOT / "utils")]
        sys.modules["ageing_packages.utils"] = pkg

    if "ageing_packages.utils.sr_fits" not in sys.modules:
        stub = types.ModuleType("ageing_packages.utils.sr_fits")
        stub.build_sr_fit_record = lambda **kwargs: kwargs
        stub.save_sr_fit_record = lambda **kwargs: None
        sys.modules["ageing_packages.utils.sr_fits"] = stub

    return importlib.import_module("ageing_packages.utils.sr_fitter")


def _baseline_scalar_params(sr_fitter) -> dict[str, float]:
    raw = sr_fitter.load_baseline_human_params_dict()
    baseline: dict[str, float] = {}

    for key, value in raw.items():
        if np.isscalar(value):
            baseline[key] = float(value)
            continue
        baseline[key] = float(np.asarray(value, dtype=float).ravel()[0])

    return baseline


def _mgg_hazard(t: np.ndarray, a: float, b: float, c: float, m: float) -> np.ndarray:
    exp_bt = np.exp(b * t)
    exp_c = np.exp(c)
    return m + a * exp_bt * (exp_c / (exp_c + exp_bt - 1))


def _estimate_h_ext_from_hazard(times: np.ndarray, hazard: np.ndarray) -> float:
    mask = np.isfinite(times) & np.isfinite(hazard) & (hazard > 0.0)
    fit_times = np.asarray(times[mask], dtype=float)
    fit_hazard = np.asarray(hazard[mask], dtype=float)

    if fit_times.size == 0:
        raise ValueError("Cannot estimate h_ext from an empty hazard curve.")

    popt, _ = curve_fit(
        lambda t, a, b, c, m: np.log(_mgg_hazard(t, a, b, c, m)),
        fit_times,
        np.log(fit_hazard),
        p0=[5e-5, 0.1, 9.0, 0.005],
        maxfev=20000,
    )
    return float(max(popt[3], 0.0))


def _usa_initial_vector(sr_fitter) -> tuple[float, ...]:
    payload = json.loads(USA_BASELINE_JSON_PATH.read_text())
    baseline = _baseline_scalar_params(sr_fitter)
    fit_order = FIT_CONFIG["fit_params"]

    vector: list[float] = []
    for key in fit_order:
        target_value = float(payload["fit_params"][key])
        base_value = float(baseline[key])
        vector.append(float(np.log2(target_value / base_value)))

    return tuple(vector)


def _dimension_ids(metadata: dict, key: str, allowed_values: set[str] | None = None) -> list[int]:
    ids: list[int] = []
    for item in metadata["availableDimensions"][key]:
        value = str(item["dimensionValue"])
        if allowed_values is not None and value not in allowed_values:
            continue
        ids.append(int(item["dimensionId"]))
    return ids


def _age_lookup(metadata: dict) -> dict[int, int]:
    return {
        int(item["dimensionId"]): int(str(item["dimensionValue"]).replace("100+", "100"))
        for item in metadata["availableDimensions"]["ages"]
    }


def _normalize_age_sex_frame(records: list[dict], value_column: str, age_lookup: dict[int, int]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    frame["age"] = frame["ageId"].map(age_lookup).astype(int)
    frame["sex"] = frame["sexId"].map({1: "male", 2: "female"})
    frame["year"] = frame["timeLabel"].astype(int)
    frame = frame.rename(columns={"value": value_column})
    return frame[["year", "sex", "age", value_column]].sort_values(["year", "sex", "age"]).reset_index(drop=True)


def _fetch_country_wpp_curves(client: WppApiClient, location_id: int, year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    population_metadata = client.fetch_indicator_metadata(POPULATION_INDICATOR_ID)
    mortality_metadata = client.fetch_indicator_metadata(MORTALITY_INDICATOR_ID)

    population_records = client.fetch_indicator_records(
        indicator_id=POPULATION_INDICATOR_ID,
        years=[year],
        ages=_dimension_ids(population_metadata, "ages"),
        sexes=_dimension_ids(population_metadata, "sexes", {"Male", "Female"}),
        variant_id=MEDIAN_VARIANT_ID,
        location_id=location_id,
        categories=[population_metadata["defaultCategoryId"]],
    )
    mortality_records = client.fetch_indicator_records(
        indicator_id=MORTALITY_INDICATOR_ID,
        years=[year],
        ages=_dimension_ids(mortality_metadata, "ages"),
        sexes=_dimension_ids(mortality_metadata, "sexes", {"Male", "Female"}),
        variant_id=MEDIAN_VARIANT_ID,
        location_id=location_id,
        categories=[mortality_metadata["defaultCategoryId"]],
    )

    population = _normalize_age_sex_frame(population_records, "population", _age_lookup(population_metadata))
    mortality = _normalize_age_sex_frame(mortality_records, "mx", _age_lookup(mortality_metadata))
    return population, mortality


def _all_sex_hazard(population: pd.DataFrame, mortality: pd.DataFrame) -> pd.DataFrame:
    merged = population.merge(mortality, on=["year", "sex", "age"], how="inner", validate="one_to_one")
    grouped = (
        merged.groupby("age", as_index=False)
        .apply(
            lambda group: pd.Series(
                {
                    "population": float(group["population"].sum()),
                    "mx": float(np.average(group["mx"], weights=group["population"])),
                }
            ),
            include_groups=False,
        )
        .sort_values("age")
        .reset_index(drop=True)
    )
    return grouped


def _build_fit_weights(slug: str, hazard: pd.DataFrame) -> np.ndarray:
    weights = hazard["population"].to_numpy(dtype=float).copy()
    rule = HIGH_AGE_WEIGHTING.get(slug)
    if rule is None:
        return weights

    ages = hazard["age"].to_numpy(dtype=float)
    start_age = float(rule["age_start"])
    end_age = float(rule["age_end"])
    max_multiplier = float(rule["max_multiplier"])
    power = float(rule["power"])

    ramp = np.clip((ages - start_age) / max(end_age - start_age, 1.0), 0.0, 1.0)
    multiplier = 1.0 + (max_multiplier - 1.0) * np.power(ramp, power)
    return weights * multiplier


def _fit_country(slug: str, country: dict[str, object], sr_fitter) -> dict[str, object]:
    client = WppApiClient(base_url=WPP_API_BASE)
    population, mortality = _fetch_country_wpp_curves(client, int(country["location_id"]), FIT_YEAR)
    hazard = _all_sex_hazard(population, mortality)
    fit_weights = _build_fit_weights(slug, hazard)

    config_kwargs = dict(FIT_CONFIG)
    if slug == "usa":
        config_kwargs["initial_vectors"] = (_usa_initial_vector(sr_fitter),)

    config = sr_fitter.SRFitConfig(
        **config_kwargs,
        save_dir=str(OUTPUT_DIR),
    )
    target = sr_fitter._build_array_target(
        times=hazard["age"].to_numpy(),
        values=hazard["mx"].to_numpy(),
        target="hazard",
        config=config,
        weights=fit_weights,
    )
    h_ext = _estimate_h_ext_from_hazard(
        times=hazard["age"].to_numpy(),
        hazard=hazard["mx"].to_numpy(),
    )

    print(f"[start] {country['label']} {FIT_YEAR} | h_ext={h_ext:.6g}", flush=True)
    fit_result = sr_fitter._run_fit(
        case_label=f"{country['label']} both period {FIT_YEAR}",
        primary_target=target,
        cross_target=None,
        h_ext=h_ext,
        config=config,
    )
    print(f"[done] {country['label']} {FIT_YEAR}: score = {fit_result.score:.6f}", flush=True)

    result = asdict(fit_result)
    result["country"] = country["label"]
    result["location_id"] = int(country["location_id"])
    result["fit_year"] = FIT_YEAR
    result["first_wpp_year_checked"] = FIRST_AVAILABLE_YEAR
    result["estimated_h_ext_from_mgg"] = h_ext
    result["wpp_all_sex_hazard_curve"] = hazard.to_dict(orient="records")
    result["fit_weights"] = fit_weights.tolist()
    result["high_age_weighting_rule"] = HIGH_AGE_WEIGHTING.get(slug)
    result["wpp_population_curve"] = population.to_dict(orient="records")
    result["wpp_mortality_curve"] = mortality.to_dict(orient="records")
    result["used_usa_warm_start"] = slug == "usa"
    result["warm_start_source_json"] = str(USA_BASELINE_JSON_PATH) if slug == "usa" else None
    return result


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fit baseline SR parameters for supported countries.",
    )
    parser.add_argument(
        "--countries",
        nargs="+",
        metavar="COUNTRY",
        help="Country slugs to update, for example: brazil china nigeria",
    )
    return parser


def _resolve_selected_slugs(country_values: list[str] | None) -> list[str]:
    if not country_values:
        return list(COUNTRIES)

    selected_slugs: list[str] = []
    unknown_slugs: list[str] = []

    for raw_value in country_values:
        slug = raw_value.strip().lower().replace(" ", "_").replace("-", "_")
        if slug in COUNTRIES:
            selected_slugs.append(slug)
            continue
        unknown_slugs.append(raw_value)

    if unknown_slugs:
        supported = ", ".join(sorted(COUNTRIES))
        unknown = ", ".join(unknown_slugs)
        raise SystemExit(f"Unknown country slugs: {unknown}. Supported: {supported}")

    return selected_slugs


def _load_existing_payload() -> dict[str, object]:
    if OUTPUT_JSON_PATH.exists():
        return json.loads(OUTPUT_JSON_PATH.read_text())

    return {
        "wpp_source": WPP_API_BASE,
        "fit_year": FIT_YEAR,
        "first_available_year_for_world_south_africa_italy_uganda": FIRST_AVAILABLE_YEAR,
        "population_indicator_id": POPULATION_INDICATOR_ID,
        "mortality_indicator_id": MORTALITY_INDICATOR_ID,
        "variant_id": MEDIAN_VARIANT_ID,
        "fit_config": {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in FIT_CONFIG.items()
        },
        "countries": {},
    }


def main() -> None:
    args = _build_argument_parser().parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sr_fitter = _load_sr_fitter()
    selected_slugs = _resolve_selected_slugs(args.countries)
    payload = _load_existing_payload()

    payload["wpp_source"] = WPP_API_BASE
    payload["fit_year"] = FIT_YEAR
    payload["first_available_year_for_world_south_africa_italy_uganda"] = FIRST_AVAILABLE_YEAR
    payload["population_indicator_id"] = POPULATION_INDICATOR_ID
    payload["mortality_indicator_id"] = MORTALITY_INDICATOR_ID
    payload["variant_id"] = MEDIAN_VARIANT_ID
    payload["fit_config"] = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in FIT_CONFIG.items()
    }
    payload.setdefault("countries", {})

    for slug in selected_slugs:
        country = COUNTRIES[slug]
        payload["countries"][slug] = _fit_country(slug, country, sr_fitter)

    OUTPUT_JSON_PATH.write_text(json.dumps(payload, indent=2))
    print(OUTPUT_JSON_PATH)

    diagnostic_paths = render_all_fit_diagnostics(
        fit_json_path=OUTPUT_JSON_PATH,
        country_slugs=selected_slugs,
    )
    for diagnostic_path in diagnostic_paths:
        print(diagnostic_path)


if __name__ == "__main__":
    main()
