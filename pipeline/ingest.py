#!/usr/bin/env python3
"""Step 1 of the Kahu Ahi pipeline: read FIRMS archive downloads and count detections per day.

Reads every .csv (or .zip of .csv) in the input folder, works out which sensor each
file holds from its own `satellite` / `instrument` columns, keeps detections inside the
region bounding box, and writes:

  daily_counts.csv   one row per (date, sensor, quality)
  schema_report.json what each input file actually contained

Nothing is assumed about the files beyond the column names NASA FIRMS documents; anything
unexpected is written to the schema report instead of being guessed at.

Standard library only. Usage:
  python3 pipeline/ingest.py --raw data/raw --out data/processed
"""
import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# California calibration region (README "Regions").
DEFAULT_BBOX = (-124.5, 32.5, -114.0, 42.0)  # west, south, east, north
CELL_DEG = 0.1  # grid size for grid_day_count

# How FIRMS files name each satellite (the `satellite` column), mapped to one code per sensor.
# The `instrument` column is not used: S-NPP archive files put "SNPP" there instead of "VIIRS".
SATELLITE_CODES = {
    "TERRA": "MODIS_TERRA", "T": "MODIS_TERRA",
    "AQUA": "MODIS_AQUA", "A": "MODIS_AQUA",
    "SNPP": "VIIRS_SNPP", "N": "VIIRS_SNPP", "NPP": "VIIRS_SNPP",
    "N20": "VIIRS_NOAA20", "NOAA-20": "VIIRS_NOAA20", "J1": "VIIRS_NOAA20",
    "N21": "VIIRS_NOAA21", "NOAA-21": "VIIRS_NOAA21", "J2": "VIIRS_NOAA21",
}

AQUA_FIRST_DATE = "2002-07-04"  # FIRMS archive page: "MODIS Aqua: July 04 2002 - present"


def sensor_code(satellite):
    return SATELLITE_CODES.get(satellite.strip().upper())


def quality_from_name(name):
    """FIRMS archive zips hold fire_archive_* (standard) and fire_nrt_* (near-real-time) files."""
    lower = name.lower()
    if "nrt" in lower:
        return "nrt"
    if "archive" in lower:
        return "standard"
    return "unknown"


def is_low_confidence(value):
    """MODIS confidence is 0-100; VIIRS is l / n / h (FIRMS attribute tables)."""
    v = value.strip().lower()
    if v in ("l", "low"):
        return True
    if v in ("n", "nominal", "h", "high", ""):
        return False
    try:
        return float(v) < 30
    except ValueError:
        return False


