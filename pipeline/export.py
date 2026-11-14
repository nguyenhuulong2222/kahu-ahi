#!/usr/bin/env python3
"""Step 3 of the Kahu Ahi pipeline: write the files the static web app reads.

  docs/data/<region>.json                  monthly series, coefficients, validation, current month
  docs/data/hotspots/<region>/<year>.csv.gz  the hotspot records behind the numbers, one file per year

Nothing is computed here that steps 1 and 2 did not already compute; this only repackages it.

Standard library only. Usage:
  python3 pipeline/export.py --id california --name "California" --bbox -124.5 32.5 -114.0 42.0
"""
import argparse
import csv
import gzip
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest import (build_static_mask, is_low_confidence, iter_csv_members, mask_cell,  # noqa: E402
                    quality_from_name, sensor_code)

HOTSPOT_COLUMNS = ["acq_date", "acq_time", "latitude", "longitude", "sensor", "quality",
                   "confidence", "frp", "daynight", "type", "counted"]


def number(text):
    if text == "":
        return None
    v = float(text)
    return int(v) if v == int(v) else v


def export_summary(region_id, name, bbox, processed, out_dir):
    cal = json.loads((processed / "calibration.json").read_text(encoding="utf-8"))
    schema = json.loads((processed / "schema_report.json").read_text(encoding="utf-8"))
    months = []
    with open(processed / "monthly_series.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            months.append({"m": r["month"], "terra": number(r["terra"]), "aqua": number(r["aqua"]),
                           "snpp": number(r["snpp"]), "n20": number(r["noaa20"]),
                           "snpp_eq": number(r["snpp_aqua_equiv"]), "n20_eq": number(r["noaa20_aqua_equiv"]),
                           "h": number(r["harmonized"]), "src": r["harmonized_source"], "status": r["status"]})
    summary = {
        "region": {"id": region_id, "name": name,
                   "bbox": {"west": bbox[0], "south": bbox[1], "east": bbox[2], "north": bbox[3]}},
        "generated_at": cal["generated_at"],
        "data_through": cal["data_through"],
        "metric": cal["metric"],
        "calibration_accepted": cal["calibration_accepted"],
        "acceptance_rule": cal["acceptance_rule"],
        "snpp_to_aqua": cal["snpp_to_aqua"],
        "noaa20_to_snpp": cal["noaa20_to_snpp"],
        "current_month": cal["current_month"],
        "static_source_mask": schema["static_source_mask"],
        "sensors": schema["sensors"],
        "months": months,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{region_id}.json").write_text(json.dumps(summary, separators=(",", ":")), encoding="utf-8")
    return summary


def export_hotspots(region_id, bbox, raw_dir, out_dir):
    """Write every detection inside the region, with the flag that says whether it was counted."""
    west, south, east, north = bbox
    paths = sorted(p for p in raw_dir.iterdir() if p.suffix.lower() in (".csv", ".zip"))
    mask = build_static_mask(paths)
    target = out_dir / "hotspots" / region_id
    target.mkdir(parents=True, exist_ok=True)
    buffers = {}
    rows_by_year = {}
    for path in paths:
        for name, stream in iter_csv_members(path):
            reader = csv.DictReader(stream)
            cols = reader.fieldnames or []
            if "latitude" not in cols or "satellite" not in cols:
                continue
            quality = quality_from_name(name)
            has_type = "type" in cols
            for row in reader:
                try:
                    lat, lon = float(row["latitude"]), float(row["longitude"])
                except ValueError:
                    continue
                sensor = sensor_code(row["satellite"])
                if sensor is None or not (west <= lon <= east and south <= lat <= north):
                    continue
                if has_type:
                    veg = row["type"].strip() in ("0", "")
                else:
                    veg = mask_cell(lat, lon) not in mask
                counted = int(veg and not is_low_confidence(row.get("confidence", "")))
                year = row["acq_date"][:4]
                if year not in buffers:
                    buffers[year] = io.StringIO()
                    csv.writer(buffers[year]).writerow(HOTSPOT_COLUMNS)
                    rows_by_year[year] = 0
                csv.writer(buffers[year]).writerow([
                    row["acq_date"], row.get("acq_time", ""), row["latitude"], row["longitude"], sensor, quality,
                    row.get("confidence", ""), row.get("frp", ""), row.get("daynight", ""),
                    row["type"] if has_type else "", counted])
                rows_by_year[year] += 1
    index = {}
    for year, buf in sorted(buffers.items()):
        # Sort by date so a year file reads in order; header stays first.
        lines = buf.getvalue().splitlines()
        body = sorted(lines[1:])
        data = ("\n".join([lines[0]] + body) + "\n").encode("utf-8")
        gz_path = target / f"{year}.csv.gz"
        with open(gz_path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            gz.write(data)
        index[year] = {"rows": rows_by_year[year], "bytes_gz": gz_path.stat().st_size}
    (target / "index.json").write_text(json.dumps({"columns": HOTSPOT_COLUMNS, "years": index}, indent=1), encoding="utf-8")
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--bbox", type=float, nargs=4, required=True, metavar=("W", "S", "E", "N"))
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--processed", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path("docs/data"))
    args = ap.parse_args()
    processed = args.processed or Path("data/processed") / args.id
    summary = export_summary(args.id, args.name, args.bbox, processed, args.out)
    index = export_hotspots(args.id, args.bbox, args.raw, args.out)
    total_rows = sum(v["rows"] for v in index.values())
    total_mb = sum(v["bytes_gz"] for v in index.values()) / 1e6
    print(f"{args.id}: {len(summary['months'])} months, data through {summary['data_through']}, "
          f"calibration accepted: {summary['calibration_accepted']}")
    print(f"hotspots: {total_rows:,} rows in {len(index)} yearly files, {total_mb:.1f} MB compressed")


if __name__ == "__main__":
    main()
