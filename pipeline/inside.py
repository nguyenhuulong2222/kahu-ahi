#!/usr/bin/env python3
"""Optional check for a large region: does its conversion fit a smaller region that lies inside it?

  docs/data/<large>_inside.json   the smaller region's leave-one-year-out error with its own coefficients,
                                  and with the large region's coefficients, on the same months

One coefficient per calendar month for a whole country averages over places whose fires burn at different
times of day and in different fuels. This measures what that costs for one area inside it. For each year held
out, the large region's coefficients are fitted without that year and applied to the smaller region's Suomi NPP
counts for that year; the result is compared with what MODIS Aqua recorded there. The smaller region's own
number is its usual leave-one-year-out error (calibrate.py), repeated here on the same months.

Nothing here changes a coefficient, the acceptance rule or any file written by the other steps.

Standard library only. Usage:
  python3 pipeline/inside.py --large data/processed/conus --small data/processed/california
"""
import argparse
import json
from pathlib import Path

from calibrate import DRIFT_YEAR, errors, fit, load_monthly, pairs, predict


def snpp_aqua_pairs(region_dir):
    monthly = load_monthly(region_dir / "daily_counts.csv")
    through = max(c["last_day"] for m in monthly.values() for c in m.values())[:7]
    return pairs(monthly, "VIIRS_SNPP", "MODIS_AQUA", through)


def tables(rows):
    return {"all_years": errors([(o, p) for _, o, p in rows]),
            f"before_{DRIFT_YEAR}": errors([(o, p) for y, o, p in rows if y < DRIFT_YEAR]),
            f"{DRIFT_YEAR}_onward": errors([(o, p) for y, o, p in rows if y >= DRIFT_YEAR])}


def compare(large_dir, small_dir):
    large, small = snpp_aqua_pairs(large_dir), snpp_aqua_pairs(small_dir)
    own, outer, by_month = [], [], {}
    for year in sorted({y for y, *_ in small}):
        k_own, annual_own = fit([p for p in small if p[0] != year])
        k_out, annual_out = fit([p for p in large if p[0] != year])
        for y, m, num, den in small:
            if y != year:
                continue
            a, b = predict(k_own, annual_own, m, num, "monthly"), predict(k_out, annual_out, m, num, "monthly")
            if a is None or b is None:
                continue
            own.append((y, den, a))
            outer.append((y, den, b))
    # The large region's own leave-one-year-out error, calendar month by calendar month.
    for year in sorted({y for y, *_ in large}):
        k, annual = fit([p for p in large if p[0] != year])
        for y, m, num, den in large:
            if y == year and predict(k, annual, m, num, "monthly") is not None:
                by_month.setdefault(m, []).append((den, predict(k, annual, m, num, "monthly")))
    k_small, annual_small = fit(small)
    k_large, annual_large = fit(large)
    return {
        "metric": "n_veg_conf",
        "method": "leave-one-year-out; observed = MODIS Aqua count in the smaller region; both rows use the same months",
        "large": large_dir.name, "small": small_dir.name,
        "annual_k": {"large": round(annual_large, 3), "small": round(annual_small, 3)},
        "k_by_month": {"large": {m: round(v, 3) if v else None for m, v in k_large.items()},
                       "small": {m: round(v, 3) if v else None for m, v in k_small.items()}},
        "small_with_own_k": tables(own),
        "small_with_large_k": tables(outer),
        "large_by_calendar_month": {m: errors(rows) for m, rows in sorted(by_month.items())},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--large", type=Path, required=True)
    ap.add_argument("--small", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("docs/data"))
    args = ap.parse_args()
    doc = compare(args.large, args.small)
    path = args.out / f"{args.large.name}_inside.json"
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    a, b = doc["small_with_own_k"]["all_years"], doc["small_with_large_k"]["all_years"]
    print(f"{doc['small']} with its own coefficients: {a['abs_error_pct_of_total']}% of total, bias {a['bias_pct']}% ({a['months']} months)")
    print(f"{doc['small']} with the coefficients of {doc['large']}: {b['abs_error_pct_of_total']}% of total, bias {b['bias_pct']}%")
    worst = max(doc["large_by_calendar_month"].items(), key=lambda kv: kv[1]["abs_error_pct_of_total"])
    best = min(doc["large_by_calendar_month"].items(), key=lambda kv: kv[1]["abs_error_pct_of_total"])
    print(f"{doc['large']} by calendar month: {best[1]['abs_error_pct_of_total']}% (month {best[0]}) to {worst[1]['abs_error_pct_of_total']}% (month {worst[0]})")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
