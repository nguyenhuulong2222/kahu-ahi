#!/usr/bin/env python3
"""Step 7 of the Kahu Ahi pipeline: the contiguous United States, state by state.

  docs/data/conus_states_geo.json     the 48 states and DC as simplified polygons (the page draws them, and both the
                                      page and this step decide which state a detection is in from this one file)
  docs/data/conus_states.json         per state: the monthly series per satellite, the coefficients, the errors
                                      (as recorded, one whole-year ratio, monthly factors; all years, before and from
                                      2022), the chain as used, the acceptance decision, and the error when the
                                      national coefficients are used instead of the state's own
  docs/data/conus_states_daily.json   per state: counted detections per day, in the layout of <region>_daily.json

Boundaries: US Census Bureau cartographic boundary file, states, 1:5,000,000, 2023 (public domain),
https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_5m.zip, kept in data/raw/census/. Coordinates are
rounded to 4 decimals (about 10 m) when the page's file is written, and the assignment below reads that written file,
so the browser and this step use exactly the same numbers.

A detection belongs to the state whose polygon contains its position (even-odd ray casting; a point exactly on an
edge follows the arithmetic of the test below, which the page repeats). A detection in no polygon (offshore, or land
the simplified outline cuts off) is counted under "outside" and reported. Nothing is dropped: for every satellite and
month, the states plus "outside" must equal the national series (data/processed/conus/monthly_series.csv), or this
step stops and writes nothing.

Which detections are in the region and which are counted is decided by export.detections(), as for every other
output. The statistics per state come from calibrate.calibrate(), unchanged: same counting, same fit, same tests, same
acceptance rule. A satellite's months are the national ones: a month in which a state has no detection is a recorded
0 for every month the satellite has data for the country.

A state is given a local time zone only when every GeoNames place in it (cities500) has the same zone.

Standard library only. Usage:
  python3 pipeline/states.py --raw data/raw/usa --bbox -125.0 24.4 -66.9 49.5
"""
import argparse
import csv
import hashlib
import io
import json
import math
import struct
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import calibrate
from export import detections, export_daily

CENSUS = "cb_2023_us_state_5m"
CENSUS_URL = f"https://www2.census.gov/geo/tiger/GENZ2023/shp/{CENSUS}.zip"
NOT_CONTIGUOUS = {"AK", "HI", "PR", "VI", "GU", "MP", "AS"}
DECIMALS = 4
BAND = 10          # index bands and cells of 1/BAND degree
SENSORS = {"MODIS_TERRA": "terra", "MODIS_AQUA": "aqua", "VIIRS_SNPP": "snpp", "VIIRS_NOAA20": "noaa20"}


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------- boundaries ----------
def read_census(zip_path, only=None):
    """[{id, fips, name, rings}] for the 48 states and DC from the shapefile inside the Census zip
    (or for the postal codes in `only`, which pipeline/outline.py uses for a region that is one state)."""
    with zipfile.ZipFile(zip_path) as z:
        shp, dbf = z.read(CENSUS + ".shp"), z.read(CENSUS + ".dbf")
    nrec, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
    fields, off = [], 32
    while dbf[off] != 0x0D:
        fields.append((dbf[off:off + 11].split(b"\0")[0].decode(), dbf[off + 16]))
        off += 32
    recs = []
    for i in range(nrec):
        rec, p, row = dbf[hlen + i * rlen: hlen + (i + 1) * rlen], 1, {}
        for name, ln in fields:
            row[name] = rec[p:p + ln].decode("utf-8", "replace").strip()
            p += ln
        recs.append(row)
    out, pos, i = [], 100, 0
    while pos < len(shp):
        clen = struct.unpack(">I", shp[pos + 4:pos + 8])[0] * 2
        body = shp[pos + 8:pos + 8 + clen]
        pos += 8 + clen
        r = recs[i]
        i += 1
        if struct.unpack("<i", body[:4])[0] != 5 or (r["STUSPS"] not in only if only else r["STUSPS"] in NOT_CONTIGUOUS):
            continue
        nparts, npts = struct.unpack("<2i", body[36:44])
        parts = list(struct.unpack(f"<{nparts}i", body[44:44 + 4 * nparts])) + [npts]
        pts = struct.unpack(f"<{2 * npts}d", body[44 + 4 * nparts:44 + 4 * nparts + 16 * npts])
        rings = []
        for k in range(nparts):
            ring, last = [], None
            for j in range(parts[k], parts[k + 1]):
                pt = (round(pts[2 * j], DECIMALS), round(pts[2 * j + 1], DECIMALS))
                if pt != last:
                    ring.append(pt)
                    last = pt
            if len(ring) >= 4:
                rings.append(ring)
        out.append({"id": r["STUSPS"], "fips": r["STATEFP"], "name": r["NAME"], "rings": rings})
    return sorted(out, key=lambda s: s["id"])


