#!/usr/bin/env python3
"""Independent recomputation of the Kahu Ahi numbers from the raw FIRMS downloads.

Written for the audit from the rules as README.md states them. Imports nothing from pipeline/.
Where the README does not say enough to fix a choice, the choice made here is listed in ASSUMPTIONS
and reported, and the alternatives that matter are tried (see VARIANTS).

Reads   data/raw/*.zip          (California, Hawaii, Vietnam region; the mask pools all nine files)
        data/raw/usa/*.zip      (contiguous United States; its own mask)
Writes  audit/out/<region>_monthly.csv, audit/out/recomputed.json, audit/out/differences.json
Prints  every difference against data/processed/<region>/{monthly_series.csv,calibration.json}
        and docs/data/<region>.json.

Standard library only.  Usage:  python3 audit/recompute.py
"""
import csv
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "out"

# README "Regions": west, south, east, north
SETS = {
    "raw": {"dir": ROOT / "data/raw", "regions": {
        "california": (-124.5, 32.5, -114.0, 42.0),
        "hawaii": (-160.6, 18.7, -154.5, 22.5),
        "vietnam": (102.1, 8.4, 109.5, 23.4)}},
    "usa": {"dir": ROOT / "data/raw/usa", "regions": {
        "conus": (-125.0, 24.4, -66.9, 49.5),
        # Not published regions: the same boxes cut from the US download, to look for double counting
        # and to see whether two downloads of the same place agree.
        "california_from_usa": (-124.5, 32.5, -114.0, 42.0),
        "hawaii_from_usa": (-160.6, 18.7, -154.5, 22.5)}},
}

ASSUMPTIONS = [
    "A point is inside a region when west <= lon <= east and south <= lat <= north (README gives the box, not whether edges count).",
    "Sensor from the file: MODIS rows by the `satellite` column (README says `satellite = A`/`T`; the files say Aqua/Terra, both accepted); "
    "VIIRS S-NPP from the SV-C2 download, NOAA-20 from the J1V-C2 download.",
    "Standard = the fire_archive_* member, near-real-time = the fire_nrt_* member of each zip.",
    "Mask cell = (floor(lat/0.02), floor(lon/0.02)). README gives the cell size and the threshold (3) but not the origin or rounding.",
    "Mask counts every archive row with type 1, 2 or 3, any sensor, any confidence, anywhere in the files of that raw folder "
    "(README: 'built from every file in data/raw/'; it does not say whether low-confidence rows count).",
    "Low confidence: MODIS confidence < 30 (numeric), VIIRS confidence 'l' (README).",
    "Month and day are the UTC acq_date (README does not say; the hotspot CSV keeps acq_date).",
    "Paired training months: February 2012 to July 2026, every month (README: 'every month ... in which both sensors have complete, "
    "standard-quality data (174 months)'). A month with zero detections for a sensor still counts as a month with data.",
    "NOAA-20 against S-NPP: April 2018 to July 2026 (README says 100 months; April 2018 to July 2026 is 100 months).",
    "k(m) falls back to the annual coefficient when the Aqua total of that calendar month in the training set is under 30 (README). "
    "README does not say what happens when the S-NPP total is 0; treated as fallback too.",
    "Leave-one-year-out: for each calendar year, coefficients are fitted on the other years' paired months and the fallback rule is "
    "re-applied inside each fit (README does not say whether the fallback is re-evaluated).",
    "Error = sum |predicted - observed| / sum observed, in percent; bias = (sum predicted - sum observed) / sum observed (README gives the first; "
    "bias is inferred from the table heading).",
    "Month to date: D = last acq_date in the downloads minus one day; Aqua NRT and NOAA-20 NRT counted detections for days 1..D of that month; "
    "baseline = Aqua standard counted detections for the same days of each year 2002..2025 (README).",
]

FIRST, LAST = "2012-02", "2026-07"          # README training window
N20_FIRST = "2018-04"
SPLIT = 2022


def sensor_of(zip_name, row):
    if "M-C61" in zip_name:
        s = (row.get("satellite") or "").strip().lower()
        return "aqua" if s in ("aqua", "a") else "terra" if s in ("terra", "t") else None
    if "SV-C2" in zip_name:
        return "snpp"
    if "J1V-C2" in zip_name:
        return "noaa20"
    return None


