# Long-SUS URL API

This API lets another model query Long-SUS projections without cloning the repository.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
long-sus-api
```

Open:

```text
http://localhost:8000/docs
```

## Endpoints

### `GET /population-pyramid`

Returns one row per year, sex, and age for a single projection year.

Example:

```text
http://localhost:8000/population-pyramid?country=World&scheme_id=threshold_age_60_all_eligible&target=Xc&factor=1.2&branch=analytic_arm&year=2050
```

CSV is the default response format:

```text
http://localhost:8000/population-pyramid?country=World&scheme_id=threshold_age_60_all_eligible&target=Xc&factor=1.2&branch=analytic_arm&year=2050
```

JSON:

```text
http://localhost:8000/population-pyramid?country=World&scheme_id=threshold_age_60_all_eligible&target=Xc&factor=1.2&branch=analytic_arm&year=2050&format=json
```

Important output fields:

- `year`
- `sex`
- `age`
- `population_count`
- `treated_population_count`
- `untreated_population_count`
- `country`
- `scheme_id`
- `target`
- `factor`
- `branch`
- `launch_year`
- `uptake_mode`
- `threshold_age`
- `threshold_probability`

### `GET /population-size`

Returns yearly summary rows. If `year` is omitted, it returns all projection years.

Example:

```text
http://localhost:8000/population-size?country=World&scheme_id=threshold_age_60_all_eligible&target=Xc&factor=1.2&branch=analytic_arm
```

Important output fields:

- `year`
- `total_population`
- `treated_population`
- `treated_share`
- `births`
- `deaths`
- `median_age`
- `old_age_share_65_plus`

### Metadata

```text
GET /countries
GET /schemes
GET /health
```

## Main Query Parameters

- `country`: `USA`, `World`, `China`, `India`, `Israel`, `Italy`, `Brazil`, `Nigeria`, `South Africa`, or `Uganda`
- `scheme_id`: treatment-start rule, such as `threshold_age_60_all_eligible`
- `target`: `eta`, `eta_shift`, `Xc`, or `none`
- `factor`: intervention strength
- `branch`: usually `analytic_arm`
- `year`: projection year, required for `/population-pyramid`
- `sex`: optional for `/population-pyramid`, either `male` or `female`
- `launch_year`: default `2025`
- `threshold_age`: optional override for threshold and rollout scenarios
- `threshold_probability`: optional override for threshold scenarios
- `rollout_curve`: optional rollout override, `linear` or `logistic`
- `rollout_launch_probability`: optional rollout launch-year annual start chance
- `rollout_max_probability`: optional rollout long-run annual start cap
- `rollout_ramp_years`: optional timing control for linear rollout
- `rollout_takeoff_years`: optional timing control for logistic rollout
- `source`: `auto`, `catalog`, or `project`

## Hosting

GitHub Pages can host the static dashboard and static JSON files, but it cannot run dynamic Python projections.

For a live URL API, deploy the included `Dockerfile` to a service that runs containers, such as Render, Fly.io, Railway, or Google Cloud Run. The service should expose port `8000`.

This repo also includes `render.yaml`, so Render can deploy it as a Docker web service and use `/health` as the health check.
