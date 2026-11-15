#!/usr/bin/env python3
"""A region that is one state: its outline, so that only detections inside the state are in the region.

  docs/data/<region>_geo.json   the state's polygons inside the region box, in the layout of conus_states_geo.json

Boundaries: the same US Census Bureau cartographic boundary file as pipeline/states.py (states, 1:5,000,000, 2023,
public domain), in data/raw/census/. Coordinates are rounded to 4 decimals when the file is written, and
ingest.py, export.py and grid.py read the written file (--outline), so every step and the page use the same numbers.

A detection is in the region when it is inside the region box and inside one of the state's polygons (even-odd ray
casting, pipeline/states.py Locator). A detection inside the box but in no polygon (offshore, or land the simplified
outline cuts off) is not in the region; ingest.py counts those rows and writes the number to schema_report.json.
Polygons that lie wholly outside the box are left out of the file and named in it.

Standard library only. Usage:
  python3 pipeline/outline.py --id alaska --state AK --bbox -170.0 51.0 -129.9 71.6
"""
import argparse
import json
from pathlib import Path


def predicate(geo_path):
    """inside(lat, lon) for the outline file written by this step."""
    from states import Locator
    loc = Locator(json.loads(Path(geo_path).read_text(encoding="utf-8")))
    return lambda lat, lon: loc.find(lat, lon) is not None


def main():
    from states import CENSUS, CENSUS_URL, read_census, write_geo
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--id", required=True)
    ap.add_argument("--state", required=True, help="two-letter postal code, as in the Census file")
    ap.add_argument("--bbox", type=float, nargs=4, required=True, metavar=("W", "S", "E", "N"))
    ap.add_argument("--census", type=Path, default=Path("data/raw/census") / (CENSUS + ".zip"))
    ap.add_argument("--out", type=Path, default=Path("docs/data"))
    args = ap.parse_args()
    if not args.census.exists():
        raise SystemExit(f"Missing {args.census}. Download it from {CENSUS_URL}")
    states = read_census(args.census, only={args.state})
    if len(states) != 1:
        raise SystemExit(f"{args.state}: {len(states)} records in the Census file, expected 1")
    west, south, east, north = args.bbox
    state = states[0]
    keep, left_out = [], []
    for ring in state["rings"]:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        (left_out if max(xs) < west or min(xs) > east or max(ys) < south or min(ys) > north else keep).append(ring)
    state["rings"] = keep
    path = args.out / f"{args.id}_geo.json"
    doc = write_geo([state], args.census, path)
    doc["region_box"] = {"west": west, "south": south, "east": east, "north": north}
    doc["polygons_left_out"] = {"count": len(left_out), "why": "wholly outside the region box",
                                "longitude_range": [min(p[0] for r in left_out for p in r), max(p[0] for r in left_out for p in r)] if left_out else None}
    path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    print(f"{args.id}: {state['name']}, {len(keep)} polygons kept, {len(left_out)} wholly outside the box left out"
          + (f" (longitude {doc['polygons_left_out']['longitude_range'][0]} to {doc['polygons_left_out']['longitude_range'][1]})" if left_out else "")
          + f", {path.stat().st_size / 1e3:.1f} kB -> {path}")


if __name__ == "__main__":
    main()
