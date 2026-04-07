from __future__ import annotations

from pathlib import Path

from .specs import DashboardArtifact, FigureArtifact


ANALYTIC_ARM_FORMULAS = r"""$$
h_0(t) \propto \exp\left[-\frac{X_c}{\epsilon}\left(\beta - \eta t\right)\right].
$$

For an $X_c$ intervention with start age $s$ and factor $f$,

$$
m_{X_c}(s,t;f) =
\begin{cases}
1 & t < s \\
\exp\left[-\frac{(f-1)X_c}{\epsilon}\left(\beta - \eta t\right)\right] & t \ge s
\end{cases}
$$

For an $\eta$ intervention,

$$
m_{\eta}(s,t;f) =
\begin{cases}
1 & t < s \\
\exp\left[-\frac{X_c}{\epsilon}\left(\eta - f\eta\right)(t-s)\right] & t \ge s
\end{cases}
$$"""


def _relative(target: Path, origin: Path) -> str:
    return target.relative_to(origin.parent).as_posix()


def _find_path(items: list[DashboardArtifact] | list[FigureArtifact], title: str) -> Path:
    for item in items:
        if item.title == title:
            return item.path
    raise KeyError(f"Missing documentation artifact: {title}")


def write_results_tutorial(
    *,
    path: Path,
    figures: list[FigureArtifact],
    dashboard_artifacts: list[DashboardArtifact],
) -> None:
    dashboard_shot = _find_path(dashboard_artifacts, "dashboard_overview")
    scheme_compare = _find_path(figures, "Scheme comparison at eta 0.80x")
    factor_compare = _find_path(figures, "Eta factor comparison for threshold age 60")
    baseline_compare = _find_path(figures, "Baseline vs intervention in 2075")
    survival_curves = _find_path(figures, "SR survival curves")
    wpp_reference = _find_path(figures, "WPP vs SR reference curves")
    heatmap = _find_path(figures, "Treated share heatmap")

    text = f"""# Results Tutorial

This generated document keeps the research-result walkthrough separate from the GitHub landing page. It explains the current USA validation build, the main figures, and how to interpret the generated artifacts.

The current validation build answers a narrower question before the full multi-country expansion: if the drug changes `eta` or `Xc`, and treatment starts under different age-based rules, do the projected USA population pyramids change in the way we expect?

The current build is intentionally USA-only. It keeps the demographic backbone fixed to `UN WPP 2024`, uses `HMD 2019` plus `MGG` as the adult benchmark, and now supports two intervention branches in the dashboard:

- `sr`: start-age-conditioned SR surfaces, still precomputed offline
- `analytic_arm`: on-demand hazard multipliers built from a named hazard-fit preset

The browser only loads the heavy SR surfaces when that branch is selected. The analytic arm stays simulation-free inside the browser.

## Flow

```mermaid
flowchart LR
A["USA WPP demography"] --> B["Annual age-sex backbone"]
C["USA HMD 2019 mortality"] --> D["Adult MGG benchmark"]
E["usa_2019 SR preset"] --> F["Untreated baseline SR run from birth"]
F --> G["For each start age, continue the cohort with switched eta or Xc"]
G --> H["Start-age-conditioned SR surfaces"]
I["USA 2019 hazard-fit preset"] --> J["Analytic hazard multipliers by start age"]
B --> K["Browser projection engine"]
H --> K
J --> K
D --> K
K --> L["Population pyramid by year"]
K --> M["Treated-share heatmap"]
K --> N["CSV export and comparison mode"]
```

## Dashboard

![Dashboard overview]({_relative(dashboard_shot, path)})

The dashboard keeps two things separate on purpose:

- `branch`, `target`, and `factor` choose the intervention surface.
- `threshold` or `banded uptake` chooses who starts treatment and when.

That separation is the main modeling correction in this pass. We no longer apply one global age-only hazard multiplier to all treated people. Instead, the browser projection keeps treated cohorts indexed by their actual treatment start age and looks up the correct surface row for each one.

## What Changed In This Rebuild

- `eta` now means a change in slope after treatment start, not a downward jump in accumulated production.
- `Xc` still changes immediately at treatment start.
- Treated people are tracked by `start_age x attained_age`, not in one pooled treated bucket.
- The old global-factor shortcut is gone.
- The dashboard can now switch between the original SR branch and a lighter analytic arm.

## Analytic Arm

The analytic arm starts from the proportional hazard form

{ANALYTIC_ARM_FORMULAS}

In this branch, the untreated cohort baseline comes from launch-year all-sex WPP mortality rather than SR simulation.

## Outputs

### One eta factor, multiple start schemes

![Scheme comparison]({_relative(scheme_compare, path)})

### One start scheme, multiple eta factors

![Eta factor comparison]({_relative(factor_compare, path)})

### Baseline vs intervention

![Baseline comparison]({_relative(baseline_compare, path)})

### SR cohort survival curves

![SR survival curves]({_relative(survival_curves, path)})

### Untreated SR baseline vs WPP backbone

![WPP vs SR reference curves]({_relative(wpp_reference, path)})

### Treated share by age and year

![Treated share heatmap]({_relative(heatmap, path)})

## Related Documentation

- [Pipeline walkthrough](pipeline.md)
- [Dashboard guide](dashboard.md)
- [USA validation scenarios](usa_validation.md)

## Current Boundaries

- This stage is USA-only.
- Future demography is medium-variant WPP only in this pass.
- The first pass exposes `eta` and `Xc`, but the main validation emphasis is still on `eta`.
- The analytic arm is preset-based in v1 and uses the USA 2019 both-sex hazard fit.
- Multi-country SR fitting with `sr_fitter.py` comes after this corrected USA mechanics pass is accepted.
"""
    path.write_text(text)


