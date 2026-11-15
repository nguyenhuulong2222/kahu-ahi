# Audit of Kahu Ahi before submission

Audited: commit `0deb160` (14 Nov 2026). Nothing under `pipeline/` or `docs/` was changed by this audit.

How it was done:

- `audit/recompute.py` reads the twelve raw FIRMS zips and rebuilds the numbers from the rules as README.md states them. It imports nothing from `pipeline/`. Results: `audit/out/recomputed.json`, differences: `audit/out/differences.json`, monthly counts: `audit/out/<region>_monthly.csv`.
- `audit/county_check.py` samples 2,000 detections per region and locates each one, and its nearest town, in boundary files the project does not use (US Census counties; geoBoundaries districts).
- The page text, README.md, SOURCES.md, AI_USE.md, THIRD_PARTY_NOTICES.md, LICENSE and data/manifest.json were read against each other and against the JSON files. Part of that read (claims against sources, licences) was done by a second reviewer working only from the files; items taken from that read and not re-checked here are marked "(read, not re-checked)".

## Follow-up: what was fixed, and what remains

Written after the fixes of 14 Nov 2026 (commits `151bf3e` to `8cd692a`). The audit below is left as it was written, against commit `0deb160`; where a figure in it has since changed, this section says so.

Re-checked after the fixes: `audit/recompute.py`, updated for the rules README now states and for the as-used chain, reproduces every monthly count, coefficient, error figure, as-used figure, adoption decision and month-to-date figure in all four regions with **zero differences** (the three one-detection differences of B6 are gone now that the mask-cell rule is written down). The page was checked in a browser at 1440×900 and 390×844 on all four regions, each new figure against its JSON value, console clean.

### Fixed

| Finding | What was done | Commit |
|---|---|---|
| A1 as-used error | `calibrate.py` now measures the chain the page uses and writes it to `calibration.json` and `<region>.json` (`as_used`): NOAA-20 standard against Aqua standard on held-out years, with Suomi NPP factors and with NOAA-20's own; and NOAA-20 near-real-time against Aqua for every complete month. The acceptance rule is applied to the chain as used; a failing region's recent converted values would read "not reliable" (none fails today). The as-used error is shown in the band, in "This month so far" and in the month detail. | `151bf3e` |
| A2 what the record contains | The band and the calendar state that the record from July 2002 is MODIS Aqua and that no month is converted. A switch rebuilds the calendar and charts as a VIIRS-only record, with each month's difference from Aqua and the forward-test result beside it. Lede changed to match. | `2b8e862` |
| A3 baseline | The band, the one-line result and the comparison table show three measured steps: as recorded, one whole-year ratio, monthly factors. | `91ea98c` |
| B1 county | The town's county is worded as the town's ("a town in ..."). The point's own county and country come only from the Nominatim answer, otherwise they are not stated. CSV columns renamed. | `ba06d94` |
| A5 "not flying" | Replaced by documented launch and first-data dates (NASA Science pages, FIRMS FAQ), "no data received yet for this date" after a download's last row, and "stopped" only for Suomi NPP, which FIRMS states. | `d7b26d3`, `8cd692a` |
| A6 Aqua drift | NASA's own account is cited (last drag make-up manoeuvre December 2021, free drift since, about +50 minutes by January 2025). The page gives it as the reason for the 2022 split and no longer suggests a cause for the higher error. | `ba72f1e` |
| A4, B6, B7, B9, parts of B5, B8, C | TBD lines resolved; status line final; four regions throughout; file sizes and periods corrected; reproduction rules added to README; licence named with what it does not cover; Esri and the licence in the footer; template text removed; "nominal" confidence; Hawaiʻi wording; image resolution wording; California-inside-the-fit stated as a lower bound with three independent areas. | `578d7db` |

### Numbers that moved, and why

Item A1's test adopted NOAA-20's own factors where they had the lower error on held-out years: the Vietnam region (13.2% against 13.4%) and the contiguous United States (10.4% against 10.8%); not California (15.6% against 14.6%). The gains are small. Everything that moved:

- NOAA-20 values on the Aqua scale, 104 months (April 2018 to November 2026), in the Vietnam region and the contiguous United States (`noaa20_aqua_equiv`, `n20_eq`).
- Month-to-date estimate: Vietnam region 98.8 → 115.1 (years below: 8 → 9); contiguous United States 1,880.7 → 1,783.5.
- The October 2026 differences quoted in A1 are now +26.1% (United States, was +39.1%) and −30.2% (Vietnam region, was −33.8%); September: −7.2% and −10.5%.

