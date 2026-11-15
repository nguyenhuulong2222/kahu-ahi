# Kahu Ahi

**One consistent satellite fire record across the MODIS → VIIRS transition, honest about what satellites cannot see.**

*Kahu Ahi* is Hawaiian for "keeper of the fire" (*kahu*, keeper or guardian; *ahi*, fire). The mark, `docs/kahu-ahi-mark.svg`, is a flame built from square satellite pixels in the colours of the page's fire ramp; it was made for this project on 14 Nov 2026 and is also the favicon and the basis of the link-preview image `docs/kahu-ahi-og.png`.

NASA Space Apps Challenge 2026 · Challenge: *Harmonization of MODIS and VIIRS Hot Spots* · Local Event: Honolulu, HI · Team: Kahu Ahi

> **Status:** submission version, built during the hackathon (14–15 Nov 2026, HST). Every figure below is a measured result; an outside audit and what was done about it are in [AUDIT.md](AUDIT.md).

## What it does

- Puts VIIRS active-fire detections on a MODIS-Aqua-equivalent scale so monthly fire activity can be compared across sensors.
- Shows a month × year burning calendar for supported regions.
- Compares the current month with the multi-year median for the same range of days.
- Shows where the burning was on a map: each month on a grid of 0.1° cells, per satellite, with the individual detections at high zoom.
- Lets you choose an area inside a supported region and recomputes the calendar, the usual months and the month-to-date comparison for it.
- Lets you download the underlying hotspot records as CSV, for the whole region or the chosen area.
- Labels every value with its data status (standard, provisional, not calibrated, partial month, unknown coverage).

## What it does not do

- It is not a fire alert, forecast, or real-time detection tool.
- It does not claim that sensors become identical after calibration. Remaining error is reported.
- "No detection" is never shown as "no fire". Clouds, smoke, short fires and overpass timing all hide fires.
- It supports a small set of pre-processed regions, not arbitrary areas worldwide. A chosen area must lie inside one of them.
- A blank map cell is not "no fire" and not "safe": it only means no detection was recorded.

## Data

All fire data come from NASA FIRMS. Details, access dates and citations are in [SOURCES.md](SOURCES.md).

| Role | Product | Satellite | Period used |
|---|---|---|---|
| Reference series | MCD14ML (MODIS C6.1), `satellite = A` | Aqua | 2002-07 → latest standard month |
| Early series (kept separate) | MCD14ML, `satellite = T` | Terra | 2000-11 → 2002-06 |
| Calibrated series | VNP14IMGML (VIIRS 375 m) | Suomi NPP | 20 Jan 2012 → 2 Nov 2026 (its last data) |
| VIIRS side of current months | VJ114IMGML / VJ114IMGTDL_NRT | NOAA-20 | 1 Apr 2018 → present |

## Sensor timeline that shapes the method

- **Why this project exists.** NASA's notice "Transition from MODIS to VIIRS" (2 May 2025) says that Terra and Aqua "will begin shutting down operations" in late 2026/early 2027, that both "are currently drifting out of their designed orbits, impacting crossing times and possibly impacting data", and encourages users to move to VIIRS products (SOURCES.md). As of the last download (14 Nov 2026) Aqua is still delivering data; this project does not say it has stopped.
- Suomi NPP stopped delivering new observations on 2 Nov 2026 (FIRMS), so the VIIRS side of current months comes from NOAA-20. The calendar value of a current month is still MODIS Aqua.
- Aqua's orbit is changing. NASA reports that Aqua "completed the last of its drag makeup maneuvers in December 2021 and is now in a free-drift mode, slowly descending below the A-Train and drifting to later equatorial crossing times, and lower altitudes"; by January 2025 its crossing time had moved about 50 minutes later (sources in SOURCES.md). The pipeline therefore splits validation at **2022** (`DRIFT_YEAR` in `pipeline/calibrate.py`), the first year of free drift, and reports the error before and after. Whether the drift causes the higher error after 2022 is not established by this project.
- Standard-quality monthly files lag by about 2–3 months. Newer months are near-real-time and labelled provisional.

## Metrics (never mixed)

1. `raw_detection_count` — hotspot records after quality filtering.
2. `grid_day_count` — number of (grid cell, date) pairs with at least one detection. Not a hotspot total.
3. `monthly_density` — the chosen metric divided by region area (per 1,000 km²) per month.

Calibration, calendar, median, map and validation all use the same metric: **metric 1, `raw_detection_count`**, computed as `n_veg_conf` in the pipeline:

- type 0 detections only (presumed vegetation fire); type 1 (volcano), 2 (other static land source) and 3 (offshore) are removed;
- near-real-time files have no `type` column, so their rows are dropped where the standard archive repeatedly recorded a non-vegetation source (the static-source mask: 0.02° cells with at least 3 such archive detections);
- low confidence removed (MODIS confidence below 30, VIIRS `l`).

Details needed to reproduce the counts exactly (an independent recomputation, `audit/recompute.py`, differed by one detection in three months until these were stated):

- a point is inside a region when west ≤ longitude ≤ east and south ≤ latitude ≤ north (both edges included);
- the satellite of a MODIS row is its `satellite` column (`Aqua` / `Terra` in the files); Suomi NPP and NOAA-20 are told apart by the download (`SV-C2`, `J1V-C2`);
- months and days are the UTC `acq_date`;
- a point's mask cell is `int((lat + 90) / 0.02)`, `int((lon + 180) / 0.02)`; every archive row of type 1, 2 or 3 counts toward the 3, whatever its sensor or confidence;
- the 30-detection fallback is applied again inside every leave-one-year-out fit; bias is (sum of predictions − sum of Aqua) / sum of Aqua;
- NOAA-20's 100 paired months run from April 2018 to July 2026.

Why counts: the same filter can be applied to every sensor's records, and counts can be checked row by row against the downloadable CSV, whose `counted` column is exactly this flag. Metrics 2 and 3 are not used anywhere in this version.

## Method

