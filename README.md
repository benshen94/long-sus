# Long SUS

`long-sus` is a clone-and-query repository for longevity-intervention population forecasts.

The repo is built around one practical question: given a country, a treatment rule, an intervention target, and a year, what does the projected population look like? The public surface is intentionally small:

- a Python API
- a matching CLI
- a shipped analytic summary catalog for supported built-in scenarios
- on-demand analytic projections for supported countries

The root README is the GitHub landing page. Generated research walkthroughs live in [docs/results_tutorial.md](docs/results_tutorial.md).

## What The Project Contains

The public query layer is designed to answer two common requests:

1. Population sizes over time.
2. Population pyramids for a specific year.

Under the hood, the current repo combines:

- `UN WPP 2024` population, fertility, mortality, sex ratio at birth, and migration inputs
- intervention scenario definitions such as `threshold_age_60_all_eligible`
- an `analytic_arm` that turns fitted hazard parameters into age-by-start-age intervention multipliers

For the public multi-country API, `analytic_arm` is the supported first-class branch. The legacy `sr` branch remains available only for USA on-demand work.

## Modeling Definitions

The public API uses the current internal vocabulary directly.

- `country`: one of `USA`, `World`, `China`, `India`, `Israel`, `Italy`, `Brazil`, `Nigeria`, `South Africa`, `Uganda`
- `scheme_id`: the treatment-start rule, for example `threshold_age_60_all_eligible`
- `target`: which parameter the intervention changes: `eta`, `eta_shift`, `Xc`, or `none`
- `factor`: the intervention strength
- `branch`: `analytic_arm` or `sr`
- `year`: projection year
- `sex`: optional, `male` or `female`
- `threshold_probability`: optional override for threshold schemes, from `0.0` to `1.0`

### Treatment scheme

`scheme_id` controls who starts treatment and when. Examples:

- `no_one`
- `everyone`
- `threshold_age_60_all_eligible`
- `prescription_bands_absolute`
- `prescription_bands_equal_probabilities`
- `prescription_bands_uniform_start_age`

Run `long-sus schemes` or `long_sus.list_supported_schemes()` to inspect the full catalog.

### Factor meaning depends on target

`factor` is not interpreted the same way for every target.

- For `target="eta"`:
  - `factor=1.0` means no intervention effect.
  - Smaller values mean a stronger slowing of the post-treatment `eta` slope.
  - The shipped analytic catalog currently includes `1.00, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70`.
- For `target="Xc"`:
  - `factor=1.0` means no intervention effect.
  - Larger values mean a stronger `Xc` intervention.
  - The supported built-in grid is `1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60`.
- For `target="eta_shift"`:
  - `factor=1.0` means no intervention effect.
  - The model applies an immediate eta shift after treatment starts:

$$
\eta_{{new}} = \eta_{{old}} \cdot \mathrm{{factor}}.
$$

  - The supported built-in grid is `1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60`.
- For `target="none"`:
  - use `scheme_id="no_one"`
  - use `factor=1.0`

The analytic arm is based on a proportional-hazard form

$$
h_0(t) \propto \exp\left[-\frac{X_c}{\epsilon}\left(\beta - \eta t\right)\right].
$$

## Supported Countries And Branches

### Public multi-country path

- `analytic_arm` supports `USA`, `World`, `China`, `India`, `Israel`, `Italy`, `Brazil`, `Nigeria`, `South Africa`, and `Uganda`
- built-in catalog queries use each country's default analytic preset
- custom analytic factors are computed on demand
- the tracked summary catalog bundled in the repo is intentionally compact and currently includes `USA` and `World`
- the same API still supports the wider country set on demand, and you can rebuild the local summary catalog to extend it

### USA-only path

- `sr` is currently supported only for `USA`
- `sr` uses the built-in SR factor grids rather than arbitrary custom factors

## Install

```bash
git clone <private-repo-url>
cd long_sus
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

If the shipped analytic catalog file is missing, the first summary-catalog query will build it locally.

To rebuild or extend the local summary catalog yourself:

```python
from long_sus import build_public_analytic_catalog

build_public_analytic_catalog()
```

## Python Quickstart

```python
from long_sus import ScenarioQuery
from long_sus import get_population_pyramid, get_population_size

query = ScenarioQuery(
    country="World",
    scheme_id="threshold_age_60_all_eligible",
    target="Xc",
    factor=1.2,
    branch="analytic_arm",
    year=2050,
)

pyramid = get_population_pyramid(query)
size = get_population_size(query)
```

### Baseline example

```python
from long_sus import ScenarioQuery, get_population_size

baseline = ScenarioQuery(
    country="USA",
    scheme_id="no_one",
    target="none",
    factor=1.0,
    branch="analytic_arm",
)

