#!/usr/bin/env python3
"""Audit check: how often does a detection card name the wrong county (district)?

The card prints the administrative names of the NEAREST TOWN (docs/data/places/<region>.json), not of the
detection's own position. This samples 2,000 detections per region from docs/data/hotspots/, finds the nearest
town with the same rule as nearTown() in docs/index.html (squared difference in degrees, longitude scaled by
cos(latitude)), and asks whether the detection and that town fall in the same second-level unit, using boundary
files that the project does not use:

  United States   US Census Bureau cartographic boundary file, counties, 1:500,000, 2023 (public domain)
                  https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip
  Vietnam, Laos, Cambodia, Thailand, China
                  geoBoundaries gbOpen ADM2, simplified (CC BY / PDDL, see geoboundaries.org)
                  https://www.geoboundaries.org/api/current/gbOpen/<ISO3>/ADM2/

Put them in audit/ext/ (not committed):  cb_2023_us_county_500k.shp + .dbf,  gb_<ISO3>_ADM2.geojson
Both the detection and the town are located in the same boundary file, so differences in how names are
spelled do not matter. For the United States the name printed on the card is also compared with the
Census name of the county that holds the detection.

Standard library only.  Usage:  python3 audit/county_check.py
"""
import gzip
import json
import math
import random
import struct
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = Path(__file__).resolve().parent / "ext"
OUT = Path(__file__).resolve().parent / "out"
SAMPLE, SEED = 2000, 20261114
ISO = {"Vietnam": "VNM", "Laos": "LAO", "Cambodia": "KHM", "Thailand": "THA", "China": "CHN"}


def read_census():
    """[(bbox, rings, name, state_fips)] from the shapefile, parsed by hand (polygons only)."""
    shp = (EXT / "cb_2023_us_county_500k.shp").read_bytes()
    dbf = (EXT / "cb_2023_us_county_500k.dbf").read_bytes()
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
        if struct.unpack("<i", body[:4])[0] == 5:
            bbox = struct.unpack("<4d", body[4:36])
            nparts, npts = struct.unpack("<2i", body[36:44])
            parts = list(struct.unpack(f"<{nparts}i", body[44:44 + 4 * nparts])) + [npts]
            pts = struct.unpack(f"<{2 * npts}d", body[44 + 4 * nparts:44 + 4 * nparts + 16 * npts])
            rings = [[(pts[2 * j], pts[2 * j + 1]) for j in range(parts[k], parts[k + 1])] for k in range(nparts)]
            out.append({"bbox": bbox, "rings": rings, "name": recs[i]["NAMELSAD"], "state": recs[i]["STATE_NAME"], "id": "US/" + recs[i]["GEOID"], "country": "United States"})
        i += 1
    return out


