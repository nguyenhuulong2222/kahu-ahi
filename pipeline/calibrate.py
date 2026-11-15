#!/usr/bin/env python3
"""Step 2 of the Kahu Ahi pipeline: put VIIRS on a MODIS-Aqua-equivalent scale and measure the error.

Reads daily_counts.csv from step 1 and writes, per region:

  monthly_series.csv   one row per month: each sensor's count, the Aqua-equivalent values,
                       the harmonized value, which sensor it came from, and a status label
  calibration.json     the monthly coefficients and every validation number

Method
  k(m) = sum of VIIRS counts / sum of Aqua counts, over all training years, for calendar month m
  VIIRS Aqua-equivalent = VIIRS count / k(m)
Months after Suomi NPP stopped (2 Nov 2026) come from NOAA-20. NOAA-20 is used 1:1 in place of
S-NPP: the same leave-one-year-out test showed a NOAA-20 -> S-NPP coefficient does not reduce the
error, so none is applied. That test is still run and reported.

The current, incomplete month is compared with the same range of days in earlier years
(month-to-date), never with a full-month median.

Validation is leave-one-year-out: each year is predicted from coefficients fitted without it.
Only standard-quality, complete months are used to fit or validate.

Standard library only. Usage:
  python3 pipeline/calibrate.py --region data/processed/california
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

METRIC = "n_veg_conf"  # vegetation-fire detections (type 0), low confidence removed

# Months that a sensor only partly covers, so they are never used to fit or validate.
# Dates from the FIRMS archive download page.
PARTIAL_START = {"MODIS_AQUA": "2002-07", "VIIRS_SNPP": "2012-01", "MODIS_TERRA": "2000-11"}
SNPP_LAST_FULL_MONTH = "2026-10"  # S-NPP delivered no new observations after 2 Nov 2026
# Calibration is refused for a region when it cannot be shown to work there.
MAX_LOYO_ERROR_PCT = 50   # leave-one-year-out absolute error, as % of the observed total
MIN_MONTHS_WITH_OWN_K = 9  # calendar months that have enough data for their own coefficient
DRIFT_YEAR = 2022  # Aqua orbit drift: approximate, see README (to be verified)


def load_monthly(path):
    """month -> sensor -> {'value': count, 'quality': 'standard'|'nrt'|'mixed', 'last_day': 'YYYY-MM-DD'}"""
    out = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            month = row["date"][:7]
            cell = out[month].setdefault(row["sensor"], {"value": 0, "quality": row["quality"], "last_day": row["date"]})
            cell["value"] += int(row[METRIC])
            if cell["quality"] != row["quality"]:
                cell["quality"] = "mixed"
            cell["last_day"] = max(cell["last_day"], row["date"])
    return fill_silent_months(out)


def fill_silent_months(monthly):
    """A month with no detections has no rows. While the satellite was flying that is a recorded 0,
    not a gap, so fill it in. Whether the region could actually be observed remains unknown."""
    span = {}
    for month, cells in monthly.items():
        for sensor, c in cells.items():
            s = span.setdefault(sensor, {"first": month, "last": month, "last_standard": ""})
            s["first"], s["last"] = min(s["first"], month), max(s["last"], month)
            if c["quality"] == "standard":
                s["last_standard"] = max(s["last_standard"], month)
    if not span:
        return monthly
    first = min(s["first"] for s in span.values())
    last = max(s["last"] for s in span.values())
    y, m = int(first[:4]), int(first[5:])
    while f"{y:04d}-{m:02d}" <= last:
        month = f"{y:04d}-{m:02d}"
        for sensor, s in span.items():
            if s["first"] <= month <= s["last"] and sensor not in monthly[month]:
                monthly[month][sensor] = {"value": 0, "last_day": month + "-01",
                                          "quality": "standard" if month <= s["last_standard"] else "nrt"}
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return monthly


def usable(monthly, month, sensor, data_through_month):
    """A month is usable for fitting/validation if it is complete and standard quality."""
    cell = monthly.get(month, {}).get(sensor)
    if cell is None:
        return False  # the satellite was not flying yet, or had stopped
    if cell["quality"] != "standard":
        return False
    if month == PARTIAL_START.get(sensor) or month >= data_through_month:
        return False
    return True


def pairs(monthly, num_sensor, den_sensor, data_through_month):
    """[(year, month_of_year, numerator count, denominator count)] where both sensors are usable."""
    out = []
    for month in sorted(monthly):
        if usable(monthly, month, num_sensor, data_through_month) and usable(monthly, month, den_sensor, data_through_month):
            out.append((int(month[:4]), int(month[5:]), monthly[month][num_sensor]["value"], monthly[month][den_sensor]["value"]))
    return out


def fit(train):
    """Monthly coefficients k[m] = sum(num)/sum(den), plus one annual coefficient as fallback."""
    num = defaultdict(int)
    den = defaultdict(int)
    for _, m, n, d in train:
        num[m] += n
        den[m] += d
    total_den = sum(den.values())
    annual = sum(num.values()) / total_den if total_den else None
    k = {}
    for m in range(1, 13):
        # Refuse a monthly coefficient built on almost nothing; fall back to the annual one.
        k[m] = num[m] / den[m] if den[m] >= 30 and num[m] > 0 else None
    return k, annual


def errors(rows):
    """rows: [(observed, predicted)] -> summary numbers."""
    if not rows:
        return None
    abs_err = [abs(p - o) for o, p in rows]
    total_obs = sum(o for o, _ in rows)
    return {
        "months": len(rows),
        "mae": round(sum(abs_err) / len(rows), 1),
        "median_abs_error": round(median(abs_err), 1),
        "abs_error_pct_of_total": round(100 * sum(abs_err) / total_obs, 1) if total_obs else None,
        "bias_pct": round(100 * (sum(p for _, p in rows) - total_obs) / total_obs, 1) if total_obs else None,
    }


def predict(k, annual, m, value, mode):
    if mode == "raw":
        return value
    coeff = annual if mode == "annual" else (k[m] if k[m] is not None else annual)
    return value / coeff if coeff else None


def loyo(all_pairs, split_year):
    """Leave-one-year-out. Returns error tables for monthly k, one annual k, and no calibration."""
    held = {"monthly_k": [], "annual_k": [], "uncalibrated": []}
    for year in sorted({y for y, *_ in all_pairs}):
        train = [p for p in all_pairs if p[0] != year]
        k, annual = fit(train)
        for y, m, num, den in all_pairs:
            if y != year:
                continue
            for mode, key in (("monthly", "monthly_k"), ("annual", "annual_k"), ("raw", "uncalibrated")):
                p = predict(k, annual, m, num, mode)
                if p is not None:
                    held[key].append((y, den, p))
    out = {}
    for key, rows in held.items():
        out[key] = {
            "all_years": errors([(o, p) for _, o, p in rows]),
            f"before_{split_year}": errors([(o, p) for y, o, p in rows if y < split_year]),
            f"{split_year}_onward": errors([(o, p) for y, o, p in rows if y >= split_year]),
        }
    return out


def forward_test(all_pairs, train_end, split_year):
    """Fit on years up to train_end, test on later years: does an old calibration still hold?"""
    train = [p for p in all_pairs if p[0] <= train_end]
    k, annual = fit(train)
    def score(lo, hi):
        rows = [(d, predict(k, annual, m, n, "monthly")) for y, m, n, d in all_pairs if lo <= y <= hi]
        return errors([r for r in rows if r[1] is not None])
    return {"trained_on": f"up to {train_end}",
            f"{train_end + 1}_to_{split_year - 1}": score(train_end + 1, split_year - 1),
            f"{split_year}_onward": score(split_year, 9999)}


def describe_k(all_pairs, k, annual):
    by_month = defaultdict(list)
    for _, m, n, d in all_pairs:
        if d > 0:
            by_month[m].append(n / d)
    table = {}
    for m in range(1, 13):
        ratios = by_month[m]
        table[str(m)] = {"k": round(k[m], 3) if k[m] is not None else None,
                         "uses_annual_fallback": k[m] is None,
                         "years": len(ratios),
                         "yearly_ratio_min": round(min(ratios), 2) if ratios else None,
                         "yearly_ratio_max": round(max(ratios), 2) if ratios else None}
    return {"annual_k": round(annual, 3) if annual else None, "by_month": table}


def month_to_date(daily_path, data_through, k_month):
    """Compare the current month so far with the same days of that month in earlier years.

    The last date in the download is dropped: it was still being observed when the file was made.
    Earlier years use MODIS Aqua standard data, which is already on the reference scale.
    """
    year, mon, last = int(data_through[:4]), data_through[5:7], int(data_through[8:]) - 1
    if last < 1:
        return None
    now = 0
    now_aqua = 0
    past = defaultdict(int)
    with open(daily_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = row["date"]
            if d[5:7] != mon or int(d[8:]) > last:
                continue
            if int(d[:4]) == year and row["sensor"] == "VIIRS_NOAA20":
                now += int(row[METRIC])
            elif int(d[:4]) == year and row["sensor"] == "MODIS_AQUA":
                now_aqua += int(row[METRIC])
            elif int(d[:4]) < year and row["sensor"] == "MODIS_AQUA" and row["quality"] == "standard":
                past[int(d[:4])] += int(row[METRIC])
    # A year with no Aqua detections in those days has no rows; count it as 0 once Aqua was flying.
    first_year = 2003 if mon <= "07" else 2002
    values = sorted(past.get(y, 0) for y in range(first_year, year))
    if not values:
        return None
    value = round(now / k_month, 1) if k_month else None
    return {
        "month": data_through[:7],
        "days": f"1-{last}",
        "source": "VIIRS_NOAA20 near-real-time, on the Aqua scale",
        "value_aqua_equiv": value,
        "raw_noaa20": now,
        "aqua_nrt_same_days": now_aqua,
        "baseline": f"MODIS Aqua, same days, {first_year}-{year - 1}",
        "baseline_years": len(values),
        "baseline_median": median(values),
        "baseline_min": values[0],
        "baseline_max": values[-1],
        "years_below_current": sum(1 for v in values if v < value) if value is not None else None,
        "years_below_current_aqua_nrt": sum(1 for v in values if v < now_aqua),
        "caveat": "near-real-time files have no `type` column, so static heat sources are not removed from the current month",
    }


def period_errors(rows, split_year):
    """rows: [(year, observed, predicted)] -> the three error tables."""
    return {"all_years": errors([(o, p) for _, o, p in rows]),
            f"before_{split_year}": errors([(o, p) for y, o, p in rows if y < split_year]),
            f"{split_year}_onward": errors([(o, p) for y, o, p in rows if y >= split_year])}


def held_out(train, test):
    """Predict each year of `test` from monthly coefficients fitted on `train` without that year.
    Returns [(year, month_of_year, observed, predicted)]."""
    out = []
    for year in sorted({y for y, *_ in test}):
        k, annual = fit([p for p in train if p[0] != year])
        for y, m, num, den in test:
            if y == year:
                pred = predict(k, annual, m, num, "monthly")
                if pred is not None:
                    out.append((y, m, den, pred))
    return out


def worst_months(rows, n=5, min_observed=30):
    """The months furthest off in percent, among months with at least `min_observed` observed detections."""
    big = [(abs(p - o) / o, y, m, o, p) for y, m, o, p in rows if o >= min_observed]
    return [{"month": f"{y}-{m:02d}", "observed_aqua": o, "predicted": round(p, 1), "pct_diff": round(100 * (p - o) / o, 1)}
            for _, y, m, o, p in sorted(big, reverse=True)[:n]]


def as_used(monthly, through_month, snpp_aqua, k_sa, annual_sa, accepted):
    """The error of the conversion as the page uses it for recent months.

    The coefficients are fitted on Suomi NPP against Aqua, both standard data. For recent months the page
    applies them to NOAA-20, and to near-real-time rows. Two measurements of that chain:

    1. NOAA-20 standard against Aqua standard, every month both have: each year predicted with Suomi NPP
       coefficients fitted without that year. Beside it, the same test with coefficients fitted on NOAA-20
       itself. The NOAA-20 coefficients are adopted only if their error on the held-out years is lower.
    2. NOAA-20 near-real-time against Aqua, every complete month both have. There are only as many such months
       as the near-real-time files hold, all in one year, so nothing can be fitted and tested on held-out years;
       the months are listed one by one, with a single near-real-time ratio tested by leaving one month out.
    """
    n20_aqua = pairs(monthly, "VIIRS_NOAA20", "MODIS_AQUA", through_month)
    out = {"definition": "NOAA-20 count / k(m), k(m) fitted on Suomi NPP against Aqua (standard data), compared with the MODIS Aqua count",
           "why": "the tested conversion is Suomi NPP standard against Aqua standard; recent months use NOAA-20, near-real-time"}
    with_snpp = held_out(snpp_aqua, n20_aqua)
    with_own = held_out(n20_aqua, n20_aqua)
    e_snpp, e_own = period_errors([(y, o, p) for y, _, o, p in with_snpp], DRIFT_YEAR), period_errors([(y, o, p) for y, _, o, p in with_own], DRIFT_YEAR)
    a, b = (e_snpp["all_years"] or {}).get("abs_error_pct_of_total"), (e_own["all_years"] or {}).get("abs_error_pct_of_total")
    k_own, annual_own = fit(n20_aqua)
    adopt_own = a is not None and b is not None and b < a
    out["noaa20_standard"] = {
        "paired_months": len(n20_aqua),
        "years": [min(y for y, *_ in n20_aqua), max(y for y, *_ in n20_aqua)] if n20_aqua else None,
        "with_snpp_coefficients": e_snpp,
        "with_noaa20_coefficients": e_own,
        "noaa20_coefficients": describe_k(n20_aqua, k_own, annual_own) if n20_aqua else None,
        "worst_months_with_snpp_coefficients": worst_months(with_snpp),
        "adopted": "noaa20_coefficients" if adopt_own else "snpp_coefficients",
        "adoption_rule": "NOAA-20's own coefficients are used only if their leave-one-year-out error over all years is lower than that of the Suomi NPP coefficients on the same months",
    }
    k_use, annual_use = (k_own, annual_own) if adopt_own else (k_sa, annual_sa)
    # 2. near-real-time months
    months, rows = [], []
    for month in sorted(monthly):
        c = monthly[month]
        if month >= through_month or "VIIRS_NOAA20" not in c or "MODIS_AQUA" not in c or c["VIIRS_NOAA20"]["quality"] != "nrt":
            continue
        m = int(month[5:])
        coeff = k_use[m] if k_use[m] is not None else annual_use
        if not coeff:
            continue
        n, o = c["VIIRS_NOAA20"]["value"], c["MODIS_AQUA"]["value"]
        pred = n / coeff
        rows.append((int(month[:4]), m, n, o, pred))
        months.append({"month": month, "aqua": o, "aqua_quality": c["MODIS_AQUA"]["quality"], "noaa20_nrt": n, "predicted": round(pred, 1),
                       "pct_diff": round(100 * (pred - o) / o, 1) if o else None})
    loo = []
    for i, (_, _, n, o, _) in enumerate(rows):
        rest = [r for j, r in enumerate(rows) if j != i]
        den = sum(r[3] for r in rest)
        if len(rest) >= 1 and den > 0 and sum(r[2] for r in rest) > 0:
            loo.append((o, n / (sum(r[2] for r in rest) / den)))
    out["noaa20_nrt"] = {
        "months": months,
        "error": errors([(o, p) for _, _, _, o, p in rows]),
        "worst_month": max(months, key=lambda x: abs(x["pct_diff"] or 0)) if months else None,
        "single_nrt_ratio_leave_one_month_out": errors(loo),
        "note": "too few months, all in one year, to fit or adopt anything; a single ratio fitted on the other near-real-time months is shown for comparison only",
    }
    e_std = out["noaa20_standard"]["with_noaa20_coefficients" if adopt_own else "with_snpp_coefficients"]["all_years"]
    std_pct = e_std["abs_error_pct_of_total"] if e_std else None
    nrt_pct = out["noaa20_nrt"]["error"]["abs_error_pct_of_total"] if out["noaa20_nrt"]["error"] else None
    own = sum(1 for v in k_use.values() if v is not None)
    ok = bool(accepted and std_pct is not None and std_pct <= MAX_LOYO_ERROR_PCT and own >= MIN_MONTHS_WITH_OWN_K
              and (nrt_pct is None or nrt_pct <= MAX_LOYO_ERROR_PCT))
    out["accepted"] = ok
    out["acceptance_rule"] = (f"the region's conversion is accepted, and the chain as used passes the same rule: error <= {MAX_LOYO_ERROR_PCT}% of total "
                              f"on held-out years of NOAA-20 standard data and over the complete near-real-time months, and at least "
                              f"{MIN_MONTHS_WITH_OWN_K} calendar months with their own coefficient; this region: {std_pct}% (standard), "
                              f"{nrt_pct}% (near-real-time, {len(months)} months), {own} months")
    return out, (k_use, annual_use) if adopt_own else None


def calibrate(region_dir):
    monthly = load_monthly(region_dir / "daily_counts.csv")
    data_through = max(c["last_day"] for m in monthly.values() for c in m.values())
    through_month = data_through[:7]

    snpp_aqua = pairs(monthly, "VIIRS_SNPP", "MODIS_AQUA", through_month)
    n20_snpp = pairs(monthly, "VIIRS_NOAA20", "VIIRS_SNPP", through_month)
    k_sa, annual_sa = fit(snpp_aqua)
    k_ns, annual_ns = fit(n20_snpp)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metric": METRIC,
        "data_through": data_through,
        "snpp_to_aqua": {
            "definition": "k(m) = sum(VIIRS_SNPP) / sum(MODIS_AQUA) per calendar month; Aqua-equivalent = SNPP / k(m)",
            "paired_months": len(snpp_aqua),
            "years": [min(y for y, *_ in snpp_aqua), max(y for y, *_ in snpp_aqua)] if snpp_aqua else None,
            "coefficients": describe_k(snpp_aqua, k_sa, annual_sa),
            "leave_one_year_out": loyo(snpp_aqua, DRIFT_YEAR),
            "forward_test": forward_test(snpp_aqua, 2018, DRIFT_YEAR),
        },
        "noaa20_to_snpp": {
            "definition": "tested: k(m) = sum(VIIRS_NOAA20) / sum(VIIRS_SNPP) per calendar month",
            "applied": "none - NOAA-20 is used 1:1 as S-NPP; see leave_one_year_out.uncalibrated for the error of doing so",
            "paired_months": len(n20_snpp),
            "years": [min(y for y, *_ in n20_snpp), max(y for y, *_ in n20_snpp)] if n20_snpp else None,
            "coefficients": describe_k(n20_snpp, k_ns, annual_ns),
            "leave_one_year_out": loyo(n20_snpp, DRIFT_YEAR),
        },
    }

    loyo_err = (result["snpp_to_aqua"]["leave_one_year_out"]["monthly_k"]["all_years"] or {}).get("abs_error_pct_of_total")
    own_k = sum(1 for v in k_sa.values() if v is not None)
    accepted = loyo_err is not None and loyo_err <= MAX_LOYO_ERROR_PCT and own_k >= MIN_MONTHS_WITH_OWN_K
    result["calibration_accepted"] = accepted
    result["acceptance_rule"] = (f"leave-one-year-out error <= {MAX_LOYO_ERROR_PCT}% of total and at least "
                                 f"{MIN_MONTHS_WITH_OWN_K} calendar months with their own coefficient; "
                                 f"this region: error {loyo_err}%, {own_k} months")

    result["as_used"], n20_own = as_used(monthly, through_month, snpp_aqua, k_sa, annual_sa, accepted)

    def coeff(k, annual, m):
        if not accepted:
            return None
        return k[m] if k[m] is not None else annual

    # NOAA-20 is converted with the Suomi NPP coefficients unless its own were shown to do better on held-out years.
    k_n20, annual_n20 = n20_own if n20_own else (k_sa, annual_sa)

    result["current_month"] = month_to_date(region_dir / "daily_counts.csv", data_through,
                                            coeff(k_n20, annual_n20, int(through_month[5:])))

    with open(region_dir / "monthly_series.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "terra", "aqua", "snpp", "noaa20", "snpp_aqua_equiv", "noaa20_aqua_equiv",
                    "harmonized", "harmonized_source", "status"])
        for month in sorted(monthly):
            cells = monthly[month]
            m = int(month[5:])
            def val(s):
                return cells[s]["value"] if s in cells else ""
            def q(s):
                return cells[s]["quality"] if s in cells else None
            snpp_eq = n20_eq = ""
            if "VIIRS_SNPP" in cells and coeff(k_sa, annual_sa, m):
                snpp_eq = round(cells["VIIRS_SNPP"]["value"] / coeff(k_sa, annual_sa, m), 1)
            if "VIIRS_NOAA20" in cells and coeff(k_n20, annual_n20, m):
                n20_eq = round(cells["VIIRS_NOAA20"]["value"] / coeff(k_n20, annual_n20, m), 1)

            partial = month == through_month
            # Which value represents the month, in order of preference.
            if q("MODIS_AQUA") == "standard" and month != PARTIAL_START["MODIS_AQUA"]:
                value, source, status = val("MODIS_AQUA"), "MODIS_AQUA", "standard"
            elif "MODIS_AQUA" in cells and month != PARTIAL_START["MODIS_AQUA"]:
                # Aqua near-real-time: the reference sensor itself, not yet reprocessed.
                value, source, status = val("MODIS_AQUA"), "MODIS_AQUA", "provisional_nrt"
            elif q("VIIRS_SNPP") == "standard" and snpp_eq != "":
                value, source, status = snpp_eq, "VIIRS_SNPP", "standard_calibrated"
            elif n20_eq != "":
                value, source = n20_eq, "VIIRS_NOAA20"
                status = "provisional_nrt" if q("VIIRS_NOAA20") != "standard" else "standard_calibrated"
            elif snpp_eq != "" and month <= SNPP_LAST_FULL_MONTH:
                value, source, status = snpp_eq, "VIIRS_SNPP", "provisional_nrt"
            elif "MODIS_AQUA" in cells:
                value, source, status = val("MODIS_AQUA"), "MODIS_AQUA", "partial_first_month"
            elif "MODIS_TERRA" in cells:
                # Before Aqua existed. Terra is a morning sensor and is not on the Aqua scale.
                value, source, status = "", "MODIS_TERRA", "terra_only_not_harmonized"
            elif "VIIRS_NOAA20" in cells or "VIIRS_SNPP" in cells:
                # VIIRS saw something but this region has no trustworthy coefficient.
                value, source, status = "", "VIIRS", "not_calibrated_insufficient_overlap"
            else:
                value, source, status = "", "", "no_detections_coverage_unknown"
            if partial and status != "terra_only_not_harmonized":
                status = "partial_month_" + status
            w.writerow([month, val("MODIS_TERRA"), val("MODIS_AQUA"), val("VIIRS_SNPP"), val("VIIRS_NOAA20"),
                        snpp_eq, n20_eq, value, source, status])

    with open(region_dir / "calibration.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result


def show(title, table):
    print(title)
    for name, periods in table.items():
        for period, e in periods.items():
            if e:
                print(f"  {name:13s} {period:14s} months={e['months']:3d}  MAE={e['mae']:>8}  "
                      f"abs err={e['abs_error_pct_of_total']:>6}% of total  bias={e['bias_pct']:>7}%")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--region", type=Path, default=Path("data/processed/california"))
    args = ap.parse_args()
    r = calibrate(args.region)
    sa = r["snpp_to_aqua"]
    print(f"calibration accepted: {r['calibration_accepted']}  ({r['acceptance_rule']})")
    print(f"metric: {r['metric']}   data through: {r['data_through']}")
    print(f"S-NPP -> Aqua: {sa['paired_months']} paired months, years {sa['years']}, annual k = {sa['coefficients']['annual_k']}")
    print("  k by month: " + "  ".join(f"{m}:{v['k']}" for m, v in sa["coefficients"]["by_month"].items()))
    show("Leave-one-year-out, S-NPP -> Aqua (observed = Aqua count):", sa["leave_one_year_out"])
    ft = sa["forward_test"]
    print(f"Forward test, trained {ft['trained_on']}:")
    for period, e in ft.items():
        if isinstance(e, dict):
            print(f"  {period:14s} months={e['months']:3d}  MAE={e['mae']:>8}  abs err={e['abs_error_pct_of_total']}% of total  bias={e['bias_pct']}%")
    ns = r["noaa20_to_snpp"]
    print(f"NOAA-20 -> S-NPP: {ns['paired_months']} paired months, annual k = {ns['coefficients']['annual_k']}")
    show("Leave-one-year-out, NOAA-20 -> S-NPP (observed = S-NPP count):", ns["leave_one_year_out"])
    cm = r["current_month"]
    if cm:
        print(f"Current month {cm['month']} days {cm['days']}: NOAA-20 on Aqua scale {cm['value_aqua_equiv']} "
              f"(raw NOAA-20 {cm['raw_noaa20']}), Aqua near-real-time {cm['aqua_nrt_same_days']}; {cm['baseline']}: median {cm['baseline_median']}, "
              f"range {cm['baseline_min']}-{cm['baseline_max']}; higher than {cm['years_below_current']} of {cm['baseline_years']} years")
    print(f"wrote {args.region / 'monthly_series.csv'} and {args.region / 'calibration.json'}")


if __name__ == "__main__":
    main()