def low_conf(sensor, conf):
    if sensor in ("aqua", "terra"):
        try:
            return float(conf) < 30
        except ValueError:
            return False
    return conf.strip().lower() in ("l", "low")


def cell(lat, lon):
    return (math.floor(lat / 0.02), math.floor(lon / 0.02))


def read_set(spec):
    """One pass over a raw folder. Returns per-region tallies and what is needed to apply the mask afterwards."""
    regions = spec["regions"]
    std = {r: defaultdict(lambda: defaultdict(int)) for r in regions}        # region -> (sensor, date) -> {all, veg, vegconf}
    nrt_rows = {r: [] for r in regions}                                      # (sensor, date, cell, lowconf)
    nonveg_all = defaultdict(int)                                            # mask cell -> archive non-veg rows, every year
    nonveg_to2023 = defaultdict(int)                                         # the same, built without 2024 onward
    late = {r: defaultdict(lambda: [0, 0]) for r in regions}                 # region -> cell -> [veg, nonveg] standard rows 2024+
    stdcells = {r: defaultdict(lambda: [0, 0]) for r in regions}             # region -> cell -> [veg, nonveg] all standard rows
    types = {r: defaultdict(int) for r in regions}                           # (sensor, type) counts, standard
    files, edge, dup = [], defaultdict(int), {r: defaultdict(int) for r in regions}
    seen = {r: set() for r in regions}
    last_date = ""
    utc = {r: defaultdict(int) for r in regions}                             # (sensor, hour) of counted standard rows
    for z in sorted(spec["dir"].glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            for member in sorted(zf.namelist()):
                if not member.endswith(".csv"):
                    continue
                quality = "standard" if "archive" in member else "nrt"
                n = 0
                with zf.open(member) as fh:
                    rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8"))
                    has_type = "type" in (rd.fieldnames or [])
                    for row in rd:
                        n += 1
                        lat, lon, date = float(row["latitude"]), float(row["longitude"]), row["acq_date"]
                        if date > last_date:
                            last_date = date
                        sensor = sensor_of(z.name, row)
                        t = row["type"].strip() if has_type else ""
                        c = cell(lat, lon)
                        if quality == "standard" and t in ("1", "2", "3"):
                            nonveg_all[c] += 1
                            if date < "2024":
                                nonveg_to2023[c] += 1
                        for r, (w, s, e, nn) in regions.items():
                            if not (w <= lon <= e and s <= lat <= nn):
                                continue
                            if lon in (w, e) or lat in (s, nn):
                                edge[r] += 1
                            key = (sensor, date, row["acq_time"], row["latitude"], row["longitude"])
                            if key in seen[r]:
                                dup[r][sensor] += 1
                            elif date >= "2026-06":          # exact duplicates are only tracked for recent months, to bound memory
                                seen[r].add(key)
                            lc = low_conf(sensor, row.get("confidence", ""))
                            if quality == "standard":
                                d = std[r][(sensor, date)]
                                d["all"] += 1
                                types[r][(sensor, t)] += 1
                                veg = t == "0"
                                stdcells[r][c][0 if veg else 1] += 1
                                if date >= "2024":
                                    late[r][c][0 if veg else 1] += 1
                                if veg:
                                    d["veg"] += 1
                                    if not lc:
                                        d["vegconf"] += 1
                                        utc[r][(sensor, row["acq_time"][:2])] += 1
                            else:
                                nrt_rows[r].append((sensor, date, c, lc, row["acq_time"]))
                files.append({"zip": z.name, "member": member, "quality": quality, "rows": n, "has_type": has_type})
                print(f"  read {z.name}:{member}  {n:,} rows", flush=True)
    return {"std": std, "nrt": nrt_rows, "nonveg_all": nonveg_all, "nonveg_to2023": nonveg_to2023, "late": late, "stdcells": stdcells,
            "types": types, "files": files, "edge": edge, "dup": dup, "last_date": last_date, "utc": utc}


def monthly_counts(S, region, mask):
    """(sensor, month) -> {'standard': n, 'nrt': n} of counted detections, and the same per day."""
    months = defaultdict(lambda: {"standard": 0, "nrt": 0})
    days = defaultdict(lambda: {"standard": 0, "nrt": 0})
    present = defaultdict(set)                       # (sensor, quality) -> months with any row at all
    for (sensor, date), d in S["std"][region].items():
        months[(sensor, date[:7])]["standard"] += d["vegconf"]
        days[(sensor, date)]["standard"] += d["vegconf"]
        present[(sensor, "standard")].add(date[:7])
    dropped = defaultdict(lambda: [0, 0])            # sensor -> [rows not low confidence, of which masked]
    for sensor, date, c, lc, _ in S["nrt"][region]:
        present[(sensor, "nrt")].add(date[:7])
        if lc:
            continue
        dropped[sensor][0] += 1
        if c in mask:
            dropped[sensor][1] += 1
            continue
        months[(sensor, date[:7])]["nrt"] += 1
        days[(sensor, date)]["nrt"] += 1
    return months, days, present, dropped


def month_range(a, b):
    y, m = int(a[:4]), int(a[5:])
    while f"{y}-{m:02d}" <= b:
        yield f"{y}-{m:02d}"
        m += 1
        if m == 13:
            y, m = y + 1, 1


def fit(pairs, min_den=30):
    num, den = defaultdict(int), defaultdict(int)
    for _, m, n, d in pairs:
        num[m] += n
        den[m] += d
    tot = sum(den.values())
    annual = sum(num.values()) / tot if tot else None
    k = {m: (num[m] / den[m] if den[m] >= min_den and num[m] > 0 else None) for m in range(1, 13)}
    return k, annual, dict(den), dict(num)


def err(rows):
    if not rows:
        return None
    obs = sum(o for o, _ in rows)
    ab = [abs(p - o) for o, p in rows]
    rel = [abs(p - o) / o for o, p in rows if o > 0]
    return {"months": len(rows), "mae": round(sum(ab) / len(rows), 1), "median_abs_error": round(median(ab), 1),
            "abs_error_pct_of_total": round(100 * sum(ab) / obs, 1) if obs else None,
            "bias_pct": round(100 * (sum(p for _, p in rows) - obs) / obs, 1) if obs else None,
            # not in the project's files: the typical month, each month weighted the same
            "median_monthly_pct_error": round(100 * median(rel), 1) if rel else None,
            "months_with_zero_observed": sum(1 for o, _ in rows if o == 0)}


def loyo(pairs, min_den=30):
    held = {"monthly_k": [], "annual_k": [], "uncalibrated": []}
    for year in sorted({p[0] for p in pairs}):
        k, annual, _, _ = fit([p for p in pairs if p[0] != year], min_den)
        for y, m, n, d in pairs:
            if y != year:
                continue
            c = k[m] if k[m] is not None else annual
            if c:
                held["monthly_k"].append((y, m, d, n / c))
            if annual:
                held["annual_k"].append((y, m, d, n / annual))
            held["uncalibrated"].append((y, m, d, n))
    out = {}
    for name, rows in held.items():
        out[name] = {"all_years": err([(o, p) for _, _, o, p in rows]),
                     f"before_{SPLIT}": err([(o, p) for y, _, o, p in rows if y < SPLIT]),
                     f"{SPLIT}_onward": err([(o, p) for y, _, o, p in rows if y >= SPLIT])}
    by_month = {m: err([(o, p) for _, mm, o, p in held["monthly_k"] if mm == m]) for m in range(1, 13)}
    return out, by_month


def analyse(S, region, mask, label="main"):
    months, days, present, dropped = monthly_counts(S, region, mask)
    def val(sensor, month, quality="standard"):
        return months[(sensor, month)][quality]
    pairs = [(int(m[:4]), int(m[5:]), val("snpp", m), val("aqua", m)) for m in month_range(FIRST, LAST)]
    npairs = [(int(m[:4]), int(m[5:]), val("noaa20", m), val("snpp", m)) for m in month_range(N20_FIRST, LAST)]
    k, annual, den, num = fit(pairs)
    L, by_month = loyo(pairs)
    nk, nannual, _, _ = fit(npairs)
    NL, _ = loyo(npairs)
    fwd_k, fwd_a, _, _ = fit([p for p in pairs if p[0] <= 2018])
    def fwd(lo, hi):
        return err([(d, n / (fwd_k[m] if fwd_k[m] is not None else fwd_a)) for y, m, n, d in pairs if lo <= y <= hi])
    # month to date
    last = S["last_date"]
    y, mo, dd = int(last[:4]), int(last[5:7]), int(last[8:]) - 1
    cur = f"{y}-{mo:02d}"
    def mtd(sensor, year, quality):
        return sum(days[(sensor, f"{year}-{mo:02d}-{d:02d}")][quality] for d in range(1, dd + 1))
    base = [mtd("aqua", yy, "standard") for yy in range(2002, y)]
    kc = k[mo] if k[mo] is not None else annual
    raw_n20 = mtd("noaa20", y, "nrt")
    aqua_now = mtd("aqua", y, "nrt")
    # The conversion as it is actually used: NOAA-20 near-real-time / k(m) against Aqua near-real-time, complete NRT months
    used = []
    for m in month_range("2026-08", cur):
        if m == cur:
            continue
        a, n = val("aqua", m, "nrt"), val("noaa20", m, "nrt")
        if (m in present[("aqua", "nrt")]) and (m in present[("noaa20", "nrt")]):
            c = k[int(m[5:])] or annual
            used.append({"month": m, "aqua_nrt": a, "noaa20_nrt": n, "noaa20_on_aqua_scale": round(n / c, 1) if c else None,
                         "pct_diff": round(100 * (n / c - a) / a, 1) if a and c else None})
    return {
        "label": label, "data_through": last,
        "paired_months": len(pairs), "annual_k": round(annual, 3) if annual else None,
        "k_by_month": {m: (round(k[m], 3) if k[m] is not None else None) for m in k},
        "aqua_total_by_calendar_month": {m: den.get(m, 0) for m in range(1, 13)},
        "snpp_total_by_calendar_month": {m: num.get(m, 0) for m in range(1, 13)},
        "months_with_own_k": sum(1 for v in k.values() if v is not None),
        "loyo": L, "loyo_by_calendar_month": by_month,
        "forward_test": {"2019_to_2021": fwd(2019, 2021), "2022_onward": fwd(2022, 2100)},
        "noaa20_snpp": {"paired_months": len(npairs), "annual_k": round(nannual, 3) if nannual else None, "loyo": NL},
        "month_to_date": {"month": cur, "days": f"1-{dd}", "aqua_nrt": aqua_now, "raw_noaa20": raw_n20,
                          "noaa20_on_aqua_scale": round(raw_n20 / kc, 1) if kc else None, "k_used": round(kc, 3) if kc else None,
                          "baseline_years": len(base), "baseline_median": median(base), "baseline_min": min(base), "baseline_max": max(base),
                          "years_below_current": sum(1 for b in base if kc and b < raw_n20 / kc)},
        "conversion_as_used_nrt_months": used,
        "nrt_rows_not_low_confidence": {s: v[0] for s, v in dropped.items()}, "nrt_rows_masked": {s: v[1] for s, v in dropped.items()},
        "_months": months, "_days": days, "_present": present, "_pairs": pairs,
    }


def mask_checks(S, region, mask_all):
    """In-sample check as the README describes it, and the same check out of sample (mask built to 2023, tested on 2024 onward)."""
    veg = nonveg = vm = nm = 0
    for c, (v, n) in S["stdcells"][region].items():
        veg += v
        nonveg += n
        if c in mask_all:
            vm += v
            nm += n
    m23 = {c for c, n in S["nonveg_to2023"].items() if n >= 3}
    veg2 = nonveg2 = vm2 = nm2 = 0
    for c, (v, n) in S["late"][region].items():
        veg2 += v
        nonveg2 += n
        if c in m23:
            vm2 += v
            nm2 += n
    pct = lambda a, b: round(100 * a / b, 1) if b else None
    return {"in_sample": {"veg_rows": veg, "veg_masked": vm, "veg_wrongly_masked_pct": pct(vm, veg), "non_veg_rows": nonveg, "non_veg_masked": nm, "non_veg_caught_pct": pct(nm, nonveg)},
            "out_of_sample_2024_on": {"veg_rows": veg2, "veg_masked": vm2, "veg_wrongly_masked_pct": pct(vm2, veg2), "non_veg_rows": nonveg2, "non_veg_masked": nm2, "non_veg_caught_pct": pct(nm2, nonveg2)},
            "mask_cells_all_years": len(mask_all), "mask_cells_to_2023": len(m23)}


# ---------- comparison with the project's files ----------
def compare(region, A, diffs):
    def note(what, mine, theirs, where):
        if mine is None and theirs is None:
            return
        try:
            size = round(float(mine) - float(theirs), 3)
        except (TypeError, ValueError):
            size = None
        same = mine == theirs or (size is not None and abs(size) < 1e-9)
        if not same:
            diffs.append({"region": region, "what": what, "recomputed": mine, "project": theirs, "difference": size, "file": where})

    proc = ROOT / "data/processed" / region
    # monthly counts
    col = {"terra": "terra", "aqua": "aqua", "snpp": "snpp", "noaa20": "noaa20"}
    n_cells = 0
    with open(proc / "monthly_series.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m = row["month"]
            for s, c in col.items():
                theirs = row[c]
                mine = A["_months"][(s, m)]["standard"] + A["_months"][(s, m)]["nrt"]
                has = m in A["_present"][(s, "standard")] or m in A["_present"][(s, "nrt")]
                if theirs == "":
                    if has and mine:
                        note(f"monthly count {s} {m} (project has no value)", mine, None, "monthly_series.csv")
                    continue
                n_cells += 1
                note(f"monthly count {s} {m}", mine, float(theirs) if "." in theirs else int(theirs), "monthly_series.csv")
    cal = json.loads((proc / "calibration.json").read_text(encoding="utf-8"))
    sa = cal["snpp_to_aqua"]
    note("paired months", A["paired_months"], sa["paired_months"], "calibration.json")
    note("annual k", A["annual_k"], sa["coefficients"]["annual_k"], "calibration.json")
    for m in range(1, 13):
        t = sa["coefficients"]["by_month"][str(m)]
        note(f"k({m})", A["k_by_month"][m], t["k"], "calibration.json")
    for mode in ("monthly_k", "annual_k", "uncalibrated"):
        for period in ("all_years", f"before_{SPLIT}", f"{SPLIT}_onward"):
            mine, theirs = A["loyo"][mode][period], sa["leave_one_year_out"][mode][period]
            for f_ in ("months", "abs_error_pct_of_total", "bias_pct", "mae", "median_abs_error"):
                note(f"S-NPP->Aqua LOYO {mode} {period} {f_}", mine and mine[f_], theirs and theirs[f_], "calibration.json")
    for period in ("2019_to_2021", "2022_onward"):
        for f_ in ("months", "abs_error_pct_of_total", "bias_pct"):
            note(f"forward test {period} {f_}", A["forward_test"][period][f_], sa["forward_test"][period][f_], "calibration.json")
    ns = cal["noaa20_to_snpp"]
    note("NOAA-20/S-NPP paired months", A["noaa20_snpp"]["paired_months"], ns["paired_months"], "calibration.json")
    note("NOAA-20/S-NPP annual k", A["noaa20_snpp"]["annual_k"], ns["coefficients"]["annual_k"], "calibration.json")
    for mode in ("monthly_k", "annual_k", "uncalibrated"):
        for period in ("all_years", f"before_{SPLIT}", f"{SPLIT}_onward"):
            mine, theirs = A["noaa20_snpp"]["loyo"][mode][period], ns["leave_one_year_out"][mode][period]
            for f_ in ("months", "abs_error_pct_of_total", "bias_pct"):
                note(f"NOAA-20->S-NPP LOYO {mode} {period} {f_}", mine and mine[f_], theirs and theirs[f_], "calibration.json")
    cm, mt = cal["current_month"], A["month_to_date"]
    for mine_key, their_key in (("month", "month"), ("days", "days"), ("raw_noaa20", "raw_noaa20"), ("aqua_nrt", "aqua_nrt_same_days"),
                                ("noaa20_on_aqua_scale", "value_aqua_equiv"), ("baseline_years", "baseline_years"), ("baseline_median", "baseline_median"),
                                ("baseline_min", "baseline_min"), ("baseline_max", "baseline_max"), ("years_below_current", "years_below_current")):
        theirs = cm.get(their_key)
        if their_key == "value_aqua_equiv" and theirs is None:
            continue       # a refused region publishes no converted value
        if their_key == "years_below_current" and cm.get("value_aqua_equiv") is None:
            continue
        note(f"month to date {mine_key}", mt[mine_key], theirs, "calibration.json")
    note("calibration accepted", bool(A["loyo"]["monthly_k"]["all_years"]["abs_error_pct_of_total"] <= 50 and A["months_with_own_k"] >= 9), cal["calibration_accepted"], "calibration.json")
    # the page's copy
    web = json.loads((ROOT / "docs/data" / f"{region}.json").read_text(encoding="utf-8"))
    for key in ("annual_k",):
        note("docs annual k", A["annual_k"], web["snpp_to_aqua"]["coefficients"]["annual_k"], f"docs/data/{region}.json")
    for mode in ("monthly_k", "uncalibrated"):
        for period in ("all_years", f"before_{SPLIT}", f"{SPLIT}_onward"):
            note(f"docs LOYO {mode} {period}", A["loyo"][mode][period]["abs_error_pct_of_total"], web["snpp_to_aqua"]["leave_one_year_out"][mode][period]["abs_error_pct_of_total"], f"docs/data/{region}.json")
    note("docs NOAA-20 vs S-NPP 1:1", A["noaa20_snpp"]["loyo"]["uncalibrated"]["all_years"]["abs_error_pct_of_total"], web["noaa20_to_snpp"]["leave_one_year_out"]["uncalibrated"]["all_years"]["abs_error_pct_of_total"], f"docs/data/{region}.json")
    n_web = 0
    for x in web["months"]:
        for s, c in (("terra", "terra"), ("aqua", "aqua"), ("snpp", "snpp"), ("noaa20", "n20")):
            if x[c] is None:
                continue
            n_web += 1
            note(f"docs monthly count {s} {x['m']}", A["_months"][(s, x["m"])]["standard"] + A["_months"][(s, x["m"])]["nrt"], x[c], f"docs/data/{region}.json")
    # the mask check the page quotes
    return n_cells, n_web


def strip(A):
    return {k: v for k, v in A.items() if not k.startswith("_")}


def main():
    OUT.mkdir(exist_ok=True)
    result, diffs, summary = {"assumptions": ASSUMPTIONS, "regions": {}}, [], []
    for set_name, spec in SETS.items():
        print(f"reading {spec['dir']}", flush=True)
        S = read_set(spec)
        mask = {c for c, n in S["nonveg_all"].items() if n >= 3}
        result[f"files_{set_name}"] = S["files"]
        for region in spec["regions"]:
            A = analyse(S, region, mask)
            A["mask"] = mask_checks(S, region, mask)
            A["rows_exactly_on_box_edge"] = S["edge"][region]
            A["exact_duplicate_rows_since_2026_06"] = dict(S["dup"][region])
            A["standard_rows_by_sensor_and_type"] = {f"{s}/{t or 'blank'}": n for (s, t), n in sorted(S["types"][region].items())}
            hours = defaultdict(int)
            tot = defaultdict(int)
            for (s, h), n in S["utc"][region].items():
                tot[s] += n
                if h in ("23", "00"):
                    hours[s] += n
            A["counted_standard_rows_within_an_hour_of_utc_midnight_pct"] = {s: round(100 * hours[s] / tot[s], 1) for s in tot if tot[s]}
            # the variant without the mask, to size its effect on near-real-time months
            B = analyse(S, region, set(), "no mask")
            A["month_to_date_without_mask"] = B["month_to_date"]
            A["nrt_month_totals_with_and_without_mask"] = {
                m: {s: [A["_months"][(s, m)]["nrt"], B["_months"][(s, m)]["nrt"]] for s in ("aqua", "terra", "snpp", "noaa20") if B["_months"][(s, m)]["nrt"]}
                for m in month_range("2026-08", A["month_to_date"]["month"])}
            with open(OUT / f"{region}_monthly.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["month", "sensor", "standard_counted", "nrt_counted"])
                for (s, m), v in sorted(A["_months"].items(), key=lambda kv: (kv[0][1], kv[0][0])):
                    w.writerow([m, s, v["standard"], v["nrt"]])
            if (ROOT / "data/processed" / region).exists():
                before = len(diffs)
                n_cells, n_web = compare(region, A, diffs)
                summary.append(f"{region}: compared {n_cells} monthly values in monthly_series.csv, {n_web} in docs/data/{region}.json, "
                               f"the coefficients, the error tables and the month-to-date figures: {len(diffs) - before} differences")
            A["_keep"] = None
            result["regions"][region] = strip(A)
    (OUT / "recomputed.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    (OUT / "differences.json").write_text(json.dumps(diffs, indent=1, default=str), encoding="utf-8")
    print()
    for line in summary:
        print(line)
    for d in diffs[:80]:
        print("  DIFF", d["region"], "|", d["what"], "| recomputed", d["recomputed"], "| project", d["project"], "| difference", d["difference"], "|", d["file"])
    if len(diffs) > 80:
        print(f"  ... {len(diffs) - 80} more in audit/out/differences.json")


if __name__ == "__main__":
    main()
