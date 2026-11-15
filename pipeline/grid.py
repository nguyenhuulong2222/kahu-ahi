#!/usr/bin/env python3
"""Step 4 of the Kahu Ahi pipeline: count detections on a 0.1 degree grid for the map.

  docs/data/grid/<region>/<year>.json   per month, every 0.1 degree cell with at least one counted
                                        detection, split by satellite and by data quality
  docs/data/grid/<region>/all_years.json  every cell's total over all complete standard years, per
                                        satellite (the map's default view)
  docs/data/grid/<region>/index.json    the years written, file sizes and the largest cell values

Which detections are inside the region and which are counted comes from export.detections(), the
same rule that sets the `counted` column in the hotspot CSVs. Nothing is re-implemented here.

Before writing, the grid is checked against step 2: summed over all cells, every sensor in every
month must equal monthly_series.csv, and the month-to-date cells must reproduce the month-to-date
numbers in calibration.json, and the all-years cells must add up to monthly_series.csv summed over
the same years. If any check fails the step stops and writes nothing.

All-years file
  A year counts for a satellite when all 12 of its months are complete, standard-quality data under
  calibrate.usable(), the rule calibration uses. Each satellite has its own list of years, stored in
  the file; "cells" is the same flat layout as a month.

Year file layout (kept small: flat arrays, no per-cell objects)
  "origin":  [row, col] of the region's south-west cell; cells are stored relative to it
  "months":  {"8": {"standard": [r, c, aqua, terra, snpp, n20, r, c, ...], "nrt": [...]}, ...}
  "mtd":     the calendar month of the current month, days 1 to D only, same layout (or absent)
A cell with both standard and near-real-time detections in a month appears once in each list.
A cell's south edge is (origin row + r) * 0.1 - 90 and its west edge (origin col + c) * 0.1 - 180.

Standard library only. Usage:
  python3 pipeline/grid.py --id california --bbox -124.5 32.5 -114.0 42.0
"""
import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).parent))
from calibrate import load_monthly, usable  # noqa: E402
from export import detections  # noqa: E402
from ingest import CELL_DEG  # noqa: E402

# Order of the counts in each cell, and the monthly_series.csv column each one must add up to.
SENSORS = ["MODIS_AQUA", "MODIS_TERRA", "VIIRS_SNPP", "VIIRS_NOAA20"]
SERIES_COLUMN = {"MODIS_AQUA": "aqua", "MODIS_TERRA": "terra", "VIIRS_SNPP": "snpp", "VIIRS_NOAA20": "noaa20"}
CELLS_PER_DEG = round(1 / CELL_DEG)


def cell_index(lat, lon):
    """Global (row, col) of the 0.1 degree cell holding a point.

    Multiplying by 10 (not dividing by 0.1) and the tiny nudge keep a point that lies exactly on a
    grid line, such as 32.5, in the cell that starts there. FIRMS gives at most 5 decimals, so no real
    point is within the nudge of a line. The web app bins CSV rows with the same expression.
    """
    return (math.floor((lat + 90) * CELLS_PER_DEG + 1e-6), math.floor((lon + 180) * CELLS_PER_DEG + 1e-6))


def build(bbox, raw_dir, mtd_month, mtd_last_day, outline=None):
    """year -> month -> quality -> (row, col) -> [aqua, terra, snpp, n20]; and the same for month-to-date."""
    grid = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))))
    mtd = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0])))
    for row, lat, lon, sensor, quality, _, counted in detections(bbox, raw_dir, outline):
        if not counted or sensor not in SENSORS:
            continue
        date = row["acq_date"].strip()
        year, month, day = date[:4], str(int(date[5:7])), int(date[8:10])
        i = SENSORS.index(sensor)
        cell = cell_index(lat, lon)
        grid[year][month][quality][cell][i] += 1
        if mtd_month and month == mtd_month and day <= mtd_last_day:
            mtd[year][quality][cell][i] += 1
    return grid, mtd