Nothing else moved: no count, no Suomi NPP coefficient, no figure of the validation table, nothing in California or Hawaiʻi.

Measured as used (from `calibration.json`):

| Region | NOAA-20 standard, held-out years | Near-real-time, Aug–Oct 2026 | Worst near-real-time month |
|---|---:|---:|---|
| California | 14.6% | 9.6% | August, −14.5% |
| Vietnam region | 13.2% | 26.1% | August, −39.5% |
| Contiguous United States | 10.4% | 6.3% | October, +26.1% |

Factors fitted on near-real-time data could not be tested on held-out years: there are three such months, all in 2026. A single near-real-time ratio tested by leaving one month out gave 11.4%, 10.5% and 15.8%; it is reported and not adopted.

### County check, re-run

The town named on the card is in a different county or district than the detection as often as before (California 26.6%, United States 25.8%, Vietnam region 45.2%, Hawaiʻi 0%); that is geography, not a defect, and the card now says whose county it is. The rate at which the card attaches a town's county or country to the detection is zero by construction. For 40 sampled detections in the United States, the county Nominatim returned for the point was the Census county every time (one spelled "Saint" for "St.").

### Remains

- **A2, partly.** The VIIRS-only record covers the calendar and the charts. The map and the sentences above it stay on the Aqua record, and the page says so.
- **A1, limits.** Three near-real-time months are a thin basis; the figure will move as months are added. The first screen at 1440×900 holds the three figures and the chart, but the explanatory lines under the third figure and the as-used sentence run below the fold.
- **B2.** Hawaiʻi's near-real-time months are still shown as provisional counts although the mask removes nearly every row there.
- **B3.** One afternoon pass over Hawaiʻi is still split across two UTC dates.
- **B4.** The mask check on the page is still the in-sample one; the out-of-sample figures are only in this file.
- **B5.** The national fit was not re-run without California; the 20.0% is stated as a lower bound.
- **B8.** Not done: DOIs for the FIRMS products; URLs and dates for the four ARSET trainings; a source for "sensors saturate on large fires"; a source for the image resolutions; the team's GOES-18 Lahaina analysis is still referred to without a source.
- **B9.** AI_USE.md does not say how `pipeline/ingest.py` and `pipeline/calibrate.py` came to be; that is for the team to state. Esri's attribution guidance was still not opened.
- **SOURCES.md, "Other projects consulted".** Filled with what is known to have been looked at (NASA Worldview and the FIRMS map, for layout). The team should confirm nothing else was read.
- **Cosmetic.** Hawaiʻi's percentages of very small numbers; "1 detections".
- **To watch.** NASA's Aqua page calls the mission active and the downloads hold Aqua rows to 13–14 Nov 2026. A search result, not opened, described a NASA status document from May 2025 that planned to end Aqua's mission in late 2026. If Aqua has in fact stopped, "Aqua still has data" needs rewording and the VIIRS-only record becomes the main one.

## Summary

The arithmetic is sound. An independent recomputation from the raw files reproduces every coefficient, every error figure and every month-to-date figure in all four regions, and 3,556 monthly counts with three differences of one detection.

The weak points are in what the numbers are taken to mean, not in how they are computed:

1. The error shown as the result (10.4% to 15.2%) is measured on a chain that the page never uses. Where the conversion is actually used (NOAA-20 near-real-time against Aqua near-real-time), the latest complete month is off by 39% in the United States and 34% in the Vietnam region.
2. The "harmonized" calendar contains no converted value at all. Every month from July 2002 is a MODIS Aqua count.
3. The headline pairs the error with a baseline nobody would use (VIIRS counts taken as they are, 525% to 747%). Against one whole-year ratio the monthly method gains 3.8 to 4.8 points in California and the Vietnam region.
4. A detection card names a county that is not the detection's county about one time in four in the United States, and a wrong district about 45% of the time in the Vietnam region.
5. SOURCES.md still has two `TBD` lines, README says "Status: in progress", and several statements still say "three regions".

---

## A. Would cost points with a judge

### A1. The reported error is not the error of the conversion as the page uses it

