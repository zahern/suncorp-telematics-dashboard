# Telematics dashboard (public, aggregates only)

Two static pages over a Suncorp telematics study area in Brisbane:

* `index.html` — a day view: hard-braking and speeding events, the daily
  statistics panel and the hourly profile.
* `routes.html` — the solved four-officer roster, switched between the
  five-site MIP plan and the roving parking-verified plan.

## What the data is

Events are **cell aggregates**, not individual records: each feature is a grid
cell — ~500 m across for hard braking, ~1.1 km for speeding, which is much
sparser — carrying a count, the worst category in the cell, per-hour counts,
the peak hour and the maximum deceleration and speed loss. No vehicle
identifiers, no per-vehicle timestamps and no trip traces are included, and
only three representative dates are shipped. The `road` field is empty: no road
matching was applied, so no cell carries a road name.

## Publication rule

No published cell represents a single event. Cells holding fewer than two
events are withheld, and every total shown here — the statistics panel, the
cluster labels, `data/summary.json` — counts **published cells only**, so it is
lower than the study's own figure for the same day. Per-date published and
withheld counts are recorded in `data/summary.json` under `publication`.

The time slider is a lower bound on the hour, not a filter on one peak hour: a
cell stays on the map while it has events at or after the chosen hour, and the
bubble shows the sum of those hours (the day total when the slider is at 0).

`data/route_plans.json` and `data/route_plans_roving.json` are the outputs of
the optimisation, written by the solve.

## Running it

Any static server works (`python -m http.server`), because the pages fetch
`data/*.json` with relative paths. Opening the files directly with `file://`
will not work: the fetches are blocked.

## Attribution

Basemap tiles come from OpenStreetMap contributors (ODbL), served by
`tile.openstreetmap.org` under its tile usage policy. The page applies a CSS
filter to darken them; no tiles are re-hosted here.
