use `python3` not `python`

write extremely easy to consume code, optimize for how easy the code is to read. make the code skimmable. avoid cleverness. use early returns.

whenever you make readmes for me with analysis on my research, and it includes mathematical expressions, always write them in latex, not in code formatting.

for dashboard changes, always treat browser cache as a real failure mode.

whenever we fix a bug, append an entry to `log.md` with:
- what the bug was
- what it caused
- what we changed to fix it

when updating baseline SR fits:
- always regenerate the matching `*_fit_diagnostic.png` files for every country whose fit changed
- do not leave the fit JSON updated without refreshed diagnostic PNGs
- if you add support for a new fitted country, include its diagnostic PNG in the same change

when updating `dashboard/index.html`, `dashboard/app.mjs`, or any nested module imported by `app.mjs`:
- bump the version on the top-level `index.html` asset URLs
- also bump the version on nested module imports such as `./runtime.mjs?...` and `./interventions.mjs?...`
- verify the final dashboard using a fresh cache-busting localhost URL
- if the dashboard appears half-loaded, suspect mixed old/new modules before assuming the app logic is broken