**Evidence.** The validated chain is S-NPP standard data against Aqua standard data, each year predicted from the other years. The page uses the coefficients on something else: NOAA-20 near-real-time counts (no `type` column, filtered by the static-source mask, used 1:1 for S-NPP) to estimate Aqua for current months. That chain can be checked directly for the two complete near-real-time months in the files, and README does it only for California and the Vietnam region. From `audit/out/recomputed.json`, `conversion_as_used_nrt_months`:

| Region | Month | Aqua NRT | NOAA-20 NRT ÷ k(m) | Difference | Error shown on the page |
|---|---|---:|---:|---:|---:|
| California | Sep 2026 | 263 | 258.9 | −1.6% | 15.2% |
| California | Oct 2026 | 227 | 230.3 | +1.4% | |
| Vietnam region | Sep 2026 | 461 | 373.0 | −19.1% | 12.0% |
| Vietnam region | Oct 2026 | 755 | 499.8 | −33.8% | |
| Contiguous United States | Sep 2026 | 2,365 | 2,262.2 | −4.3% | 10.4% |
| Contiguous United States | Oct 2026 | 2,917 | 4,056.4 | **+39.1%** | |

The US October figure is not caused by missing Aqua days: Aqua has rows on all 31 days (`data/processed/conus/daily_counts.csv`). This October's NOAA-20:Aqua ratio is 7.79 against k(10) = 5.605, outside the yearly range the project itself publishes for October (3.98 to 7.37). The Vietnam figures are in README; the US one is nowhere in the repository.

