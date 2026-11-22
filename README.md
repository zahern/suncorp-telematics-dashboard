# Telematics dashboard (public, aggregates only)

Two static pages over a Suncorp telematics study area across Queensland:

* `index.html` — a day view: hard-braking and speeding events, the daily
  statistics panel and the hourly profile.
* `routes.html` — the solved rosters: choose a squad size (P = 1..8) on the
  MIP plan or switch to the roving parking-verified plan, and read the
  predicted hottest roads bin by bin as the clock moves, ranked either by
  predicted volume or by how far each road sits above its own 28-bin mean.

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

`data/route_plans_by_squad.json` holds the MIP roster solved separately for
every squad size from P = 1 to P = 8, which is what the squad slider selects
between, and `data/route_plans_roving.json` is the roving plan over the
parking-verified pool. `data/hot_roads_15min.json` holds the predicted per-road
15-minute profiles the "hottest roads" panel ranks — by predicted volume, or
against each road's own 28-bin mean. All three are outputs of the optimisation,
written by the solve, not by this exporter.

## Running it

Any static server works (`python -m http.server`), because the pages fetch
`data/*.json` with relative paths. Opening the files directly with `file://`
will not work: the fetches are blocked.

## Publishing on GitHub Pages

This repository is already laid out to be served by GitHub Pages as it stands:
the pages sit at the repository root, every fetch is relative (`data/*.json`), so
the site works under a project URL (`https://<user>.github.io/<repo>/`), and
`.nojekyll` stops Jekyll from processing the files. There is no build step and
no workflow to add: Pages serves the committed files, and every push to `main`
republishes the site.

1. Create an empty repository on GitHub (no README, no `.gitignore`). Its name
   is the last part of the URL, so `suncorp-telematics-dashboard` gives
   `https://<user>.github.io/suncorp-telematics-dashboard/`; a repository named
   `<user>.github.io` serves at the root instead.
2. Point the existing history at it and push:

       git remote add origin git@github.com:<user>/<repo>.git
       git push -u origin main

   Use the `https://github.com/<user>/<repo>.git` URL instead, and sign in with a
   personal access token (or let Git Credential Manager open a browser) when
   prompted.
3. In the repository, **Settings → Pages → Build and deployment**, set
   *Source* to **Deploy from a branch**, *Branch* to **main** and the folder to
   **/ (root)**, then save. The first build takes a minute; the URL appears at
   the top of the same page, and **Actions** shows each build.

The repository must be public for Pages to serve it on a free account. The
published data is the aggregated-only bundle described above — no vehicle ids,
no exact event times, no trip traces — so a public repository exposes no
per-event record.

## Attribution

Basemap tiles come from OpenStreetMap contributors (ODbL), served by
`tile.openstreetmap.org` under its tile usage policy. The page applies a CSS
filter to darken them; no tiles are re-hosted here.
