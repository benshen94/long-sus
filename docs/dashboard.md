# Dashboard Guide

This file explains what the dashboard controls do and how to interpret the outputs.

## Top-level views

The dashboard has two main tabs:

- `Results`: the projection plots, comparison panels, and exports
- `Methods`: a scrollable explanation of the data inputs, yearly projection loop, intervention biology, rollout rules, and the currently active scenario

## Core controls

### Branch

Choose which intervention engine to use:
- `sr`: precomputed SR surfaces, loaded on demand
- `analytic_arm`: analytic hazard multipliers built from the named preset

### Target

Choose whether the drug changes:
- `eta`: the rate of aging, or damage production, slows after treatment start
- `eta_shift`: an immediate eta shift after treatment start, with `eta_new = eta_old * factor`; smaller factors mean stronger rejuvenation
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
- `rollout`: pick one eligibility age, one launch-year annual start chance, and a calendar-time popularity curve that raises the annual start chance after launch

### Start rule inside band

- `absolute`: the band share starts at the lower edge of the band
- `equal_probabilities`: untreated people inside the band all face the same yearly chance to start
- `uniform_start_age`: yearly start probabilities are tuned so realized start ages are uniform across the band

### Threshold controls

- `threshold age`: the first eligible age
- `probability of taking`: the share that starts at the first eligibility event

This mode is not a catch-up model. If `p = 0.5`, then half of each cohort starts when it first becomes eligible and the untreated remainder stay untreated later.

### Rollout controls

- `eligibility age`: the first age at which someone can start
- `launch-year annual chance`: the annual start chance for eligible untreated people in the launch year
- `long-run annual cap`: the upper annual start chance after popularity saturates
- `rollout curve`: either `linear` or `logistic`
- `years to cap`: used by the linear rollout
- `takeoff year after launch`: used by the logistic rollout

Rollout keeps age-based eligibility, but changes the annual start chance over calendar time. This is the dashboard's "drug becomes more popular over time" mode.

For years since launch $y$:

$$
p_{linear}(y) = p_0 + (p_{max} - p_0)\min\left(\frac{y}{T}, 1\right)
$$

and

$$
L(y) = \frac{1}{1 + \exp[-0.5(y - m)]},
\qquad
p_{logistic}(y) = p_0 + (p_{max} - p_0)\frac{L(y) - L(0)}{1 - L(0)}.
$$

Rollout scenarios are always projected on demand. They are intentionally excluded from the shipped summary catalog so the tracked repo stays compact.

## Main plots

### Population pyramids

The two pyramid panels compare the active scenario and the comparison scenario for the selected year.

### Total population

This shows how the intervention changes overall population size over time.

### Share age 65+

This tracks how much mass accumulates at older ages.

### Treated-share heatmap

This is the quickest way to verify whether the start rule is behaving as intended. It is especially useful for rollout scenarios because it shows both the age eligibility gate and the calendar-time popularity ramp.

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
- `uptake_mode`
- `threshold_age`
- `threshold_probability`
- `rollout_curve`
- `rollout_launch_probability`
- `rollout_max_probability`
- `rollout_ramp_years`
- `rollout_takeoff_years`

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
- `uptake_mode`
- `threshold_age`
- `threshold_probability`
- `rollout_curve`
- `rollout_launch_probability`
- `rollout_max_probability`
- `rollout_ramp_years`
- `rollout_takeoff_years`
