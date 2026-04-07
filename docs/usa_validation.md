# USA Validation Scenarios

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
