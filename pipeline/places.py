#!/usr/bin/env python3
"""Step 5 of the Kahu Ahi pipeline: a small list of named places per region, for saying where a detection is.

  docs/data/places/<region>.json   every GeoNames populated place inside the region box (plus a margin, so a
                                   detection near the edge still finds its nearest town), with its admin names

Source: GeoNames (https://www.geonames.org), cities500 extract: places with more than 500 people or seats of
administrative divisions. Licence: Creative Commons Attribution 4.0. The downloads go in data/raw/geonames/:
  cities500.zip  admin1CodesASCII.txt  admin2Codes.txt  countryInfo.txt
from https://download.geonames.org/export/dump/ . Their sha256 and date are recorded in data/manifest.json.

The web app works out the nearest place, the distance and the compass direction in the browser; nothing here
touches the fire counts.

File layout (kept small)
  "admin":  list of "County, State, Country" strings
  "places": [name, local name ("" when the same), lat, lon, population, index into "admin"]
The name is GeoNames' ASCII name; the local name is GeoNames' main name when it is written differently.

Standard library only. Usage:
  python3 pipeline/places.py --id california --bbox -124.5 32.5 -114.0 42.0
"""
import argparse
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MARGIN_DEG = 0.5
SOURCE = "cities500"
FILES = [SOURCE + ".zip", "admin1CodesASCII.txt", "admin2Codes.txt", "countryInfo.txt"]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_names(path, name_col):
    """GeoNames code files: tab-separated, the code first. Lines starting with # are comments."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            c = line.rstrip("\n").split("\t")
            out[c[0]] = c[name_col]
    return out


def build(region_id, bbox, src, out_dir):
    west, south, east, north = bbox
    admin1 = code_names(src / "admin1CodesASCII.txt", 1)   # "US.CA" -> California
    admin2 = code_names(src / "admin2Codes.txt", 1)        # "US.CA.019" -> Fresno County
    country = code_names(src / "countryInfo.txt", 4)       # "US" -> United States
    admins, places = [], []
    with zipfile.ZipFile(src / (SOURCE + ".zip")) as z:
        for line in io.TextIOWrapper(z.open(SOURCE + ".txt"), encoding="utf-8"):
            c = line.rstrip("\n").split("\t")
            lat, lon = float(c[4]), float(c[5])
            if not (west - MARGIN_DEG <= lon <= east + MARGIN_DEG and south - MARGIN_DEG <= lat <= north + MARGIN_DEG):
                continue
            cc, a1, a2 = c[8], c[10], c[11]
            parts = [admin2.get(f"{cc}.{a1}.{a2}"), admin1.get(f"{cc}.{a1}"), country.get(cc)]
            label = ", ".join(p for p in parts if p)
            if label not in admins:
                admins.append(label)
            places.append([c[2], c[1] if c[1] != c[2] else "", round(lat, 4), round(lon, 4), int(c[14] or 0), admins.index(label)])
    places.sort(key=lambda p: (p[0], p[2], p[3]))
    doc = {"source": f"GeoNames {SOURCE}, https://download.geonames.org/export/dump/{SOURCE}.zip",
           "licence": "Creative Commons Attribution 4.0, https://creativecommons.org/licenses/by/4.0/",
           "margin_deg": MARGIN_DEG, "columns": ["name", "local_name", "lat", "lon", "population", "admin"],
           "admin": admins, "places": places}
    target = out_dir / "places"
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{region_id}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(places), path.stat().st_size


def record(manifest_path, src, region_id, n):
    """Note where the gazetteer came from in data/manifest.json."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    g = manifest.setdefault("gazetteer", {})
    g.update({
        "source": "GeoNames", "source_url": "https://download.geonames.org/export/dump/",
        "licence": "Creative Commons Attribution 4.0", "extract": SOURCE,
        "files": [{"file": f, "sha256": sha256_of(src / f), "bytes": (src / f).stat().st_size,
                   "downloaded": datetime.fromtimestamp((src / f).stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")} for f in FILES],
    })
    g.setdefault("places_per_region", {})[region_id] = n
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--id", required=True)
    ap.add_argument("--bbox", type=float, nargs=4, required=True, metavar=("W", "S", "E", "N"))
    ap.add_argument("--geonames", type=Path, default=Path("data/raw/geonames"))
    ap.add_argument("--out", type=Path, default=Path("docs/data"))
    ap.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    args = ap.parse_args()
    missing = [f for f in FILES if not (args.geonames / f).exists()]
    if missing:
        raise SystemExit(f"Missing GeoNames files in {args.geonames}: {missing}. Download them from https://download.geonames.org/export/dump/")
    n, size = build(args.id, tuple(args.bbox), args.geonames, args.out)
    record(args.manifest, args.geonames, args.id, n)
    print(f"{args.id}: {n:,} named places, {size / 1e3:.1f} kB -> {args.out / 'places' / (args.id + '.json')}")


if __name__ == "__main__":
    main()
