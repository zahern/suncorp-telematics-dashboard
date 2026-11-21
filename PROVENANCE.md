# Provenance

Where these files come from, and how to regenerate them.

## Origin

`index.html`, `routes.html` and `data/*.json` are exports from the Suncorp
telematics study (Brisbane), written by `scripts/82_export_public_dashboard.py`.
Nothing here was edited by hand: that script also applies its own changes to
`index.html` — event counts rather than cell counts in the labels, the hourly
slider, the cluster labels, the published-only totals. The authoritative copy of
the script sits beside the analysis at `scripts/82_export_public_dashboard.py` in
the study repository; the copy here matches it.

## Rebuilding

    python scripts/82_export_public_dashboard.py [source-dir]

The source is the study's dashboard directory: `summary.json` plus one GeoJSON
per date. It holds per-event records with vehicle ids and exact timestamps,
which are deliberately not published here, so a clone on its own cannot
rebuild `data/`. With no argument the script falls back to `DEFAULT_SRC` at the
top of the script, which points at that folder in the study.

A run rewrites `data/` and `index.html` in place and regenerates `README.md`.
It clears `data/` only, so `.git` survives a rebuild.

## Publication rule

Cells are ~500 m for hard braking and ~1.1 km for speeding, and any cell holding
fewer than two events is withheld, so no published feature is a single event's
position on a known day. Every total — `data/summary.json`, the statistics panel,
the cluster labels — counts published cells only, so the figures here sit below
the study's own for the same dates; the difference is in `publication` in
`data/summary.json`. The `road` field is shipped empty because no road matching
was applied to the source, so no cell carries a road name.

## Dates

Three dates are shipped (`DATES` in the script) — a quiet, a typical and a busy
day. `README.md` describes what the aggregates contain and credits the basemap.