- **Calibration pair:** VIIRS Suomi NPP (375 m) against MODIS Aqua (about 1 km). Both cross the equator in the early afternoon, so they see the same part of the day. Terra (morning) is never put on the Aqua scale.
- **Training window:** every month from February 2012 to July 2026 in which both sensors have complete, standard-quality data (174 months in each region). Partial first months and near-real-time months are never used.
- **Coefficient:** for each calendar month m, k(m) = Σ S-NPP counts / Σ Aqua counts over all training years. A VIIRS count is put on the Aqua scale by dividing by k(m). A calendar month whose Aqua total is under 30 falls back to one annual coefficient.
- **NOAA-20:** converted with the Suomi NPP coefficients, or with coefficients fitted on NOAA-20 against Aqua where those have the lower error on held-out years (see "The conversion as it is used"). A further NOAA-20 → S-NPP coefficient was tested and did not reduce the error, so none is applied.
- **Which value the calendar shows:** MODIS Aqua when it has data for the month (standard, else near-real-time); otherwise VIIRS on the Aqua scale. In all four regions Aqua still has data, so every calendar month from July 2002 is an Aqua count; the conversion is used for the month-to-date estimate and the "On the Aqua scale" columns.
- **Refusal:** calibration is refused for a region when the leave-one-year-out error exceeds 50% of the total, or fewer than 9 calendar months have their own coefficient. A refused region shows Aqua only and states the measured error.

### Partial-month comparison

The current month is compared with the median of the **same day range** (day 1 to D) in earlier years, never with a full-month median. Implemented, no fallback: D is the last date in the download minus one (that day was still being observed when the files were made), so for data through 14 Nov 2026 the comparison is 1–13 November against the same days of 2002–2025 (24 years of MODIS Aqua standard data; a year with no detection in those days counts as 0).

