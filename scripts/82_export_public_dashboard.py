#!/usr/bin/env python3
"""82_export_public_dashboard.py - build the public, aggregates-only dashboard.

The local dashboard ships ~714 MB of per-event GeoJSON: every hard-braking and
speeding event with its own vehicle id, exact timestamp and coordinates. That is
the right data for the analysis and the wrong data for a public repository.

This writes dashboard_public/, which keeps both pages working on aggregated
data instead:

  * events are collapsed onto a grid (500 m for hard braking, 1.1 km for
    speeding, which is far sparser), one feature per cell, carrying the event
    count, the worst category, per-hour event counts, the peak hour and the
    maximum decel and speed loss. No vehicle ids. No exact times. The per-hour
    counts are what the public time slider sums, so a cell with a 13:00 peak but
    later events stays on the map after 14:00.
  * cells holding a single event are withheld, and the totals published here
    count only the cells that survive, so they are lower than the study's.
  * summary.dates is trimmed to the dates actually shipped, so the date arrows
    cannot navigate to a file that does not exist.
  * the cluster label in the copy of index.html sums the cell counts, so a
    bubble reads "number of events", not "number of cells".
  * routes.html is unchanged apart from the two plan files it needs.

Usage
  python scripts/82_export_public_dashboard.py [source-dir]

The source is the dashboard folder of the study: summary.json plus one
GeoJSON per date. Pass it as the first argument, or leave it out and the
default below is used.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = Path("C:/Users/ahernz/OneDrive - Queensland University of Technology/"
           "Desktop/telematics_data/dashboard")
# when the script runs from the bundle's own scripts/ directory, ROOT is the
# bundle itself rather than the study root
DST = ROOT / "dashboard_public" if (ROOT / "dashboard_public").is_dir() else ROOT
DATES = ["2026-01-03", "2026-02-03", "2026-03-03"]
# hard braking is dense enough for a ~500 m cell; speeding events are far
# sparser, so they get a ~1.1 km cell or nearly every cell would be withheld
CELL_DEG_HB = 0.005
CELL_DEG_SP = 0.010
MIN_COUNT = 2                    # publish no cell that is a single event
HB_RANK = {"Extreme": 3, "Critical-Likely": 2}
SP_RANK = {"Extreme (160+)": 3, "High (140-159)": 2}

README = """# Telematics dashboard (public, aggregates only)

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
"""


def cell_key(lon, lat, deg):
    return (math.floor(lat / deg), math.floor(lon / deg))


def worst(cats, rank):
    best = max(cats, key=lambda c: (rank.get(c, 1), cats[c]))
    return best


def aggregate(features, kind, deg):
    """Collapse event features onto grid cells, keeping aggregates only.

    Returns the FeatureCollection and what it holds: events published, events
    withheld by MIN_COUNT, and the per-category counts of the published cells.
    """
    cells = {}
    for f in features:
        try:
            lon, lat = f["geometry"]["coordinates"][:2]
            p = f["properties"]
        except (KeyError, TypeError, ValueError):
            continue
        k = cell_key(lon, lat, deg)
        c = cells.get(k)
        if c is None:
            c = cells[k] = {"n": 0, "cats": Counter(), "hours": Counter(),
                            "roads": Counter(),
                            "decel": 0.0, "loss": 0.0, "speed": 0.0}
        c["n"] += 1
        if kind == "hb":
            c["cats"][p.get("category") or "Unknown"] += 1
            try:
                c["decel"] = max(c["decel"], float(p.get("peak_decel") or 0.0))
                c["loss"] = max(c["loss"], float(p.get("speed_loss") or 0.0))
            except (TypeError, ValueError):
                pass
            if p.get("hour") is not None:
                c["hours"][int(p["hour"])] += 1
        else:
            c["cats"][p.get("category") or "Unknown"] += 1
            try:
                c["speed"] = max(c["speed"], float(p.get("speed") or 0.0))
            except (TypeError, ValueError):
                pass
            stamp = p.get("timestamp") or p.get("time") or ""
            # stamps look like "2026-01-03 19:24:24" or "19:24:24": take the
            # clock hour, never the first two characters of the year
            clock = stamp.split()[-1] if stamp else ""
            if len(clock) >= 2 and clock[:2].isdigit():
                h = int(clock[:2])
                if 0 <= h <= 23:
                    c["hours"][h] += 1
        if p.get("road"):
            c["roads"][p["road"]] += 1

    # withhold sparse cells: a cell holding one event is that event's position
    # on a known day, which is the record this bundle must not publish
    withheld = sum(c["n"] for c in cells.values() if c["n"] < MIN_COUNT)
    cells = {k: c for k, c in cells.items() if c["n"] >= MIN_COUNT}

    rank = HB_RANK if kind == "hb" else SP_RANK
    feats = []
    published = 0
    kept_cats = Counter()
    kept_hours = Counter()
    for k, c in sorted(cells.items()):
        # publish the CELL centre, never the mean of the member events
        lat = (k[0] + 0.5) * deg
        lon = (k[1] + 0.5) * deg
        published += c["n"]
        kept_cats.update(c["cats"])
        kept_hours.update(c["hours"])
        peak = c["hours"].most_common(1)[0][0] if c["hours"] else 0
        props = {
            "count": c["n"],
            "category": worst(c["cats"], rank),
            "hour": peak,
            "time": f"{peak:02d}:00 (day peak)",
            "road": c["roads"].most_common(1)[0][0] if c["roads"] else "",
            "vehicle_type": "aggregate",
        }
        if kind == "hb":
            # per-hour counts drive the public time slider: it sums the hours at
            # or after the chosen hour instead of trusting a single peak hour
            props["hours"] = [[h, n] for h, n in sorted(c["hours"].items())]
            if sum(n for _, n in props["hours"]) != props["count"]:
                raise SystemExit(f"FATAL: hourly counts do not sum to count in cell {k}")
            props["peak_decel"] = round(c["decel"], 3)
            props["speed_loss"] = round(c["loss"], 1)
            props["confidence"] = "cell max"
        else:
            props["speed"] = round(c["speed"], 1)
            props["timestamp"] = f"{peak:02d}:00 (day peak)"
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                      "properties": props})
    return ({"type": "FeatureCollection", "features": feats},
            {"events": published, "withheld": withheld,
             "categories": dict(kept_cats),
             "hourly": dict(kept_hours)})


PATCHES = [
    # cluster labels: sum the cell counts instead of counting markers
    ("            let count = cluster.getChildCount();\n"
     "            let size = count < 50 ? 'small' : (count < 200 ? 'medium' : 'large');",
     "            let count = cluster.getAllChildMarkers().reduce(function (s, m) {\n"
     "                return s + (m._aggCount || 1); }, 0);\n"
     "            let size = count < 50 ? 'small' : (count < 200 ? 'medium' : 'large');"),
    ("            let count = cluster.getChildCount();\n"
     "            let size = count < 20 ? 'small' : (count < 100 ? 'medium' : 'large');",
     "            let count = cluster.getAllChildMarkers().reduce(function (s, m) {\n"
     "                return s + (m._aggCount || 1); }, 0);\n"
     "            let size = count < 20 ? 'small' : (count < 100 ? 'medium' : 'large');"),
    # carry the cell count onto the marker the cluster sums over
    ("        hbCluster.addLayer(icon);",
     "        icon._aggCount = p.count || 1;\n        hbCluster.addLayer(icon);"),
    ("        speedingCluster.addLayer(icon);",
     "        icon._aggCount = p.count || 1;\n        speedingCluster.addLayer(icon);"),
    # "Extreme Speeding" is a count of events, not of cells
    ("currentSpeedingEvents.length.toLocaleString()",
     "currentSpeedingEvents.reduce(function (s, f) { return s + "
     "(f.properties.count || 1); }, 0).toLocaleString()"),
    # the slider is a lower bound on the hour: the aggregate data resolves whole
    # hours only, so the slider steps by one hour and never sits at 24:00
    ('<input type="range" id="time-slider" min="0" max="24" value="0" step="0.25">',
     '<input type="range" id="time-slider" min="0" max="23" value="0" step="1">'),
    # whole hours only: the slider is an integer, so the page's minute arithmetic
    # in the time display is dead at step=1 and the label is just "HH:00 onwards"
    ("        timeFilterValue = parseFloat(this.value);",
     "        timeFilterValue = parseInt(this.value, 10);"),
    ("    if (timeFilterValue === 0) { display.textContent = 'All day'; }\n"
     "    else {\n"
     "        let h = Math.floor(timeFilterValue);\n"
     "        let m = Math.round((timeFilterValue - h) * 60);\n"
     "        display.textContent = String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ' onwards';\n"
     "    }",
     "    display.textContent = timeFilterValue === 0 ? 'All day'\n"
     "        : hh(timeFilterValue) + ':00 onwards';"),
    # sum the cell's per-hour counts instead of comparing its single peak hour
    ("const SPEED_COLORS = {\n"
     "    'Extreme (160+)': '#ff0000',\n"
     "    'High (140-159)': '#ff6600',\n"
     "    'Elevated (130-139)': '#ffaa00'\n"
     "};",
     "const SPEED_COLORS = {\n"
     "    'Extreme (160+)': '#ff0000',\n"
     "    'High (140-159)': '#ff6600',\n"
     "    'Elevated (130-139)': '#ffaa00'\n"
     "};\n"
     "\n"
     "// events in a cell at or after the slider hour (0 means the whole day)\n"
     "function cellShown(p) {\n"
     "    if (timeFilterValue <= 0) return p.count || 1;\n"
     "    let n = 0;\n"
     "    (p.hours || []).forEach(function (pair) {\n"
     "        if (pair[0] >= timeFilterValue) n += pair[1];\n"
     "    });\n"
     "    return n;\n"
     "}\n"
     "\n"
     "function hh(h) {\n"
     "    return String(Math.round(h)).padStart(2, '0');\n"
     "}"),
    ("        let p = f.properties;\n"
     "        if (timeFilterValue > 0) {\n"
     "            let h = p.hour + p.minute / 60;\n"
     "            if (h < timeFilterValue) return;\n"
     "        }\n"
     "        let cat = document.getElementById('category-filter').value;",
     "        let p = f.properties;\n"
     "        let shown = cellShown(p);\n"
     "        if (!shown) return;\n"
     "        let cat = document.getElementById('category-filter').value;"),
    ("        icon._aggCount = p.count || 1;\n        hbCluster.addLayer(icon);",
     "        icon._aggCount = shown;\n        hbCluster.addLayer(icon);"),
    ("        let popup = '<b>' + p.category + '</b><br>' +\n"
     "            '<div class=\"popup-row\"><span class=\"popup-label\">Time:</span> <span class=\"popup-val\">' + p.time + '</span></div>' +",
     "        let popup = '<b>' + p.category + '</b><br>' +\n"
     "            '<div class=\"popup-row\"><span class=\"popup-label\">Events:</span> <span class=\"popup-val\">' + shown.toLocaleString() + ' of ' + (p.count || 0).toLocaleString() + (timeFilterValue > 0 ? ' after ' + hh(timeFilterValue) + ':00' : ' on this day') + '</span></div>' +\n"
     "            '<div class=\"popup-row\"><span class=\"popup-label\">Peak hour:</span> <span class=\"popup-val\">' + hh(p.hour) + ':00</span></div>' +"),
    ("    if (catFilter !== 'all') {\n"
     "        filtered = currentHBEvents.filter(function(f) { return f.properties.category === catFilter; });\n"
     "    }\n"
     "    if (timeFilterValue > 0) {\n"
     "        filtered = filtered.filter(function(f) {\n"
     "            return (f.properties.hour + f.properties.minute / 60) >= timeFilterValue;\n"
     "        });\n"
     "    }",
     "    if (catFilter !== 'all') {\n"
     "        filtered = currentHBEvents.filter(function(f) { return f.properties.category === catFilter; });\n"
     "    }\n"
     "    if (timeFilterValue > 0) {\n"
     "        filtered = filtered.filter(function(f) { return cellShown(f.properties) > 0; });\n"
     "    }"),
    ("    if (catFilter !== 'all') filtered = filtered.filter(function(f) { return f.properties.category === catFilter; });\n"
     "    if (timeFilterValue > 0) {\n"
     "        filtered = filtered.filter(function(f) {\n"
     "            return (f.properties.hour + f.properties.minute / 60) >= timeFilterValue;\n"
     "        });\n"
     "    }",
     "    if (catFilter !== 'all') filtered = filtered.filter(function(f) { return f.properties.category === catFilter; });\n"
     "    if (timeFilterValue > 0) {\n"
     "        filtered = filtered.filter(function(f) { return cellShown(f.properties) > 0; });\n"
     "    }"),
    ("    let html = '<h3>HB Events (' + filtered.length.toLocaleString() + ')</h3>';",
     "    let shownEvents = filtered.reduce(function (s, f) { return s + cellShown(f.properties); }, 0);\n"
     "    let html = '<h3>HB Events (' + shownEvents.toLocaleString() + ')</h3>';"),
    ("Showing 200 of ' + filtered.length.toLocaleString() + '</div>';",
     "Showing 200 of ' + filtered.length.toLocaleString() + ' cells</div>';"),
    # the panel's totals are sums of published cells, and must say so
    ('<span class="stat-label">HB Events:</span>',
     '<span class="stat-label">HB Events (published cells):</span>'),
    ("    document.getElementById('stats-content').innerHTML = html;\n}",
     "    html += '<div style=\"color:#a0a0b0;font-size:0.7rem;margin-top:8px;\">"
     f"Counts cover published cells only: cells with at least {MIN_COUNT} events.</div>';\n"
     "    document.getElementById('stats-content').innerHTML = html;\n}"),
]


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    if not src.exists():
        raise SystemExit(f"FATAL: dashboard source not found at {src}")
    # rebuild data/ only: anything else in here (a .git directory, say) survives
    if (DST / "data").exists():
        shutil.rmtree(DST / "data")
    (DST / "data").mkdir(parents=True)

    for page in ("index.html", "routes.html"):
        shutil.copy2(src / page, DST / page)
    shutil.copy2(src / "data" / "route_plans.json", DST / "data" / "route_plans.json")
    shutil.copy2(src / "data" / "route_plans_roving.json",
                 DST / "data" / "route_plans_roving.json")
    (DST / ".nojekyll").write_text("", encoding="utf-8", newline="\n")
    (DST / "README.md").write_text(README, encoding="utf-8", newline="\n")

    src_summary = json.loads((src / "data" / "summary.json").read_text(encoding="utf-8"))
    kept = {}
    report = []
    for date in DATES:
        hb_path = src / "data" / f"{date}.json"
        sp_path = src / "data" / f"speeding_{date}.json"
        if not hb_path.exists():
            raise SystemExit(f"FATAL: missing {hb_path}")
        hb = json.loads(hb_path.read_text(encoding="utf-8"))
        hb_cells, hb_stats = aggregate(hb["features"], "hb", CELL_DEG_HB)
        out = json.dumps(hb_cells, separators=(",", ":")).encode()
        (DST / "data" / f"{date}.json").write_bytes(out)

        sp_cells = None
        sp_stats = None
        if sp_path.exists():
            sp = json.loads(sp_path.read_text(encoding="utf-8"))
            sp_cells, sp_stats = aggregate(sp["features"], "sp", CELL_DEG_SP)
            (DST / "data" / f"speeding_{date}.json").write_bytes(
                json.dumps(sp_cells, separators=(",", ":")).encode())
        cnt = src / "data" / f"speeding_counts_{date}.json"
        if cnt.exists():
            shutil.copy2(cnt, DST / "data" / cnt.name)

        day = dict((src_summary.get("daily_summary") or {}).get(date) or {})
        if day:
            # the statistics panel reads these, so they must describe the
            # published cells, not the study's own totals for the day
            day["source_total"] = int(day.get("total", 0))
            day["total"] = hb_stats["events"]
            day["withheld"] = hb_stats["withheld"]
            day["categories"] = hb_stats["categories"]
            # the chart plots this, so it is the published cells' hours
            day["hourly"] = {str(h): n
                             for h, n in sorted(hb_stats["hourly"].items())}
            day.pop("vehicle_types", None)   # source-wide; would not reconcile
            if sp_stats:
                day["speeding_count"] = sp_stats["events"]
                day["speeding_withheld"] = sp_stats["withheld"]
            kept[date] = day
        report.append((date, len(hb["features"]), len(hb_cells["features"]),
                       len(out), len(sp_cells["features"]) if sp_cells else 0,
                       hb_stats, sp_stats))

    summary = {
        "dates": [d for d in DATES if d in kept],
        "daily_summary": kept,
        "has_osm_data": src_summary.get("has_osm_data"),
        "brisbane_bbox": src_summary.get("brisbane_bbox"),
        "center": src_summary.get("center"),
        "aggregation": (f"events collapsed to ~{int(CELL_DEG_HB * 111000)} m cells "
                        f"(hard braking) and ~{int(CELL_DEG_SP * 111000)} m cells "
                        "(speeding); counts, worst category and per-hour counts"),
        "totals_cover": "published cells only: cells holding at least "
                        f"{MIN_COUNT} events",
        "publication": {
            "hb_grid_m": int(CELL_DEG_HB * 111000),
            "speeding_grid_m": int(CELL_DEG_SP * 111000),
            "minimum_count": MIN_COUNT,
            "hb_events_published": sum(r[5]["events"] for r in report),
            "hb_events_withheld": sum(r[5]["withheld"] for r in report),
            "speeding_events_published": sum(r[6]["events"] for r in report if r[6]),
            "speeding_events_withheld": sum(r[6]["withheld"] for r in report if r[6]),
        },
    }
    # every total here is the sum of the published cells' counts
    summary["total_events"] = sum(int(v.get("total", 0)) for v in kept.values())
    cats = Counter()
    for v in kept.values():
        for k, n in (v.get("categories") or {}).items():
            cats[k] += int(n)
    summary["categories"] = dict(cats)
    (DST / "data" / "summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8", newline="\n")

    # patch the copy so labels and stats count events, not cells
    page = DST / "index.html"
    src = page.read_text(encoding="utf-8")
    for old, new in PATCHES:
        n = src.count(old)
        if n != 1:
            raise SystemExit(f"ABORT: HTML pattern occurs {n} times, not 1:\n{old[:80]}")
        src = src.replace(old, new)
    # newline="\n": keep the source page's LF endings instead of CRLF on Windows
    page.write_text(src, encoding="utf-8", newline="\n")

    total = 0
    for date, n_ev, n_cell, size, n_sp, hs, ss in report:
        total += size
        print(f"[82] {date}: {n_ev:6,} events -> {n_cell:5,} cells "
              f"({size / 1024:7.1f} KB), speeding cells {n_sp}")
        print(f"[82] {date}: published {hs['events']:,} hb events, withheld "
              f"{hs['withheld']:,}" + (f"; speeding published {ss['events']:,}, "
                                       f"withheld {ss['withheld']:,}" if ss else ""))
    # .git is inside the output directory now, so it is not part of the bundle
    files = [p for p in DST.rglob("*") if p.is_file() and ".git" not in p.parts]
    du = sum(p.stat().st_size for p in files)
    print(f"[82] dates shipped: {', '.join(summary['dates'])}")
    print(f"[82] total events kept: {summary['total_events']:,}")
    print(f"[82] wrote {DST} ({du / 1048576:.2f} MB across "
          f"{len(files)} files)")


if __name__ == "__main__":
    main()
