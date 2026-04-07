from __future__ import annotations

import pandas as pd

from .specs import UsaCalibrationPreset
from .sr_intervention import build_sr_intervention_asset


def build_sr_hazard_multiplier(
    preset: UsaCalibrationPreset,
    target: str | None,
    param_factor: float,
    *,
    start_age: int = 0,
) -> pd.DataFrame:
    """
    Backward-compatible adapter.

    The old code returned one age-only multiplier curve. The corrected model now
    builds a full start-age-conditioned surface in `sr_intervention.py`.
    This helper exposes one chosen start-age row so older call sites can fail
    less abruptly while the rest of the codebase moves to the surface API.
    """
    if target is None:
        target = "eta"
        param_factor = 1.0

    asset = build_sr_intervention_asset(
        preset=preset,
        target=target,
        factor=param_factor,
    )
    start_row = int(start_age)
    multiplier = asset.annual_hazard_multiplier[start_row]

    return pd.DataFrame(
        {
            "age": asset.ages.astype(int),
            "hazard_multiplier": multiplier.astype(float),
            "preset": preset.name,
            "target": target,
            "param_factor": float(param_factor),
            "start_age": start_row,
        }
    )