def iter_csv_members(path):
    """Yield (member name, text stream) for a .csv file or every .csv inside a .zip."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.filename.lower().endswith(".csv"):
                    with zf.open(info) as raw:
                        yield f"{path.name}:{info.filename}", io.TextIOWrapper(raw, encoding="utf-8", newline="")
    else:
        with open(path, encoding="utf-8", newline="") as f:
            yield path.name, f


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest(raw_dir, out_dir, bbox):
    west, south, east, north = bbox
    # (date, sensor, quality) -> counters
    n_all = Counter()
    n_veg = Counter()
    n_veg_conf = Counter()
    cells = defaultdict(set)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "bbox": {"west": west, "south": south, "east": east, "north": north},
              "cell_deg": CELL_DEG, "files": [], "problems": []}

    paths = sorted(p for p in raw_dir.iterdir() if p.suffix.lower() in (".csv", ".zip"))
    if not paths:
        sys.exit(f"No .csv or .zip files found in {raw_dir}")

    for path in paths:
        digest = sha256_of(path)
        for name, stream in iter_csv_members(path):
            reader = csv.DictReader(stream)
            cols = reader.fieldnames or []
            entry = {"file": name, "sha256_of_download": digest, "columns": cols,
                     "quality": quality_from_name(name), "rows": 0, "rows_in_bbox": 0,
                     "rows_skipped": 0, "satellite_values": Counter(), "instrument_values": Counter(),
                     "type_values": Counter(), "confidence_values": Counter(),
                     "version_values": Counter(), "date_min": None, "date_max": None}
            missing = [c for c in ("latitude", "longitude", "acq_date", "satellite", "instrument") if c not in cols]
            if missing:
                report["problems"].append(f"{name}: missing columns {missing}; file not counted")
                report["files"].append(entry)
                continue
            has_type = "type" in cols
            has_conf = "confidence" in cols
            for row in reader:
                entry["rows"] += 1
                try:
                    lat = float(row["latitude"])
                    lon = float(row["longitude"])
                except ValueError:
                    entry["rows_skipped"] += 1
                    continue
                date = row["acq_date"].strip()
                entry["satellite_values"][row["satellite"]] += 1
                entry["instrument_values"][row["instrument"]] += 1
                if "version" in cols:
                    entry["version_values"][row["version"]] += 1
                if has_type:
                    entry["type_values"][row["type"]] += 1
                if has_conf:
                    conf = row["confidence"].strip()
                    # Keep the report small: letters as-is, numbers by band.
                    key = conf if not conf.replace(".", "").isdigit() else ("<30" if float(conf) < 30 else ">=30")
                    entry["confidence_values"][key] += 1
                if entry["date_min"] is None or date < entry["date_min"]:
                    entry["date_min"] = date
                if entry["date_max"] is None or date > entry["date_max"]:
                    entry["date_max"] = date

                sensor = sensor_code(row["satellite"])
                if sensor is None:
                    entry["rows_skipped"] += 1
                    continue
                if not (west <= lon <= east and south <= lat <= north):
                    continue
                entry["rows_in_bbox"] += 1
                key = (date, sensor, entry["quality"])
                n_all[key] += 1
                # type 0 = presumed vegetation fire. Files without `type` (NRT) cannot be classified.
                if has_type and row["type"].strip() not in ("0", ""):
                    continue
                n_veg[key] += 1
                if has_conf and is_low_confidence(row["confidence"]):
                    continue
                n_veg_conf[key] += 1
                cells[key].add((int((lat + 90) / CELL_DEG), int((lon + 180) / CELL_DEG)))

            unknown = [s for s in entry["satellite_values"] if sensor_code(s) is None]
            if unknown:
                report["problems"].append(f"{name}: unrecognised satellite values {unknown}; those rows not counted")
            if not has_type:
                report["problems"].append(f"{name}: no `type` column; volcano/static sources cannot be separated")
            for k in ("satellite_values", "instrument_values", "type_values", "confidence_values", "version_values"):
                entry[k] = dict(entry[k])
            report["files"].append(entry)

    # Guard from the method notes: an Aqua detection before Aqua existed means the satellite split is wrong.
    early_aqua = [k for k in n_all if k[1] == "MODIS_AQUA" and k[0] < AQUA_FIRST_DATE]
    if early_aqua:
        report["problems"].append(f"{len(early_aqua)} day(s) of MODIS_AQUA before {AQUA_FIRST_DATE}: satellite split is wrong")

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "daily_counts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "sensor", "quality", "n_all", "n_veg", "n_veg_conf", "cells_veg_conf"])
        for key in sorted(n_all):
            w.writerow([*key, n_all[key], n_veg[key], n_veg_conf[key], len(cells[key])])

    dates = [k[0] for k in n_all]
    report["data_through"] = max(dates) if dates else None
    report["sensors"] = {}
    for (date, sensor, quality), n in n_all.items():
        s = report["sensors"].setdefault(f"{sensor}/{quality}", {"rows": 0, "first": date, "last": date})
        s["rows"] += n
        s["first"] = min(s["first"], date)
        s["last"] = max(s["last"], date)
    with open(out_dir / "schema_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--out", type=Path, default=Path("data/processed"))
    ap.add_argument("--bbox", type=float, nargs=4, default=DEFAULT_BBOX, metavar=("W", "S", "E", "N"))
    args = ap.parse_args()
    report = ingest(args.raw, args.out, tuple(args.bbox))
    print(f"data through: {report['data_through']}")
    for name, s in sorted(report["sensors"].items()):
        print(f"  {name:28s} {s['rows']:>10,d} rows  {s['first']} -> {s['last']}")
    for f in report["files"]:
        print(f"  {f['file']}: satellite={f['satellite_values']} type={f['type_values']}")
    if report["problems"]:
        print("PROBLEMS:")
        for p in report["problems"]:
            print("  -", p)
    print(f"wrote {args.out / 'daily_counts.csv'} and {args.out / 'schema_report.json'}")


if __name__ == "__main__":
    main()
