from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class AgeBandUptake:
    start_age: int
    end_age: int | None
    target_share: float


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    label: str = ""
    scheme_id: str = ""
    country: str = "USA"
    mode: str = "dynamic"
    launch_year: int = 2025
    projection_end_year: int | None = None
    uptake_mode: str = "threshold"
    threshold_age: int | None = None
    bands: tuple[AgeBandUptake, ...] = ()
    start_rule_within_band: str = "absolute"
    target: str | None = None
    factor: float = 1.0
    branch: str = "sr"
    analytic_preset_id: str | None = None
    persistence_rule: str = "once_on_stay_on"
    demo_variant: str = "medium"
    migration_mode: str = "on"
    hetero_mode: str = "off"
    steady_state_anchor_year: int | None = None


@dataclass(frozen=True)
class UsaCalibrationPreset:
    name: str
    use_heterogeneity: bool = False
    heterogeneity_param: str = "Xc"
    heterogeneity_std: float = 0.2


@dataclass(frozen=True)
class FigureArtifact:
    title: str
    path: Path
    caption: str


@dataclass(frozen=True)
class DashboardArtifact:
    title: str
    path: Path


@dataclass(frozen=True)
class InterventionAsset:
    target: str
    factor: float
    hetero_mode: str
    start_ages: np.ndarray
    ages: np.ndarray
    annual_hazard_multiplier: np.ndarray
    baseline_survival: np.ndarray
    survival_by_start_age: np.ndarray


SRInterventionAsset = InterventionAsset


@dataclass
class ProjectionState:
    untreated: dict[str, np.ndarray]
    treated: dict[str, np.ndarray]


@dataclass
class ForecastArtifacts:
    population_path: Path
    summary_path: Path
    readme_path: Path
    results_doc_path: Path
    dashboard_path: Path
    pipeline_doc_path: Path
    validation_doc_path: Path
    figures: list[FigureArtifact] = field(default_factory=list)
    dashboard_artifacts: list[DashboardArtifact] = field(default_factory=list)


@dataclass(frozen=True)
class ScenarioQuery:
    country: str
    scheme_id: str
    target: str = "none"
    factor: float = 1.0
    branch: str = "analytic_arm"
    year: int | None = None
    sex: str | None = None
    launch_year: int = 2025
    projection_end_year: int | None = 2100
    analytic_preset_id: str | None = None
    hetero_mode: str = "off"
    source: str = "auto"