def write_geo(states, zip_path, out_path):
    doc = {"source": "US Census Bureau, cartographic boundary file, states, 1:5,000,000, 2023 (public domain)",
           "source_url": CENSUS_URL, "sha256_of_download": sha256_of(zip_path),
           "coordinates": f"longitude, latitude in a flat list per ring, rounded to {DECIMALS} decimals; even-odd rule over all rings of a state",
           "states": []}
    for s in states:
        xs = [p[0] for r in s["rings"] for p in r]
        ys = [p[1] for r in s["rings"] for p in r]
        doc["states"].append({"id": s["id"], "fips": s["fips"], "name": s["name"], "bbox": [min(xs), min(ys), max(xs), max(ys)],
                              "rings": [[v for p in r for v in p] for r in s["rings"]]})
    out_path.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    return doc


class Locator:
    """Which state a point is in, from the page's geometry file. Exact: cells no edge touches are settled by their
    centre; every other point is tested against the edges that cross its latitude."""

    def __init__(self, geo):
        self.ids = [s["id"] for s in geo["states"]]
        self.bands = [defaultdict(list) for _ in self.ids]     # state -> latitude band -> edges
        self.edge_cells = defaultdict(set)                      # (gy, gx) -> states with an edge in the cell
        for si, s in enumerate(geo["states"]):
            for flat in s["rings"]:
                n = len(flat) // 2
                for a in range(n):
                    b = (a + 1) % n
                    x1, y1, x2, y2 = flat[2 * a], flat[2 * a + 1], flat[2 * b], flat[2 * b + 1]
                    for gy in range(math.floor(min(y1, y2) * BAND), math.floor(max(y1, y2) * BAND) + 1):
                        self.bands[si][gy].append((x1, y1, x2, y2))
                        for gx in range(math.floor(min(x1, x2) * BAND), math.floor(max(x1, x2) * BAND) + 1):
                            self.edge_cells[(gy, gx)].add(si)
        self.centre = {}                                        # (gy, gx) -> state at the cell centre
        for si in range(len(self.ids)):
            for gy, edges in self.bands[si].items():
                y = (gy + .5) / BAND
                xs = sorted((x2 - x1) * (y - y1) / (y2 - y1) + x1 for x1, y1, x2, y2 in edges if (y1 > y) != (y2 > y))
                for k in range(0, len(xs) - 1, 2):
                    for gx in range(math.ceil(xs[k] * BAND - .5), math.floor(xs[k + 1] * BAND - .5) + 1):
                        if xs[k] < (gx + .5) / BAND < xs[k + 1]:
                            self.centre.setdefault((gy, gx), si)
        self.multi = 0

    def inside(self, si, lon, lat):
        hit = False
        for x1, y1, x2, y2 in self.bands[si].get(math.floor(lat * BAND), ()):
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                hit = not hit
        return hit

    def find(self, lat, lon):
        cell = (math.floor(lat * BAND), math.floor(lon * BAND))
        cands = self.edge_cells.get(cell)
        if not cands:
            return self.centre.get(cell)
        found = None
        for si in sorted(cands):
            if self.inside(si, lon, lat):
                if found is None:
                    found = si
                else:
                    self.multi += 1
        return found


# ---------- time zones ----------
def zones(geonames_dir):
    """USPS code -> Counter of IANA zones over the state's GeoNames places."""
    out = defaultdict(Counter)
    path = geonames_dir / "cities500.zip"
    if not path.exists():
        return out
    with zipfile.ZipFile(path) as z:
        for line in io.TextIOWrapper(z.open("cities500.txt"), encoding="utf-8"):
            c = line.rstrip("\n").split("\t")
            if c[8] == "US" and c[17]:
                out[c[10]][c[17]] += 1
    return out


