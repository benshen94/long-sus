# TODO

## Current execution

- [ ] Add a public country registry and route supported-country WPP loading through it.
  Verification: supported countries resolve to location ids, cache slugs, and default analytic preset ids in tests.
- [ ] Build a readable query layer for shipped catalog lookups and on-demand analytic projections.
  Verification: Python API returns pandas DataFrames for country, pyramid, and size queries.
- [ ] Add a small CLI that mirrors the Python query API.
  Verification: `long-sus countries`, `schemes`, `pyramid`, `size`, and `project` work in tests.
- [ ] Move generated research writeups out of the root README and keep the GitHub README hand-maintained.
  Verification: the pipeline writes a docs results file instead of overwriting the root README.
- [ ] Build multi-country analytic catalog support for the initial public country set.
  Verification: catalog build code writes queryable outputs for USA, World, Italy, South Africa, and Uganda.
- [ ] Run targeted tests, review the diff, and finish git/GitHub setup.
  Verification: targeted Python tests pass and the repository exists as a private GitHub repo.