def write_pipeline_doc(path: Path) -> None:
    text = """# Pipeline Walkthrough

This file explains the corrected USA validation pipeline step by step. The focus is on what each stage does, why it exists, and what modeling choice it introduces.

## End-to-end flow

```mermaid
flowchart TD
A["Load USA WPP population, fertility, mortality, migration"] --> B["Normalize annual age-sex tables"]
C["Load USA HMD period mortality"] --> D["Fit adult MGG benchmark"]
E["Load usa_2019 SR preset"] --> F["Run untreated baseline SR cohort from birth"]
F --> G["For each start age, continue survivors under eta or Xc intervention"]
G --> H["Build start-age-conditioned SR surfaces"]
I["Load analytic hazard-fit preset catalog"] --> J["Build analytic multipliers on demand"]
B --> K["Yearly age-structured population projection"]
H --> K
J --> K
K --> L["Write forecast CSVs"]
H --> M["Write dashboard SR asset files"]
I --> N["Write dashboard analytic preset catalog"]
K --> O["Generate README figures"]
M --> P["Static HTML dashboard"]
N --> P
O --> Q["README and docs"]
P --> Q
```

## 1. USA demography from WPP

What goes in:
- yearly USA population by age and sex
- yearly mortality by age and sex
- yearly fertility by maternal age
- yearly sex ratio at birth
- yearly migration residual

What comes out:
- one clean yearly age-by-sex input bundle

Why this stage exists:
- the projection needs a demographic backbone before any intervention logic is added

What approximation it introduces:
- this pass keeps future demography exogenous and fixed to the WPP medium variant

## 2. Adult untreated benchmark from HMD and MGG

What goes in:
- USA adult period mortality from HMD

What comes out:
- a fitted MGG benchmark curve

Why this stage exists:
- it gives a sanity check against observed adult mortality before we start projecting intervention scenarios

What approximation it introduces:
- MGG is used as an adult benchmark layer, not as the intervention engine

## 3. Untreated SR baseline

What goes in:
- the `usa_2019` SR preset
- optional `Xc` heterogeneity for the sensitivity branch

What comes out:
- one untreated SR cohort simulation from birth
- saved survivor states by age

Why this stage exists:
- the corrected intervention model needs the actual state distribution of survivors at each possible treatment start age

What approximation it introduces:
- the USA validation pass uses one fixed USA baseline preset instead of refitting SR here

## 4. Start-age-conditioned intervention surfaces

What goes in:
- untreated survivor states at age `a_start`
- target parameter (`eta` or `Xc`)
- factor grid

What comes out:
- one hazard-multiplier row for every treatment start age

Why this stage exists:
- treatment does not affect everyone the same way
- someone who starts at 60 should not use the same SR trajectory as someone treated from birth

What approximation it introduces:
- the `sr` branch reads precomputed surfaces from disk
- the `analytic_arm` branch rebuilds the same surface shape directly from the fitted hazard formula

## 5. Leslie-equivalent projection state

What goes in:
- yearly WPP demography
- one scenario definition
- one intervention asset

What comes out:
- yearly population counts by sex and age

Why this stage exists:
- this is where the intervention is combined with births, survival, aging, and migration

What approximation it introduces:
- the code uses explicit vector and tensor updates instead of materializing one giant dense Leslie matrix, but the transition is Leslie-equivalent

## 6. Dashboard assets and docs

What goes in:
- processed demography
- calibration diagnostics
- one analytic preset catalog
- SR intervention surfaces split into deterministic per-asset files
- validation scenario catalog

What comes out:
- a static dashboard asset bundle
- figures and docs

Why this stage exists:
- this validation pass is meant to be inspected visually, not just executed from code
"""
    path.write_text(text)