baseline_size = get_population_size(baseline)
```

### Query a specific sex in one year

```python
from long_sus import ScenarioQuery, get_population_pyramid

female_pyramid = get_population_pyramid(
    ScenarioQuery(
        country="Italy",
        scheme_id="threshold_age_60_all_eligible",
        target="eta",
        factor=0.8,
        branch="analytic_arm",
        year=2075,
        sex="female",
    )
)
```

### Threshold query with a fixed treated share

This keeps the treated share fixed at the threshold. For example, `0.5` means half of each eligible cohort starts when it first reaches the threshold age, and the untreated half never catch up later.

```python
from long_sus import ScenarioQuery, get_population_size

half_take_up = get_population_size(
    ScenarioQuery(
        country="India",
        scheme_id="threshold_age_60_all_eligible",
        target="eta",
        factor=0.8,
        branch="analytic_arm",
        threshold_age=60,
        threshold_probability=0.5,
    )
)
```

### Rejuvenation example

```python
from long_sus import ScenarioQuery, get_population_size

rejuvenation = get_population_size(
    ScenarioQuery(
        country="China",
        scheme_id="threshold_age_60_all_eligible",
        target="eta_shift",
        factor=1.2,
        branch="analytic_arm",
    )
)
```

### On-demand analytic projection with a custom factor

Use this when your factor is outside the shipped catalog grid.

```python
from long_sus import ScenarioQuery, project_analytic_scenario

population_frame, summary_frame = project_analytic_scenario(
    ScenarioQuery(
        country="Uganda",
        scheme_id="threshold_age_60_all_eligible",
        target="Xc",
        factor=1.15,
        branch="analytic_arm",
    )
)
```

### List supported countries and schemes

```python
from long_sus import list_supported_countries, list_supported_schemes

countries = list_supported_countries()
schemes = list_supported_schemes()
```

## CLI Quickstart

List supported countries:

```bash
long-sus countries
```

List supported schemes:

```bash
long-sus schemes
```

Get a world population pyramid for a threshold-60 `Xc` intervention in 2050:

```bash
long-sus pyramid \
  --country World \
  --scheme-id threshold_age_60_all_eligible \
  --target Xc \
  --factor 1.2 \
  --branch analytic_arm \
  --year 2050
```

Get total-population summaries across all years for a USA baseline:

```bash
long-sus size \
  --country USA \
  --scheme-id no_one \
  --target none \
  --factor 1.0 \
  --branch analytic_arm
```

Project a custom analytic scenario and write both outputs to disk:

```bash
long-sus project \
  --country South\ Africa \
  --scheme-id threshold_age_60_all_eligible \
  --target Xc \
  --factor 1.15 \
  --branch analytic_arm \
  --population-out outputs/custom_population.csv \
  --summary-out outputs/custom_summary.csv
```

## Catalog Queries vs On-Demand Queries

There are two query modes.

### Shipped catalog query

Use a built-in factor grid and let the API read precomputed analytic summary results.

This is the fast path. It is what `get_population_pyramid()` and `get_population_size()` try first when:

- `branch="analytic_arm"`
- the country is supported
- the factor is in the shipped grid for that target

To keep the repository GitHub-sized, the shipped catalog is summary-focused. Population-size queries can be served directly from the tracked catalog. Population-pyramid queries fall back to on-demand projection when a local population catalog has not been built.

### On-demand analytic query

Use this when:

- you want a custom factor such as `1.15`
- the shipped catalog is unavailable locally
- you explicitly want to recompute the scenario

For on-demand analytic work, use `project_analytic_scenario()` directly, or keep using `get_population_pyramid()` / `get_population_size()` and let them fall back automatically.

## Public API Reference

### `list_supported_countries()`

Returns one record per supported country with:

- `slug`
- `country`
- `location_id`
- `cache_slug`
- `default_analytic_preset_id`

### `list_supported_schemes()`

Returns the treatment scheme catalog, including:

- `id`
- `label`
- `uptake_mode`
- `threshold_age`
- `start_rule_within_band`
- `bands`

### `get_population_pyramid(query)`

Returns a pandas DataFrame with one row per `age x sex` for the requested year. If a local population catalog is unavailable, it computes the pyramid on demand.

### `get_population_size(query)`

Returns a pandas DataFrame from the summary table. If `year` is omitted, it returns all available years.

### `project_analytic_scenario(query)`

Returns `(population_frame, summary_frame)` for an on-demand analytic projection.

## Current Boundaries

- The public multi-country path is `analytic_arm`.
- The shipped catalog is currently `demo_variant="medium"`.
- `sr` is not a first-class multi-country public branch.
- The root README is hand-maintained and is not regenerated by the pipeline.
