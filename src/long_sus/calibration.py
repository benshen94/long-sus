from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import OptimizeWarning

from .config import PROCESSED_CALIBRATION_DIR
from .data_sources import load_hfd_if_available, load_hmd_period_data
from .external_paths import ensure_ageing_python_path


@dataclass
class CalibrationOutputs:
    parameters: pd.DataFrame
    curves: pd.DataFrame
    hfd_available: bool


def _load_gamma_gompertz():
    ensure_ageing_python_path()
    from ageing_packages.mortality_models.gamma_gompertz import GammaGompertz  # type: ignore

    return GammaGompertz


def fit_usa_mgg_benchmarks(year: int = 2019, min_age: int = 40, max_age: int = 95) -> CalibrationOutputs:
    GammaGompertz = _load_gamma_gompertz()
    parameter_rows: list[dict[str, float | int | str]] = []
    curve_frames: list[pd.DataFrame] = []

    for sex in ("male", "female"):
        hmd = load_hmd_period_data(sex)
        sample = hmd[(hmd["year"] == year) & (hmd["age"].between(min_age, max_age))].copy()
        if sample.empty:
            raise ValueError(f"No HMD data for sex={sex}, year={year}")

        sample = sample[sample["mx"] > 0].copy()
        model = GammaGompertz()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            warnings.simplefilter("ignore", OptimizeWarning)
            model.fit_params(
                time_array=sample["age"].to_numpy(),
                log10_hazard_array=np.log10(sample["mx"].to_numpy()),
                print_out=False,
            )

        predicted_hazard = model.hazard_function(
            sample["age"].to_numpy(),
            model.a,
            model.b,
            model.c,
            model.m,
        )

        parameter_rows.append(
            {
                "sex": sex,
                "year": year,
                "a": model.a,
                "b": model.b,
                "c": model.c,
                "m": model.m,
                "min_age": min_age,
                "max_age": max_age,
            }
        )

        curve_frames.append(
            pd.DataFrame(
                {
                    "sex": sex,
                    "year": year,
                    "age": sample["age"].to_numpy(),
                    "hmd_mx": sample["mx"].to_numpy(),
                    "mgg_mx": predicted_hazard,
                }
            )
        )

    parameters = pd.DataFrame(parameter_rows)
    curves = pd.concat(curve_frames, ignore_index=True)

    PROCESSED_CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    parameters.to_csv(PROCESSED_CALIBRATION_DIR / "usa_mgg_parameters.csv", index=False)
    curves.to_csv(PROCESSED_CALIBRATION_DIR / "usa_mgg_curves.csv", index=False)

    return CalibrationOutputs(
        parameters=parameters,
        curves=curves,
        hfd_available=load_hfd_if_available() is not None,
    )