The forward test (fit to 2018, predict later years) is closer to real use than leave-one-year-out and is worse where it matters: 22.8% from 2022 in California and 18.1% in the Vietnam region, against 15.2% and 12.0% shown. It is in README and `calibration.json` but not on the page (no occurrence of "forward" in the page's text).

**Why it matters.** The band under the map reads "After conversion, tested on years left out: 10.4%" for the United States, on the same screen as a month-to-date estimate made by the chain that was 39% off last month.

**Fix.** Add to each region's JSON, and show beside the tested error: (a) the forward-test error, (b) the difference between NOAA-20 ÷ k and Aqua for each complete near-real-time month. Word the headline as "tested on past years of standard data", and say that current months are estimated with a different satellite and provisional data.

### A2. The harmonized record contains no VIIRS

**Evidence.** In `docs/data/<region>.json` every month from 2002-07 has `src: "MODIS_AQUA"` in all four regions; README line 65 says so ("every calendar month from July 2002 is an Aqua count"). The conversion feeds only the month-to-date estimate and the "on the Aqua scale" columns. The page title is "one fire record across MODIS and VIIRS" and the band says "One record: MODIS Aqua where it has data, VIIRS divided by its month's factor elsewhere" — but "elsewhere" is empty today.

**Why it matters.** The challenge is about carrying the record across the MODIS-to-VIIRS transition. A judge who opens the calendar is looking at an Aqua record with a tested conversion standing by. That is a defensible position (it is what one would do while Aqua still flies), but the page should say it rather than leave it to be found.

**Fix.** State on the page that no month of the calendar is converted yet, and show what the record would look like if Aqua had stopped: a second calendar or a toggle built from VIIRS ÷ k for 2012 onward, with the months where it disagrees with Aqua marked. That is the harmonized product the challenge asks for, and the data for it (`snpp_eq`, `n20_eq`) are already in the JSON.

### A3. The headline baseline flatters the result

**Evidence.** The band's first figure is the error of using VIIRS counts unchanged (California 747.1%, Vietnam region 524.7%, United States 563.8%), followed by the monthly-factor error. Nobody would use a 375 m sensor's counts as a 1 km sensor's. The meaningful baseline is one ratio for the whole year, which the project measures:

| Region | VIIRS unchanged | One annual ratio | Monthly factors | Gain of monthly over annual |
|---|---:|---:|---:|---:|
| California | 747.1% | 19.0% | 15.2% | 3.8 points |
| Vietnam region | 524.7% | 16.8% | 12.0% | 4.8 points |
| Contiguous United States | 563.8% | 28.2% | 10.4% | 17.8 points |

(Recomputed; equal to `calibration.json`.) The annual figure is in the trust section's bars but not in the band, the one-line result or the "Compare regions" table.

**Fix.** Put the annual-ratio error in the band and the table. The US row is the strongest evidence that calendar-month factors matter; the other two are modest and should be shown as such.

### A4. Unfinished and stale text a judge will see first

- SOURCES.md:44 `TBD — add any further paper actually used.` and SOURCES.md:59 `TBD — list any repository or project read for reference, with URL and what was taken from it.` The file opens with "Every source used in this project is listed here". Fix: a real entry or "None."
- README.md:7 `Status: in progress ... Sections marked TBD are filled only with measured results.` Fix: final status and date.
- README still describes three regions: line 65 "In all three regions Aqua is still flying"; line 131 "in all three regions"; line 146 (the area check lists three regions; the US check was done but is not recorded there); lines 159–160 give errors for two regions; line 163 says the mask "is built from every file in `data/raw/`" with 4,518 cells "shared by all regions", which contradicts line 120 (the US mask is separate, 7,832 cells).
- THIRD_PARTY_NOTICES.md:30 lists the GeoNames places for three regions; `docs/data/places/conus.json` (25,032 places, by far the largest redistribution) is not mentioned. (read, not re-checked)
- README.md:266 says the map and timeline take "about 70% of the window"; README.md:247 and the page's CSS say 55%. A CSS comment at docs/index.html:75 still says 70%.

### A5. "Not flying" is inferred from the first and last row of a file, and is wrong for real dates

**Evidence.** `flyingOn()` and `sensorSpan()` (docs/index.html:662–667) take a satellite's span from the first and last row in this region's files. The messages built from it (docs/index.html:1789–1790) are "was not flying yet" and "was no longer sending data ... Its record here ends on ...".

- In California, Hawaiʻi and the Vietnam region the last Aqua near-real-time row is 13 Nov 2026 while `data_through` is 14 Nov (`docs/data/*.json`, `sensors`). Selecting 14 Nov in the harmonized view therefore says MODIS Aqua "was no longer sending data". Aqua has not stopped; the last day of a download is incomplete. (Derived from the code and the data; not observed in a browser.)
- Suomi NPP's last row is 1 Nov in the Vietnam region and 2 Nov elsewhere, so the page gives two end dates for the same satellite.
- Before the first row, the page says "not flying yet" for periods when the satellite was in orbit: the S-NPP record starts 20 Jan 2012 and NOAA-20's on 1 Apr 2018, while the page's own image table gives NOAA-20 imagery from 5 Jan 2018.

**Fix.** Say "no data in this record" instead of "not flying" and "no longer sending data". Treat days after the last row but within `data_through` as "not yet in the download". Keep "stopped" for Suomi NPP only, with its source.

### A6. Aqua's orbit drift is stated as fact, with no source, and the 2022 split is the team's own

**Evidence.** docs/index.html:1137: "Aqua's orbit has been drifting toward later in the afternoon in recent years, which may be part of the reason; this record cannot confirm it." Only the causal link is hedged. README.md:42 says the 2022 start "has not been checked against NASA documentation"; `pipeline/calibrate.py:43` says "to be verified". No entry in SOURCES.md is cited for the drift, its direction or its start. The split appears on the page as "2012 to 2021" and "from 2022" with no note that 2022 was chosen by the team.

**Fix.** Cite a NASA document for the drift and its timing, or reword to "we split the test at 2022, our own choice". Then remove "not checked" and "to be verified".

---

## B. Should fix

### B1. The card names the nearest town's county, not the detection's (confirmed and sized)

**Evidence.** `nearTown()` prints the administrative names attached to the nearest GeoNames place. `audit/county_check.py`, 2,000 detections per region drawn at random from `docs/data/hotspots/` (seed in the script), detection and town both located in the same boundary file:

| Region | Both located | Different county or district | Share (95% interval) | Card names another country | Median distance to the town |
|---|---:|---:|---:|---:|---:|
| California | 1,977 | 526 | 26.6% (24.7–28.6) | 2 | 18.1 km |
| Contiguous United States | 1,989 | 514 | 25.8% (23.9–27.8) | 8 | 13.5 km |
| Vietnam region | 1,993 | 901 | 45.2% (43.0–47.4) | 87 (4.4%) | 16.2 km |
| Hawaiʻi | 1,950 | 0 | 0% | 0 | 7.1 km |

In the United States the printed county or state name differs from the Census county of the point in 532 of 1,989 cases (26.7%). Hawaiʻi is unaffected because its counties are whole islands. In the Vietnam region the card also names the wrong country for about 1 detection in 23 (a town across a border is nearer). Examples with coordinates are in `audit/out/county_check.json`.

Limits of this estimate: the Vietnam-region boundaries are the simplified geoBoundaries files (2014 to 2020 vintages, before Vietnam's 2025 reorganisation), so points close to a boundary can be misplaced; the US file is 1:500,000. The sample is of all detections, counted or not.

**Fix.** Print the town line without its county ("22 km south-east of Wimauma, Florida"), or label it "nearest town: Wimauma (Hillsborough County)". If the point's own county is wanted, bundle a county boundary file (the Census file is public domain) or use the county Nominatim already returns for the point.

### B2. Near-real-time months in Hawaiʻi are decided by the mask

**Evidence.** For Hawaiʻi the mask removes 118 of 120 Aqua near-real-time rows and 1,664 of 1,678 NOAA-20 rows. Aqua counted detections for Sep, Oct and 1–13 Nov 2026 are 2, 0 and 0 with the mask and 43, 33 and 44 without it. In the standard record the mask removes 90.2% of rows typed as vegetation fire there (73.8% when built without 2024 onward and tested on 2024 onward). So "This month so far: 0" for Hawaiʻi means "nothing outside the masked cells", and a vegetation fire inside them would not be counted. README says the conversion is refused for this reason; the page still shows these near-real-time Aqua values as provisional counts.

**Fix.** For Hawaiʻi, label near-real-time months as "not separable from volcanic heat" rather than giving a count, or show the count with the number of rows the mask removed.

### B3. In Hawaiʻi one afternoon pass is split across two dates

**Evidence.** Dates are UTC `acq_date`. 68.6% of Hawaiʻi's counted Aqua detections were acquired within an hour of 00:00 UTC (S-NPP 16.0%, NOAA-20 14.7%); elsewhere the share is under 1%. The early-afternoon pass over Hawaiʻi (about 14:00 HST) falls on the UTC date line, so a "day" on the map, the daily chart and the "1 to 13 November" cut can hold half of one pass and half of the next. Monthly totals move by the same mechanism at month ends. The page says dates are UTC but not that a pass can be split.

**Fix.** Say so for Hawaiʻi, or group that region's days by local date.

### B4. The mask check quoted on the page is in-sample and reads better than an out-of-sample one

**Evidence.** The page quotes the share of non-fire rows removed, checked on the same rows the mask was built from. Built from years to 2023 and tested on 2024 onward (`audit/out/recomputed.json`, `mask`):

| Region | Non-fire rows removed, in-sample | Out of sample | Fire rows wrongly removed, in-sample | Out of sample |
|---|---:|---:|---:|---:|
| California | 98.2% | 95.2% | 2.2% | 2.2% |
| Vietnam region | 97.6% | 93.7% | 4.1% | 2.2% |
| Contiguous United States | 99.0% | 95.9% | 4.2% | 2.8% |

The mask is the only thing standing in for `type` in near-real-time months. It removes 18% to 25% of near-real-time VIIRS rows in the three accepted regions, so its accuracy carries the month-to-date numbers: without it the US month-to-date NOAA-20 count is 13,244 instead of 9,681. The net bias from the figures above is small (a few percent low), but the page's numbers should be the out-of-sample ones. The page does say "checked against that same record".

**Fix.** Publish the out-of-sample check and quote it.

### B5. "California inside the national fit" is not independent of it

**Evidence.** The 20.0% in the "Compare regions" table applies US coefficients to California. California's rows are part of the US fit: its Aqua total over the paired months is about 14% of the US total. The US download cut to California's box reproduces California closely (annual k 8.462 against 8.471, error 15.2%). The comparison is therefore optimistic: with California's data removed from the national fit the error would be at least as large. README notes the boxes are not an exact subset but not this.

Related: the table presents four regions as four tests. California lies inside the United States box, so there are three independent areas.

**Fix.** Refit the national coefficients without California's box for this comparison, or state that the 20.0% is a lower bound. Say in the table that California is inside the United States.

### B6. README's rules are not quite enough to reproduce the counts

The recomputation matched everything except three monthly counts, each one detection apart (`audit/out/differences.json`):

| Region | Sensor, month | Recomputed | Project |
|---|---|---:|---:|
| California | Aqua, Sep 2026 | 263 | 264 |
| Contiguous United States | Aqua, Sep 2026 | 2,365 | 2,366 |
| Contiguous United States | S-NPP, Sep 2026 | 19,210 | 19,211 |

Cause: README gives the mask cell size (0.02°) and threshold (3) but not how a point is assigned to a cell. The audit used `floor(lat / 0.02)`; the pipeline uses `int((lat + 90) / 0.02)`. Floating-point rounding puts a few points in different cells (4,516 mask cells against 4,518; 7,831 against 7,832). No coefficient or error figure changes.

Other things README does not state, where the audit's guess happened to match: whether the box edges are inclusive (19 California rows and 62 Vietnam-region rows lie exactly on an edge); whether low-confidence rows count toward the mask; that months and days are UTC dates; that the fallback rule is re-applied inside each leave-one-year-out fit; how the bias column is defined; that NOAA-20's 100 months start in April 2018. README's data table says `satellite = A` / `T`; the files say `Aqua` / `Terra`.

**Fix.** Add these to README's Method section. They are a short paragraph.

### B7. Numbers that disagree or are typed in

Checked against the JSON files, `schema_report.json`, the hotspot indexes and file sizes. Everything not listed here agreed, including README's validation table, the month-to-date table, the per-calendar-month ranges, the forward-test figures, the Hawaiʻi type counts (73,595 of 80,102), the place counts, all 24 manifest row counts and all 12 sha256 hashes.

| Where | Says | Files say |
|---|---|---|
| README.md:166 | Vietnam hotspot files "total 114 MB compressed" | 119.3 MB (index.json); README.md:164 itself says 120 MB |
| README.md:214 | daily files "42 to 149 kB" | United States is 168.7 kB |
| README.md:35 | S-NPP period "2012 → 2026-10" | last row 2 Nov 2026; README.md:64 says 2 Nov |
| README.md:43, docs/index.html:459 | standard data "lags by 2 to 3 months" | VIIRS standard ends 31 Jul on a 14 Nov download: 3.5 months |
| README.md:36, 41 | "current months come from NOAA-20" | calendar values for current months are Aqua (README.md:65) |
| data/manifest.json | gazetteer `downloaded: 2026-11-15` | SOURCES.md says 14 Nov 2026 HST; one is UTC, unlabelled |
| docs/index.html:337 | "VIIRS (flying since 2012)" | Suomi NPP launched in 2011; "data since 2012" is what the files show |

Typed into the page where they could be read from data: "2 November 2026" (docs/index.html:1139); "2012 to 2021" and "2022 onward" in the trust table and month detail (docs/index.html:917 and the trust table), while the band derives the same periods from the JSON; the Hawaiʻi sentence "Most heat detected here is volcanic" (the 91.9% behind it is in README only). STATUS entries `standard_calibrated` and `no_detections_coverage_unknown` never occur in any region's data. (last item read, not re-checked)

### B8. Claims on the page with no source listed, or worded too strongly

(From the second reviewer's read of the page against SOURCES.md; quotes checked, sources not opened.)

- "VIIRS ... has smaller pixels than MODIS ..., so it records several times more detections of the same fires" (docs/index.html:337). "So" gives pixel size the whole ratio; README repeats it as "6 to 8 times". The project's own ratios run from 4.5 to 9.6 by month in accepted regions.
- "Counted detections are those the satellite marked as a likely vegetation fire with normal or high confidence" (docs/index.html:339). For near-real-time rows the satellite marks nothing; the project's mask decides. FIRMS says "nominal", not "normal".
- "the satellite record cannot reliably separate it from vegetation fire" (Hawaiʻi). The standard record does separate them (`type` 1); only the near-real-time rows cannot.
- Image resolutions "about 250 m per pixel" and "about 375 m per pixel": SOURCES.md says only names, dates and the tile matrix came from the GIBS capabilities document.
- "Sensors saturate on large fires" (README.md:179), the Machado et al. 2009 matrices (README.md:261), and "the team's own GOES-18 analysis of the 2023 Lahaina fire" (README.md:195) have no entry in SOURCES.md. The four ARSET trainings have no URL or date.
- The FIRMS acknowledgment quoted in SOURCES.md speaks of "imagery"; the project uses data, and the product rows carry no DOIs. The exact wording FIRMS asks for was not checked.

### B9. Licence and credits

(read, not re-checked, except where noted)

- LICENSE is the complete Apache 2.0 text. No file names the licence outside it: README says only "See LICENSE", and neither the page nor the pipeline mentions Apache. There is no copyright line. Nothing says that `docs/data/places/*.json` is GeoNames data under CC BY 4.0 rather than Apache, or that the hotspot files are NASA FIRMS data. Fix: one line in README and the footer.
- The page footer credits GIBS, OpenStreetMap, Nominatim and GeoNames but not Esri, which draws the default basemap from zoom 9. Esri appears only in the map's attribution control and in THIRD_PARTY_NOTICES.md, which itself says Esri's attribution guidance "could not be read on 14 Nov 2026".
- THIRD_PARTY_NOTICES.md:3 still has template text ("Add each dependency when it is first used. Versions come from the lock files."); there are no lock files.
- AI_USE.md:17 "none generated by AI so far. Any added later will be listed here" reads as unfinished. Its list of what was built does not name `pipeline/ingest.py` or `pipeline/calibrate.py`.

Found in order: Leaflet, esri-leaflet and esri-leaflet-vector are pinned with integrity hashes; every external host the page calls is in THIRD_PARTY_NOTICES.md; the only key in tracked files is the documented Esri key; no absolute local paths or email addresses in tracked files; no NASA logo or image; "Not endorsed by NASA" is on the page and in README; AI_USE.md is linked from both; `data/raw/` is ignored and no zip is tracked.

---

## C. Cosmetic

- Hawaiʻi's band shows "16808.2%" and "256.2%". Aqua recorded 414 counted detections there in 174 months and none in 99 of them, so these are ratios of very small numbers. Showing the counts would say more than the percentages.
- README's validation table rounds k to two decimals; the page shows three.
- docs/index.html:1790 builds "in 14 Nov 2026" for a day (should be "on").
- docs/index.html:391 lists California and Hawaiʻi as the regions with negative longitudes; the United States is missing.
- README.md:240 says a day is drawn "from that year's hotspot file"; for the United States it is a month file.
- Commit metadata carries an author email address, and the page names a GitHub account. Presumably intended.

---

## D. Checked and found sound

- **Counts.** 3,556 monthly values (four satellites, 313 months, four regions) recomputed from the raw zips: 3,553 equal, three differ by one (B6). `docs/data/<region>.json` carries the same values as `monthly_series.csv`.
- **Coefficients and errors.** All 48 monthly factors, the annual ratios, every leave-one-year-out figure (all years, before 2022, from 2022; monthly, annual and unconverted), the forward test, NOAA-20 against S-NPP, the acceptance decision and every month-to-date figure are reproduced exactly.
- **Leakage.** None found. The held-out year is excluded from the fit; the recomputation, written separately, gives the same errors. The mask is built from all years but touches only near-real-time rows, which are never in the test.
- **Small denominators.** In the three accepted regions the smallest Aqua total behind a monthly factor is 1,616 (California, May). In Hawaiʻi seven of twelve are under 30 and the region is correctly refused.
- **Typical month.** The headline error weights busy months most. The median monthly error, every month weighted equally, is lower or similar (California 13.4%, Vietnam region 11.6%, United States 7.4%), so the choice of measure does not flatter the result.
- **Double counting.** `data/raw/` is not read recursively, so the US files do not enter the other regions. No exact duplicate row (same satellite, date, time and position) was found from June 2026 onward; earlier months were not searched for duplicates. Hawaiʻi cut from the US download gives identical counts to Hawaiʻi's own download (two non-fire rows differ out of 228,966). California cut from the US download is slightly smaller than California's own box, as expected from the part of the box in Mexico.
- **UTC boundaries.** Under 1% of counted detections fall within an hour of UTC midnight outside Hawaiʻi.
- **Days without Aqua.** The 9 days with no Aqua row in the Vietnam region in September and in October 2026 are normal for those months (5 to 20 in 2015–2025), not a data gap.
- **Manifest.** Row counts and sha256 of all twelve downloads match.

## E. What could not be checked

- Any external document: whether the FIRMS and GIBS acknowledgments are quoted verbatim, what the Suomi NPP notice says, the GIBS first-image dates, Esri's and Nominatim's terms, the Space Apps 2026 rules on licence and AI disclosure.
- Whether the integrity hashes match the CDN files, and whether the Esri key is restricted as README says.
- The page in a browser. Section A5's messages and the footer credits were read from the source.
- Whether the raw zips are what FIRMS serves today; they were taken as given.
- The conversion as used (A1) for more than two months per region: only September and October 2026 are complete near-real-time months with both satellites.
- The county estimate near boundaries in the Vietnam region, for the reasons given in B1.
- Git history for secrets removed in earlier commits.
- Accessibility with a screen reader.