def write_dashboard_doc(path: Path) -> None:
    text = f"""# Dashboard Guide

This file explains what the dashboard controls do and how to interpret the outputs.

## Core controls

### Branch

Choose which intervention engine to use:
- `sr`: precomputed SR surfaces, loaded on demand
- `analytic_arm`: analytic hazard multipliers built from the named preset

### Target

Choose whether the drug changes:
- `eta`: production slope slows after treatment start, without decreasing accumulated production
- `Xc`: the critical threshold jumps immediately at treatment start

### Factor

In the `sr` branch, this selects the precomputed surface:
- `eta`: `1.00x`, `0.95x`, `0.90x`, `0.85x`, `0.80x`, `0.75x`, `0.70x`
- `Xc`: `1.00x`, `1.10x`, `1.20x`

In the `analytic_arm` branch, this is a positive numeric input.

### Heterogeneity

- `usa_2019`: homogeneous baseline preset
- `usa_2019 + Xc heterogeneity`: same baseline plus Gaussian `Xc` heterogeneity with `std=0.2`

### Analytic preset

The current analytic preset is `usa_period_2019_both_hazard`, the USA 2019 both-sex hazard fit.

The analytic arm uses

{ANALYTIC_ARM_FORMULAS}

### Uptake mode

- `threshold`: everyone above one age starts deterministically
- `banded`: use age bands with one of the PDF start rules inside each band

### Start rule inside band

- `absolute`: the band share starts at the lower edge of the band
- `equal_probabilities`: constant yearly start probability across the band
- `uniform_start_age`: yearly start probabilities tuned so realized start age is uniform across the band

## Main plots

### Population pyramids

The two pyramid panels compare the active scenario and the comparison scenario for the selected year.

### Total population

This shows how the intervention changes overall population size over time.

### Share age 65+

This tracks how much mass accumulates at older ages.

### Treated-share heatmap

This is the quickest way to verify whether the start rule is behaving as intended.

### Survival curves

This is a cohort-level view, not a demographic projection. In the `sr` branch it mixes precomputed SR survival surfaces. In the `analytic_arm` branch it mixes WPP-based baseline survival with the analytic multipliers.

## Exports

### `population_by_year_age.csv`

One row per scenario, year, sex, and age.

Important fields:
- `population_count`
- `treated_population_count`
- `untreated_population_count`
- `branch`
- `analytic_preset_id`

### `summary.csv`

One row per year.

Important fields:
- `total_population`
- `treated_share`
- `births`
- `deaths`
- `median_age`
- `old_age_share_65_plus`
- `branch`
- `analytic_preset_id`
"""
    path.write_text(text)


def write_validation_doc(path: Path) -> None:
    text = """# USA Validation Scenarios

This stage is designed to validate the corrected intervention mechanics before the full multi-country expansion.

## Paper-style presets

- `no_one`
- `everyone`
- `only_elderly_65plus`
- `50pct_elderly_65plus`
- `30pct_middle_40_64_plus_70pct_elderly_65plus`
- `half_population_adult_band`
- `prescription_bands_absolute`

## Uptake-rule comparison presets

- `prescription_bands_absolute`
- `prescription_bands_equal_probabilities`
- `prescription_bands_uniform_start_age`
- `threshold_age_60_all_eligible`

## Fixed PDF-style age bands

- `20-39`: `35%`
- `40-64`: `65%`
- `65+`: `95%`

## Important interpretation notes

- `eta` reductions are implemented as a slower slope after treatment start, not as a downward jump in accumulated production.
- `Xc` changes are immediate after treatment start.
- The `analytic_arm` branch uses the USA 2019 both-sex hazard-fit preset and launch-year WPP mortality as its untreated baseline.
- `half_population_adult_band` is defined here as `50%` uptake in a single `20+` band.
- `elderly` means `65+`.
- `middle age` means `40-64`.
"""
    path.write_text(text)
