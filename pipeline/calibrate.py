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
    return out


def usable(monthly, month, sensor, data_through_month):
    """A month is usable for fitting/validation if it is complete and standard quality."""
    cell = monthly.get(month, {}).get(sensor)
    if cell is None:
        # No detections at all that month. Whether that is a true zero is unknown, so skip it.
        return False
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

    def coeff(k, annual, m):
        if not accepted:
            return None
        return k[m] if k[m] is not None else annual

    result["current_month"] = month_to_date(region_dir / "daily_counts.csv", data_through,
                                            coeff(k_sa, annual_sa, int(through_month[5:])))

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
            if "VIIRS_NOAA20" in cells and coeff(k_sa, annual_sa, m):
                n20_eq = round(cells["VIIRS_NOAA20"]["value"] / coeff(k_sa, annual_sa, m), 1)

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