def check_against_series(grid, series_path):
    """Grid totals per sensor per month must equal monthly_series.csv. Returns a list of mismatches."""
    totals = defaultdict(lambda: [0, 0, 0, 0])
    for year, months in grid.items():
        for month, qualities in months.items():
            for cells in qualities.values():
                for counts in cells.values():
                    t = totals[f"{year}-{int(month):02d}"]
                    for i in range(4):
                        t[i] += counts[i]
    problems = []
    seen = set()
    with open(series_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            seen.add(r["month"])
            for i, sensor in enumerate(SENSORS):
                want = int(r[SERIES_COLUMN[sensor]] or 0)
                got = totals[r["month"]][i] if r["month"] in totals else 0
                if got != want:
                    problems.append(f"{r['month']} {sensor}: grid {got}, monthly_series.csv {want}")
    for month in sorted(set(totals) - seen):
        if any(totals[month]):
            problems.append(f"{month}: grid has detections but monthly_series.csv has no row")
    return problems


def check_against_month_to_date(mtd, current):
    """Summed over all cells, the month-to-date grid must give calibration.json's current_month numbers."""
    def total(year, sensor, qualities):
        return sum(c[SENSORS.index(sensor)] for q in qualities for c in mtd.get(year, {}).get(q, {}).values())
    year = current["month"][:4]
    first, last = (int(y) for y in re.search(r"(\d{4})-(\d{4})", current["baseline"]).groups())
    past = sorted(total(str(y), "MODIS_AQUA", ["standard"]) for y in range(first, last + 1))
    got = {"raw_noaa20": total(year, "VIIRS_NOAA20", ["standard", "nrt"]),
           "aqua_nrt_same_days": total(year, "MODIS_AQUA", ["standard", "nrt"]),
           "baseline_years": len(past), "baseline_median": median(past),
           "baseline_min": past[0], "baseline_max": past[-1]}
    return [f"month-to-date {k}: grid {v}, calibration.json {current[k]}" for k, v in got.items() if v != current[k]]


def complete_years(processed):
    """sensor -> years in which all 12 months are complete standard data (calibrate.usable())."""
    monthly = load_monthly(processed / "daily_counts.csv")
    through = max(c["last_day"] for m in monthly.values() for c in m.values())[:7]
    years = {int(m[:4]) for m in monthly}
    return {s: [y for y in sorted(years) if all(usable(monthly, f"{y}-{m:02d}", s, through) for m in range(1, 13))]
            for s in SENSORS}


def all_years_cells(grid, years):
    """(row, col) -> [aqua, terra, snpp, n20], each satellite summed over its own complete years."""
    cells = defaultdict(lambda: [0, 0, 0, 0])
    for i, sensor in enumerate(SENSORS):
        for year in years[sensor]:
            for qualities in grid.get(str(year), {}).values():
                for q_cells in qualities.values():
                    for cell, counts in q_cells.items():
                        cells[cell][i] += counts[i]
    return cells


def check_all_years(cells, years, series_path):
    """All-years totals per satellite must equal monthly_series.csv summed over the same years."""
    want = [0, 0, 0, 0]
    with open(series_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for i, sensor in enumerate(SENSORS):
                if int(r["month"][:4]) in years[sensor]:
                    want[i] += int(r[SERIES_COLUMN[sensor]] or 0)
    got = [sum(c[i] for c in cells.values()) for i in range(4)]
    return [f"all years {s}: grid {g}, monthly_series.csv {w}" for s, g, w in zip(SENSORS, got, want) if g != w]


def flat(cells, origin):
    out = []
    for (r, c), counts in sorted(cells.items()):
        out.extend([r - origin[0], c - origin[1], *counts])
    return out


def write_all_years(region_id, bbox, cells, years, out_dir):
    origin = cell_index(bbox[1], bbox[0])
    doc = {"cell_deg": CELL_DEG, "origin": list(origin), "columns": ["row", "col", "aqua", "terra", "snpp", "n20"],
           "years": years, "max_cell": {s: max((c[i] for c in cells.values()), default=0) for i, s in enumerate(SENSORS)},
           "cells": flat(cells, origin)}
    path = out_dir / "grid" / region_id / "all_years.json"
    path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    return path.stat().st_size


def write(region_id, bbox, grid, mtd, mtd_info, out_dir):
    target = out_dir / "grid" / region_id
    target.mkdir(parents=True, exist_ok=True)
    origin = cell_index(bbox[1], bbox[0])
    max_cell = [0, 0, 0, 0]
    max_cell_year = [0, 0, 0, 0]   # largest total of one cell over one calendar year: the map's fixed scale for a year
    sizes = {}
    for year in sorted(grid):
        year_cells = defaultdict(lambda: [0, 0, 0, 0])
        for qualities in grid[year].values():
            for cells in qualities.values():
                for cell, counts in cells.items():
                    year_cells[cell] = [a + b for a, b in zip(year_cells[cell], counts)]
        for counts in year_cells.values():
            max_cell_year = [max(a, b) for a, b in zip(max_cell_year, counts)]
        doc = {"year": int(year), "cell_deg": CELL_DEG, "origin": list(origin),
               "columns": ["row", "col", "aqua", "terra", "snpp", "n20"], "months": {}}
        for month in sorted(grid[year], key=int):
            doc["months"][month] = {q: flat(cells, origin) for q, cells in sorted(grid[year][month].items())}
            for cells in grid[year][month].values():
                for counts in cells.values():
                    max_cell = [max(a, b) for a, b in zip(max_cell, counts)]
        if year in mtd:
            doc["mtd"] = {"month": int(mtd_info["month"][5:]), "days": mtd_info["days"],
                          **{q: flat(cells, origin) for q, cells in sorted(mtd[year].items())}}
        path = target / f"{year}.json"
        path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
        sizes[year] = path.stat().st_size
    index = {"cell_deg": CELL_DEG, "origin": list(origin), "sensors": SENSORS,
             "max_cell": dict(zip(SENSORS, max_cell)), "max_cell_year": dict(zip(SENSORS, max_cell_year)), "mtd": mtd_info,
             "years": {y: {"bytes": b} for y, b in sizes.items()},
             "checked": "per sensor per month totals equal monthly_series.csv; month-to-date equals calibration.json"}
    (target / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    return sizes


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--id", required=True)
    ap.add_argument("--bbox", type=float, nargs=4, required=True, metavar=("W", "S", "E", "N"))
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--processed", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path("docs/data"))
    ap.add_argument("--outline", type=Path, default=None, help="outline file from pipeline/outline.py: keep only rows inside it")
    args = ap.parse_args()
    processed = args.processed or Path("data/processed") / args.id

    current = json.loads((processed / "calibration.json").read_text(encoding="utf-8"))["current_month"]
    mtd_info = None
    if current:
        first_day, last_day = (int(d) for d in current["days"].split("-"))
        mtd_info = {"month": current["month"], "days": [first_day, last_day]}
    grid, mtd = build(tuple(args.bbox), args.raw, str(int(current["month"][5:])) if current else None,
                      mtd_info["days"][1] if mtd_info else 0, args.outline)

    problems = check_against_series(grid, processed / "monthly_series.csv")
    if current:
        problems += check_against_month_to_date(mtd, current)
    years = complete_years(processed)
    every = all_years_cells(grid, years)
    problems += check_all_years(every, years, processed / "monthly_series.csv")
    if problems:
        print(f"{args.id}: GRID DOES NOT MATCH THE COUNTED SERIES. Nothing written.", file=sys.stderr)
        for p in problems[:40]:
            print("  -", p, file=sys.stderr)
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more", file=sys.stderr)
        sys.exit(1)

    sizes = write(args.id, tuple(args.bbox), grid, mtd, mtd_info, args.out)
    all_size = write_all_years(args.id, tuple(args.bbox), every, years, args.out)
    cells = sum(len(c) for months in grid.values() for qs in months.values() for c in qs.values())
    print(f"{args.id}: grid matches monthly_series.csv for every sensor and month"
          + (" and the month-to-date numbers" if current else "") + ", and over all complete years")
    for s in SENSORS:
        y = years[s]
        print(f"  all years {s:13s} {len(y):2d} complete years" + (f" ({y[0]}-{y[-1]})" if y else ""))
    print(f"  all_years.json {all_size / 1e3:.1f} kB, {len(every):,} cells")
    print(f"  {cells:,} cell-months in {len(sizes)} yearly files, {sum(sizes.values()) / 1e6:.2f} MB total")
    for year, size in sizes.items():
        print(f"  {year}.json {size / 1e3:8.1f} kB")


if __name__ == "__main__":
    main()
