# Bug Log

## 2026-04-12

### Migration mode was hard-wired on in the dashboard

What the bug was:
- The browser runtime already supported projecting with or without WPP migration residuals, but the dashboard UI always built scenarios with migration forced on.

What it caused:
- Users could not inspect the no-migration population path even though the projection code supported it.
- Exported files and on-screen comparisons silently included migration whether or not that matched the intended scenario.

What we changed:
- Added an explicit migration toggle to the main area-selection panel, defaulting to no migration.
- Wired that toggle through scenario state, URL state, exports, and reset behavior.
- Added a short inline explainer so the two migration modes are understandable from the UI.

### Analytic-arm `100+` mortality tail was too flat

What the bug was:
- The analytic-arm logic treated the WPP `100+` open age bin as if mortality stayed flat after age 100.
- That flat-tail assumption existed in the cohort survival builder and in the projection backbone used for population distributions.

What it caused:
- Survival curves for strong `eta` slowdowns could look stuck instead of continuing to fall.
- Population projections could keep too many people alive at extremely old ages because post-100 mortality stopped steepening.
- The dashboard could show inconsistent behavior if the cohort chart used one tail assumption and the population projection used another.

What we changed:
- For open-ended `100+` mortality tails, we now extrapolate hazards after age 100 using the recent log-hazard slope instead of holding mortality flat.
- We applied that change in the analytic cohort builder, the Python projection pipeline, and the browser runtime used by the dashboard.
- We also updated the open-age population spread so the initial `100+` population is distributed using the extrapolated mortality curve.
- We stopped the cohort hazard builder from dropping to zero at extreme ages just because the weighting population had numerically vanished there.
- We added regression tests for post-100 mortality extrapolation.