# ---------- per-state statistics ----------
def national_spans(conus_dir):
    """(sensor, quality) -> (first date, last date) in the national daily counts."""
    spans = {}
    with open(conus_dir / "daily_counts.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            k = (r["sensor"], r["quality"])
            a, b = spans.get(k, (r["date"], r["date"]))
            spans[k] = (min(a, r["date"]), max(b, r["date"]))
    return spans


def write_daily(path, counts, spans):
    """A state's daily_counts.csv in the columns calibrate.py and export.py read. A zero row on the first and last
    national date of each satellite and quality makes the state's months the national ones."""
    rows = dict(counts)
    for (sensor, quality), (first, last) in spans.items():
        for d in (first, last):
            rows.setdefault((d, sensor, quality), [0, 0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "sensor", "quality", "n_all", "n_veg_conf"])
        for (d, sensor, quality), (n_all, n_counted) in sorted(rows.items()):
            w.writerow([d, sensor, quality, n_all, n_counted])


def number(v):
    if v == "":
        return None
    f = float(v)
    return int(f) if f.is_integer() and "." not in v else f


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", type=Path, default=Path("data/raw/usa"))
    ap.add_argument("--bbox", type=float, nargs=4, default=[-125.0, 24.4, -66.9, 49.5], metavar=("W", "S", "E", "N"))
    ap.add_argument("--processed", type=Path, default=Path("data/processed/conus"))
    ap.add_argument("--census", type=Path, default=Path("data/raw/census") / (CENSUS + ".zip"))
    ap.add_argument("--geonames", type=Path, default=Path("data/raw/geonames"))
    ap.add_argument("--out", type=Path, default=Path("docs/data"))
    ap.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    args = ap.parse_args()
    if not args.census.exists():
        raise SystemExit(f"Missing {args.census}. Download it from {CENSUS_URL}")

    states = read_census(args.census)
    geo_path = args.out / "conus_states_geo.json"
    geo_before = geo_path.read_bytes() if geo_path.exists() else None
    write_geo(states, args.census, geo_path)
    geo = json.loads(geo_path.read_text(encoding="utf-8"))          # the numbers the page will read
    loc = Locator(geo)
    ids = loc.ids

    # assign every detection
    daily = [defaultdict(lambda: [0, 0]) for _ in ids]
    outside = defaultdict(lambda: [0, 0])
    rows_in = rows_out = 0
    for row, lat, lon, sensor, quality, _, counted in detections(tuple(args.bbox), args.raw):
        si = loc.find(lat, lon)
        cell = (outside if si is None else daily[si])[(row["acq_date"], sensor, quality)]
        cell[0] += 1
        cell[1] += counted
        if si is None:
            rows_out += 1
        else:
            rows_in += 1

    # the states plus "outside" must be the national series, per satellite and month
    national = {}
    with open(args.processed / "monthly_series.csv", newline="", encoding="utf-8") as f:
        nat_rows = list(csv.DictReader(f))
    for r in nat_rows:
        for sensor, col in SENSORS.items():
            if r[col] != "":
                national[(r["month"], sensor)] = int(r[col])
    got = defaultdict(int)
    for d in daily + [outside]:
        for (day, sensor, _), (_, n) in d.items():
            got[(day[:7], sensor)] += n
    problems = [f"{m} {s}: states + outside {got.get((m, s), 0)}, national {n}" for (m, s), n in sorted(national.items()) if got.get((m, s), 0) != n]
    problems += [f"{m} {s}: {n} counted but no national value" for (m, s), n in sorted(got.items()) if n and (m, s) not in national]
    if problems:
        if geo_before is None:
            geo_path.unlink()
        else:
            geo_path.write_bytes(geo_before)
        print("STATES DO NOT ADD UP TO THE NATIONAL SERIES. Nothing written.", file=sys.stderr)
        for p in problems[:40]:
            print("  -", p, file=sys.stderr)
        sys.exit(1)

    spans = national_spans(args.processed)
    nat_monthly = calibrate.load_monthly(args.processed / "daily_counts.csv")
    through = max(c["last_day"] for m in nat_monthly.values() for c in m.values())[:7]
    nat_pairs = calibrate.pairs(nat_monthly, "VIIRS_SNPP", "MODIS_AQUA", through)
    tz = zones(args.geonames)
    months = [r["month"] for r in nat_rows]
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metric": calibrate.METRIC,
        "boundaries": {"file": "conus_states_geo.json", "source": geo["source"], "source_url": CENSUS_URL, "sha256_of_download": geo["sha256_of_download"]},
        "assignment": "each detection belongs to the state whose polygon in conus_states_geo.json contains its position",
        "rows": {"in_a_state": rows_in, "outside_every_state": rows_out, "in_two_polygons": loc.multi},
        "check": "for every satellite and month, the states plus `outside` equal data/processed/conus/monthly_series.csv",
        "time_zone_rule": "a state has a local time zone here only when every GeoNames place in it (cities500) has the same zone",
        "months": months,
        "status": [r["status"] for r in nat_rows], "src": [r["harmonized_source"] for r in nat_rows],
        "outside": {col: [sum(n for (day, s, _), (_, n) in outside.items() if s == sensor and day[:7] == m) if (m, sensor) in national else None for m in months]
                    for sensor, col in SENSORS.items()},
        "states": {},
    }
    daily_doc = {"metric": calibrate.METRIC, "columns": ["day", "aqua", "terra", "snpp", "n20"],
                 "checked": "per state, per sensor and month, the days add up to the state's monthly series", "states": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for si, sid in enumerate(ids):
            d = Path(tmp) / sid
            d.mkdir()
            write_daily(d / "daily_counts.csv", daily[si], spans)
            cal = calibrate.calibrate(d)
            with open(d / "monthly_series.csv", newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if [r["month"] for r in rows] != months or [r["status"] for r in rows] != doc["status"] or [r["harmonized_source"] for r in rows] != doc["src"]:
                raise SystemExit(f"{sid}: the state's months or statuses differ from the national ones; nothing written")
            monthly = calibrate.load_monthly(d / "daily_counts.csv")
            st_pairs = calibrate.pairs(monthly, "VIIRS_SNPP", "MODIS_AQUA", through)
            with_nat = calibrate.held_out(nat_pairs, st_pairs)
            g = geo["states"][si]
            z = tz.get(sid, Counter())
            ns = cal["noaa20_to_snpp"]
            doc["states"][sid] = {
                "name": g["name"], "fips": g["fips"], "bbox": g["bbox"],
                "time_zone": next(iter(z)) if len(z) == 1 else None, "time_zones_of_places": dict(z.most_common()),
                "terra": [number(r["terra"]) for r in rows], "aqua": [number(r["aqua"]) for r in rows],
                "snpp": [number(r["snpp"]) for r in rows], "n20": [number(r["noaa20"]) for r in rows],
                "snpp_eq": [number(r["snpp_aqua_equiv"]) for r in rows], "n20_eq": [number(r["noaa20_aqua_equiv"]) for r in rows],
                "aqua_detections_paired_months": sum(p[3] for p in st_pairs), "snpp_detections_paired_months": sum(p[2] for p in st_pairs),
                "calibration_accepted": cal["calibration_accepted"], "acceptance_rule": cal["acceptance_rule"],
                "snpp_to_aqua": cal["snpp_to_aqua"],
                "noaa20_to_snpp": {"paired_months": ns["paired_months"], "leave_one_year_out": {"uncalibrated": ns["leave_one_year_out"]["uncalibrated"]}},
                "as_used": cal["as_used"], "current_month": cal["current_month"],
                "with_national_coefficients": calibrate.period_errors([(y, o, p) for y, _, o, p in with_nat], calibrate.DRIFT_YEAR),
            }
            out_daily = Path(tmp) / "daily"
            out_daily.mkdir(exist_ok=True)
            export_daily(sid, d, out_daily)
            dd = json.loads((out_daily / f"{sid}_daily.json").read_text(encoding="utf-8"))
            daily_doc["states"][sid] = {k: dd[k] for k in ("start", "standard", "nrt") if k in dd}
            doc["data_through"] = cal["data_through"]
    (args.out / "conus_states.json").write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    (args.out / "conus_states_daily.json").write_text(json.dumps(daily_doc, separators=(",", ":")), encoding="utf-8")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest["state_boundaries"] = {
        "source": geo["source"], "source_url": CENSUS_URL, "file": args.census.name, "sha256": geo["sha256_of_download"], "bytes": args.census.stat().st_size,
        "downloaded": datetime.fromtimestamp(args.census.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d") + " (UTC)",
        "used_for": "docs/data/conus_states_geo.json (48 states and DC, coordinates rounded to 4 decimals) and the assignment of detections to states",
        "detections_in_a_state": rows_in, "detections_outside_every_state": rows_out}
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    acc = [s for s, v in doc["states"].items() if v["calibration_accepted"]]
    counted_out = sum(n for (_, _, _), (_, n) in outside.items())
    print(f"{len(ids)} states; {rows_in:,} detections in a state, {rows_out:,} outside every state ({counted_out:,} of them counted), {loc.multi} in two polygons")
    print(f"states + outside equal the national series for every satellite and month ({len(national)} values)")
    print(f"accepted: {len(acc)} of {len(ids)}; refused: {', '.join(s for s in ids if s not in acc)}")
    for name in ("conus_states_geo.json", "conus_states.json", "conus_states_daily.json"):
        print(f"  {name}  {(args.out / name).stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main()