def read_geoboundaries(country, iso):
    path = EXT / f"gb_{iso}_ADM2.geojson"
    if not path.exists():
        return []
    out = []
    for f in json.loads(path.read_text(encoding="utf-8"))["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        rings = [[(x, y) for x, y, *_ in ring] for poly in polys for ring in poly]
        xs, ys = [p[0] for r in rings for p in r], [p[1] for r in rings for p in r]
        out.append({"bbox": (min(xs), min(ys), max(xs), max(ys)), "rings": rings, "name": f["properties"]["shapeName"], "state": "",
                    "id": iso + "/" + f["properties"]["shapeID"], "country": country})
    return out


def inside(rings, x, y):
    hit = False
    for ring in rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                hit = not hit
            j = i
    return hit


class Units:
    def __init__(self, units):
        self.grid = {}
        for u in units:
            w, s, e, n = u["bbox"]
            for gx in range(math.floor(w), math.floor(e) + 1):
                for gy in range(math.floor(s), math.floor(n) + 1):
                    self.grid.setdefault((gx, gy), []).append(u)

    def find(self, lat, lon):
        for u in self.grid.get((math.floor(lon), math.floor(lat)), []):
            w, s, e, n = u["bbox"]
            if w <= lon <= e and s <= lat <= n and inside(u["rings"], lon, lat):
                return u
        return None


def km(a, b, c, d):
    r = math.radians
    x = math.sin(r(c - a) / 2) ** 2 + math.cos(r(a)) * math.cos(r(c)) * math.sin(r(d - b) / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def sample_rows(region):
    idx = json.loads((ROOT / "docs/data/hotspots" / region / "index.json").read_text(encoding="utf-8"))
    files = idx.get("months") or idx["years"]
    total = sum(v["rows"] for v in files.values())
    want = sorted(random.Random(SEED).sample(range(total), SAMPLE))
    rows, seen, w = [], 0, 0
    for name in sorted(files):
        n = files[name]["rows"]
        if w < len(want) and want[w] < seen + n:
            with gzip.open(ROOT / "docs/data/hotspots" / region / f"{name}.csv.gz", "rt", encoding="utf-8") as f:
                next(f)
                for i, line in enumerate(f):
                    while w < len(want) and want[w] == seen + i:
                        c = line.rstrip("\n").split(",")
                        rows.append((float(c[2]), float(c[3]), c[4], c[0], c[10] == "1"))
                        w += 1
                    if w == len(want) or want[w] >= seen + n:
                        break
        seen += n
    return rows, total


def nearest(places, lat, lon):
    k = math.cos(math.radians(lat))
    best, bd = None, float("inf")
    for p in places:
        dy, dx = p[2] - lat, (p[3] - lon) * k
        d = dx * dx + dy * dy
        if d < bd:
            bd, best = d, p
    return best


def main():
    OUT.mkdir(exist_ok=True)
    units = Units(read_census() + [u for c, iso in ISO.items() for u in read_geoboundaries(c, iso)])
    report = {"sample": SAMPLE, "seed": SEED, "regions": {}}
    for region in ("california", "hawaii", "vietnam", "conus"):
        P = json.loads((ROOT / "docs/data/places" / f"{region}.json").read_text(encoding="utf-8"))
        rows, total = sample_rows(region)
        c, dist, examples, by_km = Counter(), [], [], Counter()
        for lat, lon, sensor, date, counted in rows:
            town = nearest(P["places"], lat, lon)
            label = P["admin"][town[5]]
            d = km(lat, lon, town[2], town[3])
            dist.append(d)
            here, there = units.find(lat, lon), units.find(town[2], town[3])
            c["sampled"] += 1
            if here is None:
                c["point not in any boundary file (sea, or a country without a file)"] += 1
                continue
            c["point located"] += 1
            town_country = label.split(", ")[-1]
            if town_country != here["country"]:
                c["card names a different COUNTRY than the point's"] += 1
            if there is None:
                c["town not in any boundary file"] += 1
                continue
            c["both located"] += 1
            band = "under 5 km" if d < 5 else "5 to 20 km" if d < 20 else "20 km and over"
            by_km[band + " (both located)"] += 1
            if here["id"] != there["id"]:
                c["point and nearest town in different counties/districts"] += 1
                by_km[band + " (different)"] += 1
                if len(examples) < 8:
                    examples.append({"lat": lat, "lon": lon, "date": date, "sensor": sensor, "card_says": f"{town[0]}; {label}", "km_to_town": round(d, 1),
                                     "point_is_in": f"{here['name']}{', ' + here['state'] if here['state'] else ''}, {here['country']}"})
            if here["country"] == "United States":
                c["US points"] += 1
                shown = label.split(", ")
                if len(shown) < 3 or shown[0].lower() != here["name"].lower() or shown[1].lower() != here["state"].lower():
                    c["US points where the printed county or state name differs from the Census county of the point"] += 1
        dist.sort()
        n = c["both located"]
        report["regions"][region] = {
            "detections_in_region": total, "counts": dict(c),
            "different_unit_pct_of_both_located": round(100 * c["point and nearest town in different counties/districts"] / n, 1) if n else None,
            "ci95_pct": [round(100 * (p - 1.96 * math.sqrt(p * (1 - p) / n)), 1), round(100 * (p + 1.96 * math.sqrt(p * (1 - p) / n)), 1)] if n and (p := c["point and nearest town in different counties/districts"] / n) is not None else None,
            "km_to_nearest_town": {"median": round(dist[len(dist) // 2], 1), "p90": round(dist[int(len(dist) * .9)], 1), "max": round(dist[-1], 1)},
            "by_distance": dict(by_km), "examples": examples}
        print(region, json.dumps(report["regions"][region]["counts"]), report["regions"][region]["different_unit_pct_of_both_located"], report["regions"][region]["ci95_pct"], report["regions"][region]["km_to_nearest_town"])
    (OUT / "county_check.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
