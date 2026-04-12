# Dashboard Guide

This file explains what the dashboard controls do and how to interpret the outputs.

## Core controls

### Branch

Choose which intervention engine to use:
- `sr`: precomputed SR surfaces, loaded on demand
- `analytic_arm`: analytic hazard multipliers built from the named preset

### Target

Choose whether the drug changes:
- `eta`: the rate of aging, or damage production, slows after treatment start
- `eta_shift`: an immediate eta shift after treatment start, with `eta_new = eta_old * factor`
- `Xc`: robustness increases, which rectangularizes the survival curve

### Factor

In the `sr` branch, this selects the precomputed surface:
- `eta`: `1.00x`, `0.95x`, `0.90x`, `0.85x`, `0.80x`, `0.75x`, `0.70x`
- `Xc`: `1.00x`, `1.10x`, `1.20x`

In the `analytic_arm` branch, the built-in dashboard options now run through `1.60x`.

### Heterogeneity

- `usa_2019`: homogeneous baseline preset
- `usa_2019 + Xc heterogeneity`: same baseline plus Gaussian `Xc` heterogeneity with `std=0.2`

### Analytic preset

The current analytic preset is `usa_period_2019_both_hazard`, the USA 2019 both-sex hazard fit.

The analytic arm uses

$$
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
$$

### Uptake mode

- `threshold`: pick one cutoff age and one fixed treated share `p`
- `banded`: use age bands, each with its own treated share

### Start rule inside band

- `absolute`: the band share starts at the lower edge of the band
- `equal_probabilities`: untreated people inside the band all face the same yearly chance to start
- `uniform_start_age`: yearly start probabilities are tuned so realized start ages are uniform across the band

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
