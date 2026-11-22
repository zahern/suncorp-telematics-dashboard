# Provenance

Where these files come from, and how to regenerate them.

## Origin

`index.html`, `routes.html` and `data/*.json` are exports from the Suncorp
telematics study (Queensland), written by `scripts/82_export_public_dashboard.py`.
Nothing here was edited by hand: that script also applies its own changes to
`index.html` — event counts rather than cell counts in the labels, the hourly
slider, the cluster labels, the published-only totals, the map view fitted to
the published cells — and generates `README.md` from a constant it carries.
`routes.html` is copied through as written: its squad-size selector reads
`data/route_plans_by_squad.json` (no re-solve in the browser) and its hottest
roads panel reads `data/hot_roads_15min.json`, ranking it either by predicted
volume or by each road's deviation from its own 28-bin mean.
The authoritative copy of the script sits beside the analysis at
`scripts/82_export_public_dashboard.py` in the study repository; the copy here
matches it.

## Rebuilding

    python scripts/82_export_public_dashboard.py [source-dir]

**A clone of this repository cannot rebuild `data/` by itself.** The script is
the build; the inputs are the study's own dashboard directory, which is not
published because it holds per-event records with vehicle ids and exact
timestamps. A rebuilder needs that folder, containing:

* `data/<date>.json` for every date in `DATES` at the top of the script — the
  day's hard-braking events, one GeoJSON feature per event. Missing any of them
  stops the run rather than shipping a partial day.
* `data/speeding_<date>.json` — the same for speeding. Optional: a date without
  one still ships, just without speeding for that day.
* `data/summary.json` — the per-date blocks the script rewrites into published
  counts. Required.
* `data/route_plans_roving.json` — the roving plan, copied through unchanged
  for `routes.html`.
* `data/route_plans_by_squad.json`, `data/hot_roads_15min.json` — copied through
  unchanged. They are written in the study repository by
  `scripts/83_dashboard_squad_plans.py` (the MIP roster solved separately for
  every squad size P = 1..8, from
  `manuscript/results/dashboard_squad_sweep/`) and
  `scripts/81_dashboard_hot_roads.py` (each road's predicted 28-bin profile
  from `results/game_day_pred_15min.parquet`). Neither is re-solved by the
exporter; it only carries them.
* `index.html`, `routes.html` — copied, then `index.html` is patched.

If `DATES` and the source's dates disagree, the script fails on the missing
date; it does not skip it. With no argument the script falls back to
`DEFAULT_SRC` at the top of the script, which points at that folder on the
study machine.

A run rewrites `data/`, `index.html` and `README.md` in place. It clears
`data/` only, so `.git` survives a rebuild. Unchanged inputs produce
byte-identical output.

## Publication rule

Cells are 0.005° of latitude and longitude for hard braking — about 555 m
north–south and 495 m east–west near Brisbane, a little narrower further south
and wider further north — and 0.010° for speeding, about 1.1 km by 1 km. Any
cell holding fewer than two events is withheld, so no published feature is a
single event's position on a known day. Every total — `data/summary.json`, the
statistics panel, the cluster labels — counts published cells only, so the
figures here sit below the study's own for the same dates; each day block
records its source total and withheld count, and `publication` holds the run
totals. Cells carry no road name: the study's OSM road matching was never run
(`has_osm_data` is false), so no cell has one and the field is not written at
all.

## Dates

Three dates are shipped (`DATES` in the script) — a quiet, a typical and a busy
day. `README.md` describes what the aggregates contain and credits the basemap.
