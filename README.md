# Telematics dashboard (public, aggregates only)

Two static pages over a Suncorp telematics study area across Queensland:

* `index.html` — a day view: hard-braking and speeding events, the daily
  statistics panel and the hourly profile.
* `routes.html` — the solved four-officer roster, switched between the
  five-site MIP plan and the roving parking-verified plan.

## What the data is

Events are **cell aggregates**, not individual records: each feature is a grid
cell of 0.005° of latitude and longitude for hard braking — about 555 m
north–south and 495 m east–west near Brisbane, a little narrower further south
and wider further north — and 0.010° for speeding, which is much sparser
(about 1.1 km by 1 km). A hard-braking cell carries its event count, the worst
category in it, per-hour counts, the peak hour and the maximum deceleration
(in g); a speeding cell carries its event count, the worst category, the peak
hour and the maximum speed. No vehicle identifiers, no exact event times and
no trip traces are included, and only three representative dates are shipped.
No road names are published: the study's OSM road matching was never run
(`has_osm_data` is false in `data/summary.json`), so there is no road name to
carry.

The cells are not a Brisbane-only dataset: measured over the published cells
they run from 16.5° S to 29.0° S and 139.5° E to 153.5° E — about 1,400 km
north–south and 1,400 km east–west, from Mount Isa and Cairns out to the Gold
Coast and the south-west border country. 3,232 of the 14,259 published cells
(22.7%) sit outside the `brisbane_bbox` in the study's `data/summary.json`
(151.5°–153.6° E, 26.0°–29.5° S), which describes Brisbane alone. They are
genuine regional driving, not coordinate errors: the out-of-area events
cluster on the same regional towns across hundreds of vehicles, and no
consecutive fix implies an impossible speed. The study's own totals count
them, so they stay in these pages, and the map opens fitted to the published
cells of the day — **Reset View** refits after panning, where a fixed Brisbane
view would leave most of the map empty.

## Publication rule

No published cell represents a single event. Cells holding fewer than two
events are withheld, and every total shown here — the statistics panel, the
cluster labels, `data/summary.json` — counts **published cells only**, so it is
lower than the study's own figure for the same day. Each day block in
`data/summary.json` records its source total and what was withheld, and the
`publication` block holds the run totals and the grid sizes.

Across the three dates shipped, 138,979 of 145,720 hard-braking events are
published (95.4%) and 6,741 withheld (4.6%); for speeding, 2,234 of 2,849 are
published (78.4%) and 615 withheld (21.6%). The withheld events are the ones
that sat alone in their cell.

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