| Region | Aqua NRT, 1–13 Nov 2026 | NOAA-20 on the Aqua scale | Same days, earlier years: median (range) |
|---|---:|---:|---|
| California | 137 | 199.8 (raw 1,223, k(11) = 6.122) | 147 (49–642) |
| Vietnam region | 180 | 115.1 (raw 686, NOAA-20's own k(11) = 5.960) | 180.5 (56–453) |
| Contiguous United States | 1,356 | 1,783.5 (raw 9,681, NOAA-20's own k(11) = 5.428) | 2,181 (1,146–3,090) |
| Hawaiʻi | 0 | not converted (raw 1) | 0 (0–9) |

**Why the two estimates disagree in November 2026.** Checked day by day in `daily_counts.csv`:

- *California.* NOAA-20 recorded 8.9 counted detections per Aqua detection over 1–13 November, close to September (9.4) and October (8.6). The sensors behave as before; the gap comes from the November coefficient, k(11) = 6.12, which is lower than this year's ratio. November is one of the least certain months: its leave-one-year-out error is 24.2% of the total (September 5.4%), and the yearly November ratio ranged 4.43–9.69 over 2012–2025. September and October agree within 2% because k(9) = 9.62 and k(10) = 8.50 happen to match this year's ratios.
- *Vietnam region.* September and October do **not** agree within 2%: NOAA-20 on the Aqua scale is 413 vs Aqua 461 (−10.5%) and 527 vs 755 (−30.2%) with NOAA-20's own factors (373 and 500 with the Suomi NPP factors used before the as-used test below). The yearly November S-NPP/Aqua ratio fell from 9.88 (2012) to 4.12–5.16 (2023–2025), and this year's NOAA-20/Aqua ratio is 3.8; k(11) = 6.94 pools all years, so the converted value runs low. This matches the larger error from 2022 onward (15.8% vs 10.5%).
- *Incomplete days.* The last date (14 Nov) is already dropped. Days on which Aqua has no record at all while NOAA-20 has 10 or more: California 3 of 13 in November (02, 03, 06) against 4 in September and 2 in October; Vietnam region 0 in November against 9 in September and 9 in October. Missing Aqua days do not explain the November gap.
- *S-NPP* stopped on 2 Nov and does not enter either estimate.

Found: the gap is the November coefficient against this year's sensor ratio. Not found: why this year's ratio differs from earlier years (Aqua's orbit drift is one candidate; this record cannot confirm it). The page keeps both values, shows this year's ratio next to the coefficient and its historical range, and says the reason is not known.

## Validation

Leave-one-year-out: each year is predicted from coefficients fitted without it and compared with what Aqua recorded. Error is the sum of absolute monthly errors as a share of the total Aqua count. From `data/processed/<region>/calibration.json`.

| Region | Paired months | Annual VIIRS:Aqua | VIIRS used raw | One annual k | Monthly k (used) | 2012–2021 / 2022 onward (monthly k) | Bias, monthly k | NOAA-20 vs S-NPP, 1:1 (100 months) | Accepted |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| California | 174 | 8.47 | 747.1% | 19.0% | **15.2%** | 14.0% / 21.2% | +0.9% | 5.8% | yes |
| Vietnam region | 174 | 6.25 | 524.7% | 16.8% | **12.0%** | 10.5% / 15.8% | +0.1% | 3.4% | yes |
| Contiguous United States | 174 | 6.64 | 563.8% | 28.2% | **10.4%** | 10.1% / 10.9% | +0.3% | 4.5% | yes |
| Hawaiʻi | 174 | 169.08 | 16,808.2% | 168.0% | **256.2%** | 308.7% / 136.2% | +124.5% | 15.8% | **no** |

### The conversion as it is used

The table above tests Suomi NPP standard data against Aqua standard data. For recent months the page converts **NOAA-20**, and **near-real-time** rows. `calibrate.py` measures that chain and writes it to `calibration.json` and `<region>.json` under `as_used`:

1. *NOAA-20 standard against Aqua standard*, the 100 months both have (April 2018 to July 2026). Each year is predicted with coefficients fitted without it, once with the Suomi NPP coefficients and once with coefficients fitted on NOAA-20 itself. NOAA-20's own coefficients are adopted for a region only if their error on the held-out years is lower.
2. *NOAA-20 near-real-time against Aqua*, the complete months both have (August to October 2026; Aqua is standard in August and near-real-time after). Three months in one year cannot be fitted and tested on held-out years, so they are listed as they are.

| Region | Suomi NPP k on NOAA-20 (bias) | NOAA-20's own k (bias) | Used | Near-real-time months: Aug, Sep, Oct 2026 | Error over those 3 months | Passes the acceptance rule as used |
|---|---:|---:|---|---|---:|---|
| California | 14.6% (+3.3%) | 15.6% (+0.9%) | Suomi NPP k | −14.5%, −1.9%, +1.4% | 9.6% | yes |
| Vietnam region | 13.4% (−2.8%) | 13.2% (0.0%) | NOAA-20's own k | −39.5%, −10.5%, −30.2% | 26.1% | yes |
| Contiguous United States | 10.8% (+5.1%) | 10.4% (+0.4%) | NOAA-20's own k | −0.3%, −7.2%, +26.1% | 6.3% | yes |
| Hawaiʻi | 264.9% | 406.2% | not converted | not meaningful (0 to 2 Aqua detections a month) | 93.3% | no |

What this changed: in the Vietnam region and the contiguous United States every NOAA-20 value on the Aqua scale (104 months, April 2018 onward) is now computed with NOAA-20's own coefficients, and the month-to-date estimate moved from 98.8 to 115.1 (Vietnam region) and from 1,880.7 to 1,783.5 (United States). No Suomi NPP coefficient, no error figure in the validation table and no count changed. The gains on held-out years are small (0.2 and 0.4 points); the rule was to adopt on any measured improvement, and the near-real-time months moved the same way (United States October +39.1% to +26.1%; Vietnam region October −33.8% to −30.2%).

What it shows: on standard data the chain as used is about as accurate as the Suomi NPP test. On near-real-time data single months have been off by 26% to 40% in two regions. The page gives both figures wherever a recent converted value appears. Where the chain as used fails the acceptance rule (error over 50% on either measurement), recent converted values are shown as "not reliable"; with the present data that happens in no accepted region. The worst standard months, and a single near-real-time ratio tested by leaving one month out, are in `as_used` too.

Forward test (fit up to 2018, predict later years with monthly k): California 13.5% for 2019–2021 and 22.8% from 2022; Vietnam region 9.4% and 18.1%; contiguous United States 14.6% and 13.3%; Hawaiʻi 98.5% and 114.1%.

Months: 174 paired months per region (February 2012 to July 2026, standard data). Excluded: January 2012 (S-NPP's first, partial month), every near-real-time month (August 2026 onward for VIIRS, September 2026 onward for MODIS), and the current month. Hawaiʻi has only 5 calendar months with enough Aqua detections for their own coefficient (needs 9).

## Regions

| Region | Role | Bounding box |
|---|---|---|
| California test box (`california`) | First calibration region. A rectangle, not the state: it also takes in parts of Nevada, Arizona and Mexico. No longer in the page's region list; kept in the "Compare regions" table and as the small region of `pipeline/inside.py`. The state of California is one of the states below | lat 32.5–42.0, lon −124.5–−114.0 |
| Hawaiʻi | Case study of a low-detection region | lat 18.7–22.5, lon −160.6–−154.5 |
| Vietnam region | Second calibration and validation region | lat 8.4–23.4, lon 102.1–109.5 (also takes in parts of Laos, Cambodia and southern China) |
| Contiguous United States (`conus`) | Whole-country region | lat 24.4–49.5, lon −125.0–−66.9. Its FIRMS downloads are limited to the United States, so the rectangle holds no detections in Canada or Mexico; Alaska and Hawaiʻi lie outside it |

### The United States, state by state

The page's region list is United States, Hawaiʻi and Vietnam region. With United States selected a second list offers "Whole country" and the 48 states and DC. `pipeline/states.py` does the work:

- **Boundaries.** US Census Bureau cartographic boundary file for states, 1:5,000,000, 2023 (public domain; source and sha256 in `data/manifest.json` and SOURCES.md). Coordinates are rounded to 4 decimals and written to `docs/data/conus_states_geo.json` (1.3 MB), which both the pipeline and the page read.
- **Assignment.** Every national detection is given to the state whose outline contains its position (even-odd ray casting; not a bounding box). The page repeats the same test on the same numbers, so a state's table, map squares and CSV hold exactly the detections the pipeline counted for it. Of 14,077,544 detections, 27,962 (0.2%; 2,410 of them counted) fall in no state: offshore, or land the simplified coastline cuts off (for example the Lake Michigan shore of Indiana). They are kept under `outside` in the file and stay in the national numbers. Against the Census 1:500,000 file, 3 of 2,000 sampled detections were assigned differently, all three of this kind.
- **Check.** For every satellite and month, the states plus `outside` must equal the national series, or the step writes nothing. It holds for all 889 values.
- **Statistics.** Each state goes through `calibrate.calibrate()` unchanged: same counting, same fit, same tests, same acceptance rule, same as-used test. A satellite's months are the national ones, so a month in which a state has no detection is a recorded 0. The result is one file, `docs/data/conus_states.json` (0.8 MB): monthly series per satellite, factors with the number of months behind each, the three errors (as recorded, one whole-year ratio, monthly factors; all years, before and from 2022), the as-used chain, the acceptance decision, and the error when the national factors are used instead of the state's own. A second file, `docs/data/conus_states_daily.json` (3.4 MB), holds each state's counted detections per day; the page needs it for the daily chart, the busiest day and the default day, and loads it only when a state is opened. No hotspot or grid file is duplicated: a state view reads the national ones.
- **Result.** 37 of 49 are harmonized. 12 are not (Connecticut, Delaware, District of Columbia, Maine, Maryland, Massachusetts, Michigan, New Hampshire, New Jersey, New York, Rhode Island, Vermont): 9 fail both parts of the rule and 3 only the number of months; all are states where MODIS Aqua recorded few fires. Among the 37, the error on years left out runs from 14.0% (Arkansas) to 49.8% (North Dakota). In 15 of the 37 the conversion as used for recent months fails the same rule, and their recent converted values are shown as "not reliable". A refused state never shows a converted value.
- **National factors in a state.** Every harmonized state but one (Utah, 20.9% against 21.2%) does better with its own factors than with the national ones; the gap is largest in Texas (19.4% against 47.0%), West Virginia and North Dakota. The state of California: 15.7% with its own, 20.7% with the national factors (the test box: 15.2% and 20.0%).
- **Time.** A state shows local time only when every GeoNames place in it has the same zone (34 states and DC); otherwise UTC, with the reason. This follows the zones GeoNames gives its places, not a boundary file, so a state is called single-zone as far as its listed towns show.
- **On the page.** A state view fits and outlines the state and dims everything else. The band, calendar, charts, "this month so far", the VIIRS-only switch, the detections table, card, report and downloads use the state. Grid cells are drawn where their centre is in the state, so a border cell's total can include a neighbour's detections; the map's sentence says so. "Choose an area" is offered for the whole country only. The whole-country view has a "By state" map (error in steps, refused states hatched and lettered) and a sortable table; each row opens its state. Old links to `region=california` open the state of California and say what changed.

### One conversion for a whole country

The contiguous United States takes in areas whose fires differ in season, in what burns and in the time of day they burn, and the VIIRS:Aqua ratio differs with them. One coefficient per calendar month averages over all of that. The acceptance rule is the same as for every region and it passes (10.4%, 12 months with their own coefficient), but that number describes the country as a whole:

- By calendar month the leave-one-year-out error ranges from 5.9% (February) to 15.7% (October).
- `pipeline/inside.py` applies the national coefficients, fitted without the year being predicted, to this project's California region over the same 174 months: the error is **20.0%** with a bias of +10.0% (18.2% before 2022, 28.9% from 2022), against **15.2%** and +0.9% for California's own coefficients. National k is 6.64 for the year against California's 8.47; in October 5.61 against 8.50. The numbers are in `docs/data/conus_inside.json` and the page states them under "Can I trust the numbers?".
- No other part of the country was measured this way. The California box comes from a separate download and also covers parts of Nevada and Arizona and a strip of Mexico, so the two regions' rows are not an exact subset of one another.

The US downloads overlap the California and Hawaiʻi ones, so they live in `data/raw/usa/` and are only read with `--raw data/raw/usa`; the other regions keep reading `data/raw/` (which is not searched recursively). The static-source mask for this region is built from the US files alone: 7,832 cells of 2 km; checked against the standard record it removes 99.0% of non-fire rows and wrongly removes 4.2% of fire rows.

Times for this region are shown in UTC only. It spans four time zones, and telling which one a point is in needs time-zone boundaries, which the page does not carry; longitude bands would be wrong near every boundary.

## Map grid (pipeline step 4)

`pipeline/grid.py` counts detections on a 0.1° grid (about 11 km north–south) and writes `docs/data/grid/<region>/<year>.json` and `docs/data/grid/<region>/all_years.json`.

- Which detections are inside a region and which are counted comes from `export.detections()`, the same function that sets the `counted` column in the hotspot CSVs: type 0 (or, for near-real-time rows without `type`, outside the static-source mask), low confidence removed. The map, the calendar and the CSV therefore use one rule.
- Each year file holds, per month, every cell with at least one counted detection, with separate counts for MODIS Aqua, MODIS Terra, VIIRS Suomi NPP and VIIRS NOAA-20, split into standard and near-real-time lists. Cells are flat arrays of integers relative to the region's south-west cell. Each file also holds the cells for days 1 to D of the current calendar month, for the month-to-date comparison.
- Before writing, the step checks that the cells add up, per sensor and per month, to `monthly_series.csv`, that the month-to-date cells reproduce the month-to-date numbers in `calibration.json`, and that the all-years cells add up to `monthly_series.csv` over the same years. If any check fails it stops, lists the mismatches and writes nothing.
- `all_years.json` is the map's default view: each cell's total over every complete standard year, per satellite. A year counts for a satellite when all 12 months are complete standard data under `calibrate.usable()`: MODIS Aqua 2003–2025 (23 years, the same years as the calendar's "usual"), Terra 2001–2025, Suomi NPP 2013–2025, NOAA-20 2019–2025 in all four regions. The step checks that these totals equal `monthly_series.csv` summed over the same years. Sizes: contiguous United States 1.25 MB (70,473 cells), California 87 kB, Hawaiʻi 3 kB, Vietnam region 160 kB.
- A point is placed in the cell `floor((lat + 90) × 10 + 10⁻⁶)`, `floor((lon + 180) × 10 + 10⁻⁶)`; the web app bins CSV rows with the same expression.

Sizes (uncompressed JSON; GitHub Pages serves it gzip-compressed, about a third of this): California 1.30 MB for 27 years, largest year 94 kB; Hawaiʻi 0.03 MB; Vietnam region 9.95 MB, largest year about 600 kB (180 kB gzip); contiguous United States 26.3 MB, largest year 1.68 MB.

## Choosing an area

On the map a user can draw a rectangle, or type its west, south, east and north edges. The area:

1. is widened outward to whole 0.1° cells and clipped to the region box (an area wholly outside it is refused);
2. is summed from the grid files: the calendar, the "usual" medians, the seasonal bars and the month-to-date panel are rebuilt from the cells inside it;
3. keeps the region's choice of satellite and data status for every month, and the region's coefficients from `<region>.json` for any VIIRS value converted to the Aqua scale. Where the region's calibration was refused (Hawaiʻi), only MODIS Aqua is shown for the area too;
4. limits the CSV download to rows whose point falls in the area's cells, so the file matches what the calendar counted;
5. is stored in the URL hash (`#region=…&month=…&area=W,S,E,N`) so a view can be shared.

Checked in the browser: with the area set to the whole region box, every rebuilt harmonized value, sensor count, median and month-to-date number equals `<region>.json` for California, Hawaiʻi, the Vietnam region and the contiguous United States (for the last, checked for the four satellites' counts and the harmonized value; values converted in the browser can differ from the file by up to 0.07% because the file publishes k to three decimals).

### Limits of an area

- **The conversion was not validated for the area.** k(m) was fitted and tested leave-one-year-out on the whole region. A smaller area can burn different vegetation, at a different time of day, and its VIIRS/Aqua ratio may differ. The page says this whenever an area is set.
- **Few detections, noisy comparisons.** When MODIS Aqua recorded fewer than **30 detections a year** in the area (mean over complete standard years from 2003), the page warns that the comparison is rough. At that level typical months hold 0 to 5 detections, so one detection more or less moves a month a long way from its usual. The threshold is a judgement, not a fitted value.
- **Cell resolution.** Areas are whole 0.1° cells. Detections are pixel centres; a fire on a cell edge can be counted in the neighbouring cell.
- **VIIRS values on the Aqua scale can differ in the last decimal** from the whole-region values when an area covers the whole region, because `<region>.json` publishes k rounded to 3 decimals. Harmonized values in these regions come from Aqua and are unaffected.
- The region's static-source mask and quality labels are reused unchanged.

## Known limits

- **Hawaiʻi is refused.** 73,595 of 80,102 standard MODIS detections there (91.9%) are type 1 (volcano). VIIRS files give no `type` for near-real-time months, and the static-source mask that replaces it wrongly removes 90.2% of Hawaiʻi's vegetation detections in the in-sample check (California 2.2%, Vietnam region 4.1%). Only Aqua is shown.
- **The conversion is less accurate from 2022.** Monthly-k error rises from 14.0% to 21.2% (California), 10.5% to 15.8% (Vietnam region) and 10.1% to 10.9% (contiguous United States). The coefficients pool 2012–2026 and do not follow the falling VIIRS:Aqua ratio seen in recent Vietnam Novembers.
- **Some calendar months are much less certain than the average.** Leave-one-year-out error by calendar month ranges from 5.4% (September) to 26.1% (December) in California, from 8.2% (February) to 23.9% (July) in the Vietnam region and from 5.9% (February) to 15.7% (October) in the contiguous United States. Only the all-month figures are shown on the page.
- **Near-real-time months are provisional.** Standard data ends 31 Aug 2026 (MODIS) and 31 Jul 2026 (VIIRS). Later months use near-real-time files, which have no `type` column.
- **`<region>.json` publishes k rounded to 3 decimals.** VIIRS values on the Aqua scale recomputed in the browser for a chosen area can differ in the last decimal from the pipeline's values.
- **The static-source mask is built from every file in the raw folder a region reads.** California, Hawaiʻi and the Vietnam region share one mask built from the nine files in `data/raw/` (4,518 cells; 1,415 before the Vietnam files were added). The contiguous United States has its own, built from the three files in `data/raw/usa/` (7,832 cells). Cells are 2 km and the three regions that share a mask do not overlap, so a region's counts are unaffected; the in-region check rates above are per region.
- **Size of the site.** `docs/` is 345 MB in 529 files: hotspot files 305 MB (contiguous United States 160 MB, Vietnam region 120 MB), map grids 38 MB. The largest single file is 10.8 MB (Vietnam region, 2019). GitHub Pages allows 100 MB per file and about 1 GB per site.
- **Hotspot files of the contiguous United States are split by month.** A year would be up to 16.6 MB (2020), read whole to show one day late in the year; the 313 month files are at most 5.5 MB (September 2020) and the newest day needs one of about 0.3 MB. `export.py --hotspots-by-month` writes them and `index.json` lists them (`"split": "month"`); the page reads either layout. The rows are the same as in year files, checked row for row.
- **Vietnam region file sizes.** Its hotspot files total 119 MB compressed (up to 11 MB a year) and its grid 9.95 MB uncompressed. Individual detections and the area download read the year files as a stream; on a slow connection a year can still take a while to arrive.
- **A town's county is the town's, not the detection's.** The nearest town is in a different county than the detection for about 26% of detections in California and the contiguous United States, and in a different district for about 45% in the Vietnam region (`audit/county_check.py`, 2,000 detections per region). The page therefore words it as "17 km north of Shaver Lake (a town in Fresno County, California, United States)". The detection's own county and country are stated only when the Nominatim lookup answers for that point ("The point itself is in ..."), and otherwise not at all. In a check of 40 detections in the United States, the county Nominatim returned was the Census county of the point every time (one differed in spelling). The table shows the town line without a county; the CSV columns are `nearest_town`, `km_to_nearest_town`, `direction_from_town` and `town_is_in`.
- **The nearest town is the nearest place in GeoNames with more than 500 people** (or an administrative seat). In remote country that can be tens of kilometres away, and smaller settlements are not in the list. Distances are great-circle distances to the town's GeoNames point, not road distances.
- **The second place line depends on a shared public service.** Nominatim allows at most 1 request per second for the whole site. The page spaces one reader's lookups, but cannot coordinate readers; with real traffic the lookups need a caching proxy or must be switched off (`NOMINATIM_URL` in `docs/index.html`). A reverse lookup gives the place that contains the pixel centre, which is not always the nearest town.
- **Daily images have gaps.** GIBS has no Suomi NPP true-colour imagery before 24 Nov 2015 and some missing days for every satellite; the page then says so and shows the automatic basemap or no picture.
- **Area limits:** see "Choosing an area" above.

## What NASA ARSET training changed in this project

Lessons the team took from these trainings and where each is applied. ARSET and NASA did not review or endorse this work.

**Fundamentals of Remote Sensing**
- MODIS pixels are about 1 km and VIIRS I-band pixels 375 m, which is why VIIRS records 6 to 8 times as many detections. The ratio is therefore measured per region, not assumed: [pipeline/calibrate.py](pipeline/calibrate.py), "Validation" above.
- Terra crosses in the morning and Aqua in the afternoon, so Terra is never merged into the Aqua scale: it has its own status and a hatched calendar cell ([docs/index.html](docs/index.html), calendar legend "Terra only, not on this scale").
- Sensors saturate on large fires, so detection counts, not fire radiative power, are harmonized ("Metrics" above).
- One ramp with a legend, shared by the calendar and the map, whose lightness rises at every step so it survives greyscale and colour-vision deficiency; the map uses its upper seven steps so they stay visible on satellite imagery ([docs/index.html](docs/index.html), `ramp()` and `mapStep()`).
- Coverage is uneven (clouds, smoke, overpass time), so 0 detections always carries "whether the area could be observed is unknown" ([docs/index.html](docs/index.html), month detail and map summary).

**Monitoring Surface Water with SAR (OPERA DSWx)**
- DSWx-NI, DSWx-S1 and DSWx-HLS share grid, spacing and format so the source stops mattering. Here every sensor is reduced to the same filter, month and 0.1° grid ([pipeline/grid.py](pipeline/grid.py), `export.detections()`).
- DSWx keeps separate codes for not water, masked, cloud and no data. Here statuses stay distinct and are never collapsed to 0: measured, provisional, partial month, not on this scale, not converted, no data from the satellite (`status` in `monthly_series.csv`; `STATUS` in [docs/index.html](docs/index.html)).
- DSWx ships simple, confidence and diagnostic layers. The month detail shows the value, its status, the conversion's tested error for that period and the per-sensor counts, and the same columns are in the monthly table download ([docs/index.html](docs/index.html), `drawDetail()`, `downloadMonthly()`).
- Radar shadow is masked as a known false source. Here the static-source mask removes known non-fire heat and reports its measured hit and false-removal rates ([pipeline/ingest.py](pipeline/ingest.py), trust card on the page).
- NISAR data is released as provisional before validated reprocessing. Near-real-time months are labelled provisional ([pipeline/calibrate.py](pipeline/calibrate.py), `provisional_nrt`).

**NISAR Surface Displacement, part 1**
- Loss of coherence means unknown, not "no movement". A region that fails validation is shown with its numbers and its VIIRS values are left unconverted, not hidden or forced (Hawaiʻi banner and trust card).
- Urgent-response products are faster and less accurate. The page states that trade next to every provisional value (`STATUS.provisional_nrt` in [docs/index.html](docs/index.html)).
- Different products suit different magnitudes. Each region gets its own coefficients; none are borrowed from another region ([pipeline/calibrate.py](pipeline/calibrate.py), run per region).

**Geostationary Remote Sensing of Aerosols**
- Polar-orbiting sensors see a place a few times a day and can miss short fires between passes. Geostationary fire detections are named as future work only; this version does not use them.

## Use of AI

AI tools were used in this project. See [AI_USE.md](AI_USE.md).

## How to run

Standard library Python 3 only. FIRMS archive downloads go in `data/raw/` (not committed). For each region:

```sh
python3 pipeline/ingest.py    --raw data/raw --out data/processed/california --bbox -124.5 32.5 -114.0 42.0
python3 pipeline/calibrate.py --region data/processed/california
python3 pipeline/export.py    --id california --name "California" --bbox -124.5 32.5 -114.0 42.0
python3 pipeline/grid.py      --id california --bbox -124.5 32.5 -114.0 42.0
python3 pipeline/places.py    --id california --bbox -124.5 32.5 -114.0 42.0   # needs the GeoNames files in data/raw/geonames/
```

`export.py` also writes `docs/data/<region>_daily.json` (counted detections per day, per satellite and data quality; 42 to 169 kB). It stops and writes nothing if the days do not add up, per satellite and per month, to `monthly_series.csv`. `--skip-hotspots` rewrites only the two summary files without reading `data/raw/` again.

Hawaiʻi uses `--bbox -160.6 18.7 -154.5 22.5`; the Vietnam region `--bbox 102.1 8.4 109.5 23.4`.

The contiguous United States reads its own folder of country downloads and writes its hotspot files by month:

```sh
python3 pipeline/ingest.py    --raw data/raw/usa --out data/processed/conus --bbox -125.0 24.4 -66.9 49.5
python3 pipeline/calibrate.py --region data/processed/conus
python3 pipeline/export.py    --id conus --name "Contiguous United States" --bbox -125.0 24.4 -66.9 49.5 --raw data/raw/usa --hotspots-by-month
python3 pipeline/grid.py      --id conus --bbox -125.0 24.4 -66.9 49.5 --raw data/raw/usa
python3 pipeline/places.py    --id conus --bbox -125.0 24.4 -66.9 49.5
python3 pipeline/inside.py    --large data/processed/conus --small data/processed/california   # California test box inside the national fit
python3 pipeline/states.py    --raw data/raw/usa --bbox -125.0 24.4 -66.9 49.5                   # the 48 states and DC; needs data/raw/census/cb_2023_us_state_5m.zip
```

The web app is the static folder `docs/`: `python3 -m http.server -d docs 8000`, then open http://localhost:8000. Besides its own files it requests Leaflet from cdnjs, on a reader's action a place name from Nominatim and a day's image from NASA GIBS or Worldview Snapshots, and basemap tiles: NASA GIBS (Blue Marble with coastline, border and label overlays) up to zoom 8, and from zoom 9 Esri World Imagery with Esri's reference labels (its two libraries load from jsDelivr only then), falling back to OpenStreetMap if Esri is unavailable. No FIRMS or other data API is called from the page.

The `ESRI_API_KEY` in `docs/index.html` is a public basemap key: ArcGIS Location Platform, basemap privileges only, restricted to the referrers https://nguyenhuulong2222.github.io and http://localhost. It is meant to be shipped in a web page and is not a secret. Leave it empty and the page uses OpenStreetMap at close zoom.

### Reading the page

- Page order: title, map, "What you are looking at", the detections table, "Fire activity over time", the full record (the month-by-year calendar), how far to trust it, downloads, method and sources.
- **Where the page opens.** With no time in the address, the page opens on the most recent day that has at least one counted detection in the harmonized view, drawn as individual detections with the map fitted to the region, with that day's table and the daily bars of its month. A link with its own selection wins; `view=all` in the address means all years. Because the conversion is tested by month, the day view also states the month on the MODIS Aqua scale against the usual (for the current month, the month-to-date numbers), with a link to the whole month. A day with fewer than 10 detections is called quiet in words, with jumps to the busiest day of the year and of the record; "quiet season" is said only when that calendar month's usual is under a quarter of the busiest month's.
- **One selection.** All years, one year, one month or one day. The map, the timeline, the charts, the calendar and the page address (`#region=…&year=…`, `&month=…` or `&day=…`) all read and write it through one function, `select()`.
- **What you are looking at** is generated for the selection from the same series as the calendar: what a square is, the count with its unit and how it compares with the usual, and what the colours mean. A refused region (Hawaiʻi), provisional months and incomplete periods get their own sentences. A "How to read this" box defines each term once.
- **Fire activity over time** drills down: a bar per year (hatched when the year lacks twelve months of final data), then twelve monthly bars over the lowest-to-highest band and median of final data since 2003 (the same "usual" as the calendar), then daily bars from `<region>_daily.json`. Daily bars show one satellite as recorded; where VIIRS is converted it appears as dots labelled "indicative: tested by month, not by day", because the conversion was validated on monthly totals only. Daily counts are for the whole region, also when an area is chosen. Every bar is a button with its value in words; a table gives each satellite's daily counts.
- **A day on the map** is drawn as individual detections from that year's hotspot file (that month's, for the contiguous United States), loaded on demand, with the 4,000-square cap.
- **A year on the map** adds up the year's months on a scale fixed across years (`max_cell_year` in the grid index).
- **Play** steps at the level of the selection (years, months or days) at slow, normal or fast speed. On the day the page opens on by itself, the first Play starts at day 1 of that month and runs to the last day with data; after that, or after any choice, it carries on from the current step. It never starts by itself, waits for each frame to be drawn instead of skipping, preloads the next grid file, keeps the colour scale fixed, stops at the last step, and is paused by any choice on the timeline, calendar, charts or map. Screen readers hear "Playing" and "Paused", not every frame. Space toggles it while the slider has focus.
- **Place names, two lines.** Line 1 is the nearest named town, worked out in the browser from a GeoNames list bundled per region (`docs/data/places/<region>.json`, built by `pipeline/places.py`): "17 km north of Shaver Lake, Fresno County, California, United States". The distance is to the nearest kilometre under 100 km, and the direction is the eight-point compass direction from the town to the detection. It needs no network, so it always shows, on cards, in the table's Place column, in the report and in the day CSV (`nearest_place`, `distance_km`, `direction`). The name shown is GeoNames' ASCII name, with its main name in brackets when written differently. Line 2, "Nearest named feature", is what one OpenStreetMap Nominatim lookup at its finest zoom returns near the pixel centre (a road or track, a hamlet or locality, a lake or park when OpenStreetMap names one): one lookup per opened detection, one at a time and at least 1.1 s apart, kept in memory, never in bulk. After 3 s, or on failure, line 2 says it is unavailable; when nothing finer than the county comes back there is no line 2. House numbers, shops and buildings are never shown. Coordinates are given in decimals and in degrees, minutes and seconds. Both lines describe the centre of the satellite pixel, not the exact spot of the fire. Nominatim's limit is 1 request a second for the whole site, which a static page cannot enforce across readers (see Known limits).
- **NASA image of the day.** With a day selected, the basemap can be "NASA satellite image of this day": GIBS daily true-colour imagery from the satellite shown on the map, for that UTC date (MODIS about 250 m per pixel, VIIRS about 375 m). The card and the report show a picture of the area from NASA Worldview Snapshots with the detection ringed, and a link that opens that day in NASA Worldview with the satellite's fire layer on. The page says what such an image can show (smoke, cloud, burn scars; not flames; cloud may hide everything) and says in words when there is none: Suomi NPP imagery in GIBS starts on 24 Nov 2015, so its 2012 to 2015 detections have no picture.
- **Report for one detection.** "Report for this place and day" on a card builds a page section from this project's files only: where and when; what each of the four satellites recorded within 5 km on that UTC date (pass times, detections, counted, highest and total fire radiative power; a satellite with no detection is not shown as zero fire); the first and last date with detections within 5 km in the 30 days before and after, with a daily bar chart for the detection's satellite; the month's harmonized total for the region against the usual; the image of the day; and the limits. It prints on one A4 page, downloads its detections as CSV, and has its own address (`#region=…&day=…&report=lat,lon,SATELLITE,HHMM`). Distances are measured from the position in the address (4 decimals), so a reopened report gives the same numbers. It is not an official incident report and names no cause.
- **Selecting a detection moves the map to it.** The map flies to zoom 11 (it jumps without animation under reduced motion), the detection is ringed, and its card is docked beside it: on the right on a wide screen, as a sheet along the bottom on a phone, with the point centred in the part of the map left free. The card's first row is the Place: the town line in bold, the admin area, the country on its own line, the nearest named feature, and a small locator showing where the point is in the region box. "Back to the whole region" returns to the view before the card opened. In the detections table, Place comes right after the time.
- **The harmonization result comes first.** The title and a one-line result at the top of the page, and a band directly under the map, give for the selected region three measured steps: VIIRS counts taken as they are, one whole-year ratio, and a factor for each calendar month (each tested on years left out, with the periods before and from 2022 and the range of the monthly factors), beside a small chart of VIIRS as recorded, VIIRS converted and MODIS Aqua for the complete years both watched (2013 to 2025). A refused region says "Not harmonized" and why in the same place. Every figure is read from `docs/data/<region>.json`; none is typed into the page. The map and timeline take about 52% of the window so the band is on the first screen of a desktop window; on a phone the one-line result is at the top and the band follows the timeline.
- **What the record contains.** The band and the calendar say it in one sentence built from the data: from July 2002 the record shown is MODIS Aqua, and no month of it is converted; converted VIIRS runs beside it from 2012 as the tested successor. A switch above the charts and the calendar, "MODIS Aqua record" / "VIIRS-only record (as if Aqua had ended)", rebuilds the calendar, its usual months and the charts from converted VIIRS alone (Suomi NPP from February 2012 while it has standard data, NOAA-20 after). Selecting a month then gives its difference from what Aqua recorded, and the forward-test result (factors fitted to 2018, tested on later years) is shown beside the switch. The map and the sentences above it stay on the Aqua record. `record=viirs` in the address keeps the choice.
- **Compare regions.** The trust section ends with one table of all four regions, tested the same way, and California with the national factors (from `docs/data/conus_inside.json`); each number links to the file it is read from.
- **Panels.** On a wide screen the Layers panel and the legend start collapsed when they would lie over the region box as first framed (for example the United States in a tall window); once the reader opens or closes one it is left alone.
- **One detection.** Selecting a square (a day, or a month at zoom 9 and closer) opens a card: the time of the satellite pass in UTC and in the region's local time (America/Los_Angeles, Pacific/Honolulu, Asia/Ho_Chi_Minh; UTC only for the contiguous United States, which spans four time zones), latitude and longitude to 4 decimals with Copy and a link that opens that point at zoom 14, the satellite and sensor, day or night, FIRMS confidence, fire radiative power in MW, data quality, and whether it was counted and, if not, why (a FIRMS type other than vegetation fire, low confidence, or a place in the static-source mask). On a phone the card opens as a sheet over the map.
- **The detections table** under the map lists a day's detections ("Detections on <date>"), the detections in view when a month's individual detections are on, or the detections behind one grid cell (select a cell in a month, then "Show the detections in this cell"). It sorts by time and by radiative power, shows 200 rows at a time, highlights a row's square on the map, and downloads its rows as CSV with the local time added. The table and the download hold every row even when the map's 4,000-square cap hides some; the page says so. It lists the satellite shown on the map.
- **What the time and place mean** is stated beside the card and the table: the time is the satellite pass, not the fire's start, and each satellite passes about twice a day; the position is the pixel centre (about 375 m for VIIRS, 1 km for MODIS, larger at the swath edge); dates on the page are UTC dates, so a local evening can fall on the neighbouring date.
- **Reaching a day.** In a month, Days selects the month's busiest day for the satellite on the map, and a daily bar selects that day; both move the map to where the day's detections are.
- **Where and when it burned most.** Directly under the timeline, for the period, satellite and region or state on the map, with no further click:
  - *Top areas.* An area is a square of 7 by 7 grid cells (about 77 km) placed where it holds the most detections; the next area is found the same way among the cells that are left, so areas never overlap. Each has its count, its share of the detections on the map, and its first and last day with detections (a month) or first and last month (a year); for all years no dates are given. It is named after the nearest town in the bundled list to where its detections centre, worded as the town's county. The same areas are numbered on the map.
  - *Top days* by counted detections, from the daily counts, each with the area that held most of that day's detections.
  - *One sentence on the season:* the fewest calendar months that together hold at least half of a year's (or all years') detections; for a month, the share of its listed busiest days.
  - For a single day the list is the top places of that day.
  - **How many are listed.** "Show: 5 | 10 | 20" sets the length of both lists (10 by default for the whole United States, 5 elsewhere; a choice is kept while the page is open). The numbered markers and the preview card's Previous and Next follow it. Under the areas one line gives the share of the period's detections that the listed areas hold together and how many lie outside the list, for example 36.2% for the top 20 areas of the United States in 2021. Markers get smaller as the list grows, and numbers that would overlap at the current zoom are drawn as one marker ("5+3": area 5 and three more) that opens the first of them; zooming in separates them.
  - **Review before anything moves.** Selecting an area or a day in the lists, or a numbered marker on the map, opens a preview card and does nothing else: no zoom, no scroll, no table. For an area the card gives its rank and name, the period, detections and share, first and last day with detections, the busiest day with its count, the highest fire radiative power, the counted detections of each satellite there, and a small bar chart (each day of a month, or each month of a year). For a day it gives the date, its detections, the area with the most that day, and how the day compares with the usual daily average of that calendar month. Only the card's buttons move the page: "Zoom to this area", "List its detections" (opens the table and scrolls to it), "Open the busiest day" (or "Open this day"), and "Close"; Previous and Next step through the five without closing it. The row of the open card is highlighted and so is its marker; pointing at or focusing a row highlights its marker; Esc closes the card and returns focus. On a phone the card is a sheet at the bottom of the screen with the same buttons.
  - The card appears at once with what the grid and the daily counts already give; days, radiative power and the chart come from the hotspot file and fill in after it opens. For a year they are loaded only when the year's files are 12 MB or less (otherwise the card gives months and offers "Open the busiest month"); for all years the card gives counts per satellite only and says that dates need a year or a month. Both lists are tables, so a keyboard and a screen reader reach the same information.
  - Areas and days come from files the view already has (grid, daily counts, places). Dates inside a month and the busiest area of a day need a hotspot file; it is fetched after the first paint with a "Loading" state, never while playing, and not at all when it would exceed 12 MB (the Vietnam region's year files over all years), in which case the row says to select the day.
  - The wording keeps the limits: these are the places and days with the most satellite detections, not a ranking of fires by size or damage. A refused region or state says the counts are MODIS Aqua's own, as recorded.
  - On screens 1100 px and wider the section sits beside the harmonization result, directly under the timeline, so both start on the first screen; on narrower screens it follows the harmonization result.
- **One satellite instead of the harmonized view** is named in a one-line chip beside the Layers button ("VIIRS NOAA-20, as recorded · Back to harmonized"), which can be dismissed. It says more only when a link set the satellite. Changing region or state returns to the harmonized view.
- **Going straight to a date.** Beside the slider a "Go to" control fits the level: a Year list, a Year and a Month list, or a Date field (a native date input limited to the record's first and last day, so a date can be typed or picked). It drives the same selection as the slider, the calendar and the charts, and pauses play. A date that is not a date, or lies outside the record, gets a sentence beside the control ("The record for this state runs from … to …") and the map stays where it was. The current value stays available as text for screen readers and in the large label shown while playing. On a phone the control has its own row of the timeline; the map keeps its height.
- **Finding a month or a day.** The timeline has a Days | Months | Years | All years switch. Days goes to the busiest day of the selected month or year, or from All years to the most recent day with data; Months goes to the selected year's first month with data, or from All years to the latest month. When a year is selected, its twelve months are a row of buttons under the map.
- **Satellite.** The harmonized view is the default. When a link or the Layers panel sets another satellite, the map says so ("Showing VIIRS S-NPP as recorded, not converted") with a button back.
- **Empty states** are in words on the map, from documented dates rather than from the files: "had not been launched" (with the launch date), "in orbit, but FIRMS has no fire data from it before ...", "no data received yet for this date" after the last row of a download, and "stopped delivering new data" only for Suomi NPP, which FIRMS states. Each is kept apart from "has data for this period but recorded no detection", which is never called no fire. A button leads back to the harmonized view.

### Map display

- The map opens on the **most recent day that has a counted detection**, drawn as individual detections; the Days | Months | Years | All years switch on the timeline changes the level, and All years shows the total over every complete year.
- Colours: one fire ramp for the calendar and the map, low to high: deep maroon, red, orange, yellow (`FIRE` in `docs/index.html`). Lightness rises at every step (L* 14 to 92), and still does under simulated protanopia, deuteranopia and tritanopia (Machado et al. 2009 matrices); every step carries white or near-black text at 4.5:1 or better. Calendar cells keep their printed numbers, and provisional, partial, Terra-only and refused keep their borders, hatching and wording, so nothing depends on colour alone.
- Map cells use the upper seven steps of that ramp on the same log scale: the darkest steps disappear on the dark satellite imagery. Opacity rises with the step, from 30% for the lowest to solid for the highest (`STEP_OPACITY`), so the basemap shows through where there were few detections and busy areas stand out; the legend swatches are drawn the same way. For a year or all years, the explanation states that a coloured square means at least one detection in the period, the measured share of squares in the faintest step, and the count half of them stay under.
- Individual detections are red squares with a dark edge; detections that were not counted are hollow dashed squares. The legend lists the count range of each step, worked out with the same function that colours the cells.
- Cells are drawn without gaps, each colour step at its own opacity, so coastlines and terrain show through the fainter ones. All cells of a view are painted on one canvas layer rather than as one Leaflet rectangle each. Measured in Chrome at 1440×900 with the 55,462 cells of the contiguous United States, all years: 233 ms per draw and 173 ms per zoom step before, 28 ms and 26 ms after; the Vietnam region's 7,763 cells went from 40 ms to 18 ms. Pointing at a cell or tapping it outlines the cell and shows its count, so no value is given by colour alone; the busiest areas are listed in words in "Where and when it burned most".
- Outside the region box the map is dimmed slightly; nothing is drawn there.
- Layout: the map sits at the top of the page, full width, with the timeline along its bottom edge (about 52% of the window together, so the result band below is on the first screen). "Expand map" fills the window with the browser's Fullscreen API, or with a fixed-position fallback where that API is missing (iPhone Safari); Esc or "Close full screen" returns.
- The timeline steps at the level of the selection: years (with an "All years" position), the months of the record, or the days of a month, with Play, a speed choice, and buttons for the next coarser step. It and the calendar and charts drive the same selection, so each moves the others.
- The Layers panel (top left) holds the basemap choice, the satellite switch, grid cells or individual detections, and the region outline. The legend (bottom right) gives the colour steps and units; a scale bar and the latitude and longitude under the pointer (or of the map centre) are at bottom left.
- Individual detections are drawn as squares of the sensor's nadir footprint, about 1 km for MODIS and 375 m for VIIRS, never smaller than 5 pixels.

## License

Code (the pipeline, the audit scripts and the web page): **Apache License 2.0**, Copyright 2026 the Kahu Ahi team. See [LICENSE](LICENSE).

Data in `docs/data/` and `data/processed/` are not covered by that licence:

- fire detections and everything counted from them: NASA FIRMS data, open with the acknowledgment in [SOURCES.md](SOURCES.md);
- `docs/data/places/*.json`: derived from the GeoNames gazetteer, Creative Commons Attribution 4.0.

Third-party libraries and services, with their licences and terms: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Acknowledgments

Fire data: NASA FIRMS. The official FIRMS acknowledgment statement is reproduced in [SOURCES.md](SOURCES.md). This project is not endorsed by NASA.
