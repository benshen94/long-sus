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

## 2026-04-13

### Brazil, China, and Nigeria fits underweighted the ages we care about most

What the bug was:
- The fitter used the default age weighting for Brazil, China, and Nigeria even though the main calibration priority for those countries is the hazard shape between ages 70 and 90.

What it caused:
- Their saved baseline SR fits could spend too much effort matching younger ages and not enough effort matching the late-life window that matters most for the intervention analysis.
- The dashboard analytics tabs then inherited those less targeted fits because they read the saved country presets.

What we changed:
- Added explicit high-age weighting rules for Brazil, China, and Nigeria.
- Concentrated the extra weight on ages 70 to 90 and increased the peak multiplier there.
- Rebuilt the saved baseline-fit params and dashboard analytic preset assets so the analytics tabs use the updated fits.

### Country-specific analytic fits existed but were not enforced as a hard rule

What the bug was:
- The project already had saved 2024 SR-fitter baseline hazard fits for all supported dashboard countries, but the runtime still tolerated implicit defaults and cross-country analytic preset mismatches.

What it caused:
- It was too easy to believe the added countries were still using a generic USA-style fallback.
- API callers could pass an analytic preset from the wrong country without a clear fail-fast check.
- The fitter script had a second hard-coded country list instead of inheriting the supported-country registry directly.

What we changed:
- Made the supported-country registry the source of truth for the baseline-fit builder.
- Added startup validation that every supported country has a matching saved country-specific analytic preset with the correct location id.
- Added query-level validation so analytic projections reject cross-country preset mismatches and always resolve to the country’s fitted preset by default.

### Baseline-fit diagnostics were incomplete across supported countries

What the bug was:
- The saved country baseline-fit JSON already contained all supported countries, but the per-country diagnostic PNGs were only present for a subset of them.

What it caused:
- It was hard to visually inspect fit quality for newly added countries.
- The fitter output looked partially finished even when the numeric fit catalog was complete.

What we changed:
- Made the baseline-fit build script render diagnostic PNGs immediately after writing the fit JSON.
- Added a test that requires every supported country to have a corresponding `*_fit_diagnostic.png`.
- Generated the missing diagnostics for Brazil, China, India, Israel, and Nigeria.

### Mobile dashboard chrome was crowding plots and exports stayed inline

What the bug was:
- On mobile, the Results/Methods switch was not anchored at the top of the page, the exports controls remained an inline panel, and Plotly legends and axis labels were competing for the same space.

What it caused:
- The mobile layout felt cramped before users even reached the charts.
- Export actions took too much vertical space in the main control flow instead of behaving like a secondary action sheet.
- Some chart legends, especially in the SR cohort view, could collide visually with axis labels on smaller screens.

What we changed:
- Moved the Results/Methods switch into a shared top bar and added a mobile exports button that opens the export panel as a modal sheet.
- Added a new configurable population-share panel with a trajectory view and a decade-sampled composition view.
- Reworked mobile Plotly layout settings so legends move to the top, margins expand appropriately, and axis titles keep enough separation from the legend.

### Desktop results hero was wasting vertical space

What the bug was:
- The results hero and year bar were using more vertical space than needed because the hero copy and metric tiles were stretching against each other.

What it caused:
- The first screen of results looked sparse and pushed the actual charts farther down the page.
- The page felt less information-dense than it should, especially on desktop.

What we changed:
- Tightened the hero grid, reduced metric tile padding and height, and stopped the hero metrics from stretching vertically.
- Reduced the year-bar padding and spacing.
- Bumped the dashboard asset version and verified the tighter layout from a fresh browser-rendered screenshot.

### Results hero still consumed too much of the first viewport

What the bug was:
- The desktop results header still spent too much vertical space on a very large multiline question and a separate year-control panel underneath it.

What it caused:
- The first viewport showed too much empty paper and pushed the actual population charts farther down than necessary.
- The dashboard felt less like a working analysis surface and more like a landing page banner.

What we changed:
- Folded the year controls into the hero so the results header uses one compact block instead of two stacked panels.
- Shortened the headline, tightened the hero spacing, and reduced the metric tile footprint.
- Bumped the dashboard asset versions again so the browser loads the updated HTML, CSS, and nested modules together.
