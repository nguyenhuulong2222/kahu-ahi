# Kahu Ahi

**One consistent satellite fire record across the MODIS → VIIRS transition, honest about what satellites cannot see.**

NASA Space Apps Challenge 2026 · Challenge: *Harmonization of MODIS and VIIRS Hot Spots* · Local Event: Honolulu, HI · Team: Kahu Ahi

> **Status:** in progress. Built during the hackathon (Nov 14–15, 2026, HST). Sections marked `TBD` are filled only with measured results.

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
| Calibrated series | VNP14IMGML (VIIRS 375 m) | Suomi NPP | 2012 → 2026-10 |
| Current months | VJ114IMGML / VJ114IMGTDL_NRT | NOAA-20 | 2018 → present |

## Sensor timeline that shapes the method

- MODIS Terra and Aqua are near end of life. The archive is unaffected.
- Suomi NPP stopped delivering new observations on 2 Nov 2026, so current months come from NOAA-20.
- Aqua's orbit has drifted in recent years. The pipeline splits validation at **2022** (`DRIFT_YEAR` in `pipeline/calibrate.py`); that start year is an approximation and has not been checked against NASA documentation. Validation is reported separately before and after.
- Standard-quality monthly files lag by about 2–3 months. Newer months are near-real-time and labelled provisional.

## Metrics (never mixed)

1. `raw_detection_count` — hotspot records after quality filtering.
2. `grid_day_count` — number of (grid cell, date) pairs with at least one detection. Not a hotspot total.
3. `monthly_density` — the chosen metric divided by region area (per 1,000 km²) per month.

Calibration, calendar, median, map and validation all use the same metric: **metric 1, `raw_detection_count`**, computed as `n_veg_conf` in the pipeline:

- type 0 detections only (presumed vegetation fire); type 1 (volcano), 2 (other static land source) and 3 (offshore) are removed;
- near-real-time files have no `type` column, so their rows are dropped where the standard archive repeatedly recorded a non-vegetation source (the static-source mask: 0.02° cells with at least 3 such archive detections);
- low confidence removed (MODIS confidence below 30, VIIRS `l`).

Why counts: the same filter can be applied to every sensor's records, and counts can be checked row by row against the downloadable CSV, whose `counted` column is exactly this flag. Metrics 2 and 3 are not used anywhere in this version.

## Method

- **Calibration pair:** VIIRS Suomi NPP (375 m) against MODIS Aqua (about 1 km). Both cross the equator in the early afternoon, so they see the same part of the day. Terra (morning) is never put on the Aqua scale.
- **Training window:** every month from February 2012 to July 2026 in which both sensors have complete, standard-quality data (174 months in each region). Partial first months and near-real-time months are never used.
- **Coefficient:** for each calendar month m, k(m) = Σ S-NPP counts / Σ Aqua counts over all training years. A VIIRS count is put on the Aqua scale by dividing by k(m). A calendar month whose Aqua total is under 30 falls back to one annual coefficient.
- **NOAA-20:** used 1:1 in place of S-NPP (S-NPP's last day of data is 2 Nov 2026). The same leave-one-year-out test of a NOAA-20 → S-NPP coefficient did not reduce the error, so none is applied.
- **Which value the calendar shows:** MODIS Aqua when it has data for the month (standard, else near-real-time); otherwise VIIRS on the Aqua scale. In all three regions Aqua is still flying, so every calendar month from July 2002 is an Aqua count; the conversion is used for the month-to-date estimate and the "On the Aqua scale" columns.
- **Refusal:** calibration is refused for a region when the leave-one-year-out error exceeds 50% of the total, or fewer than 9 calendar months have their own coefficient. A refused region shows Aqua only and states the measured error.

### Partial-month comparison

The current month is compared with the median of the **same day range** (day 1 to D) in earlier years, never with a full-month median. Implemented, no fallback: D is the last date in the download minus one (that day was still being observed when the files were made), so for data through 14 Nov 2026 the comparison is 1–13 November against the same days of 2002–2025 (24 years of MODIS Aqua standard data; a year with no detection in those days counts as 0).

| Region | Aqua NRT, 1–13 Nov 2026 | NOAA-20 on the Aqua scale | Same days, earlier years: median (range) |
|---|---:|---:|---|
| California | 137 | 199.8 (raw 1,223, k(11) = 6.122) | 147 (49–642) |
| Vietnam region | 180 | 98.8 (raw 686, k(11) = 6.942) | 180.5 (56–453) |
| Hawaiʻi | 0 | not converted (raw 1) | 0 (0–9) |

**Why the two estimates disagree in November 2026.** Checked day by day in `daily_counts.csv`:

- *California.* NOAA-20 recorded 8.9 counted detections per Aqua detection over 1–13 November, close to September (9.4) and October (8.6). The sensors behave as before; the gap comes from the November coefficient, k(11) = 6.12, which is lower than this year's ratio. November is one of the least certain months: its leave-one-year-out error is 24.2% of the total (September 5.4%), and the yearly November ratio ranged 4.43–9.69 over 2012–2025. September and October agree within 2% because k(9) = 9.62 and k(10) = 8.50 happen to match this year's ratios.
- *Vietnam region.* September and October do **not** agree within 2%: NOAA-20 on the Aqua scale is 373 vs Aqua 461 (−19%) and 500 vs 755 (−34%). The yearly November S-NPP/Aqua ratio fell from 9.88 (2012) to 4.12–5.16 (2023–2025), and this year's NOAA-20/Aqua ratio is 3.8; k(11) = 6.94 pools all years, so the converted value runs low. This matches the larger error from 2022 onward (15.8% vs 10.5%).
- *Incomplete days.* The last date (14 Nov) is already dropped. Days on which Aqua has no record at all while NOAA-20 has 10 or more: California 3 of 13 in November (02, 03, 06) against 4 in September and 2 in October; Vietnam region 0 in November against 9 in September and 9 in October. Missing Aqua days do not explain the November gap.
- *S-NPP* stopped on 2 Nov and does not enter either estimate.

Found: the gap is the November coefficient against this year's sensor ratio. Not found: why this year's ratio differs from earlier years (Aqua's orbit drift is one candidate; this record cannot confirm it). The page keeps both values, shows this year's ratio next to the coefficient and its historical range, and says the reason is not known.

## Validation

Leave-one-year-out: each year is predicted from coefficients fitted without it and compared with what Aqua recorded. Error is the sum of absolute monthly errors as a share of the total Aqua count. From `data/processed/<region>/calibration.json`.

| Region | Paired months | Annual VIIRS:Aqua | VIIRS used raw | One annual k | Monthly k (used) | 2012–2021 / 2022 onward (monthly k) | Bias, monthly k | NOAA-20 vs S-NPP, 1:1 (100 months) | Accepted |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| California | 174 | 8.47 | 747.1% | 19.0% | **15.2%** | 14.0% / 21.2% | +0.9% | 5.8% | yes |
| Vietnam region | 174 | 6.25 | 524.7% | 16.8% | **12.0%** | 10.5% / 15.8% | +0.1% | 3.4% | yes |
| Hawaiʻi | 174 | 169.08 | 16,808.2% | 168.0% | **256.2%** | 308.7% / 136.2% | +124.5% | 15.8% | **no** |

Forward test (fit up to 2018, predict later years with monthly k): California 13.5% for 2019–2021 and 22.8% from 2022; Vietnam region 9.4% and 18.1%; Hawaiʻi 98.5% and 114.1%.

Months: 174 paired months per region (February 2012 to July 2026, standard data). Excluded: January 2012 (S-NPP's first, partial month), every near-real-time month (August 2026 onward for VIIRS, September 2026 onward for MODIS), and the current month. Hawaiʻi has only 5 calendar months with enough Aqua detections for their own coefficient (needs 9).

## Regions

| Region | Role | Bounding box |
|---|---|---|
| California | Calibration and validation | lat 32.5–42.0, lon −124.5–−114.0 |
| Hawaiʻi | Case study of a low-detection region | lat 18.7–22.5, lon −160.6–−154.5 |
| Vietnam region | Second calibration and validation region | lat 8.4–23.4, lon 102.1–109.5 (also takes in parts of Laos, Cambodia and southern China) |

## Map grid (pipeline step 4)

`pipeline/grid.py` counts detections on a 0.1° grid (about 11 km north–south) and writes `docs/data/grid/<region>/<year>.json` and `docs/data/grid/<region>/all_years.json`.

- Which detections are inside a region and which are counted comes from `export.detections()`, the same function that sets the `counted` column in the hotspot CSVs: type 0 (or, for near-real-time rows without `type`, outside the static-source mask), low confidence removed. The map, the calendar and the CSV therefore use one rule.
- Each year file holds, per month, every cell with at least one counted detection, with separate counts for MODIS Aqua, MODIS Terra, VIIRS Suomi NPP and VIIRS NOAA-20, split into standard and near-real-time lists. Cells are flat arrays of integers relative to the region's south-west cell. Each file also holds the cells for days 1 to D of the current calendar month, for the month-to-date comparison.
- Before writing, the step checks that the cells add up, per sensor and per month, to `monthly_series.csv`, that the month-to-date cells reproduce the month-to-date numbers in `calibration.json`, and that the all-years cells add up to `monthly_series.csv` over the same years. If any check fails it stops, lists the mismatches and writes nothing.
- `all_years.json` is the map's default view: each cell's total over every complete standard year, per satellite. A year counts for a satellite when all 12 months are complete standard data under `calibrate.usable()`: MODIS Aqua 2003–2025 (23 years, the same years as the calendar's "usual"), Terra 2001–2025, Suomi NPP 2013–2025, NOAA-20 2019–2025 in all three regions. The step checks that these totals equal `monthly_series.csv` summed over the same years. Sizes: California 87 kB, Hawaiʻi 3 kB, Vietnam region 160 kB.
- A point is placed in the cell `floor((lat + 90) × 10 + 10⁻⁶)`, `floor((lon + 180) × 10 + 10⁻⁶)`; the web app bins CSV rows with the same expression.

Sizes (uncompressed JSON; GitHub Pages serves it gzip-compressed, about a third of this): California 1.30 MB for 27 years, largest year 94 kB; Hawaiʻi 0.03 MB; Vietnam region 9.95 MB, largest year about 600 kB (180 kB gzip).

## Choosing an area

On the map a user can draw a rectangle, or type its west, south, east and north edges. The area:

1. is widened outward to whole 0.1° cells and clipped to the region box (an area wholly outside it is refused);
2. is summed from the grid files: the calendar, the "usual" medians, the seasonal bars and the month-to-date panel are rebuilt from the cells inside it;
3. keeps the region's choice of satellite and data status for every month, and the region's coefficients from `<region>.json` for any VIIRS value converted to the Aqua scale. Where the region's calibration was refused (Hawaiʻi), only MODIS Aqua is shown for the area too;
4. limits the CSV download to rows whose point falls in the area's cells, so the file matches what the calendar counted;
5. is stored in the URL hash (`#region=…&month=…&area=W,S,E,N`) so a view can be shared.

Checked in the browser: with the area set to the whole region box, every rebuilt harmonized value, sensor count, median and month-to-date number equals `<region>.json` for California, Hawaiʻi and the Vietnam region.

### Limits of an area

- **The conversion was not validated for the area.** k(m) was fitted and tested leave-one-year-out on the whole region. A smaller area can burn different vegetation, at a different time of day, and its VIIRS/Aqua ratio may differ. The page says this whenever an area is set.
- **Few detections, noisy comparisons.** When MODIS Aqua recorded fewer than **30 detections a year** in the area (mean over complete standard years from 2003), the page warns that the comparison is rough. At that level typical months hold 0 to 5 detections, so one detection more or less moves a month a long way from its usual. The threshold is a judgement, not a fitted value.
- **Cell resolution.** Areas are whole 0.1° cells. Detections are pixel centres; a fire on a cell edge can be counted in the neighbouring cell.
- **VIIRS values on the Aqua scale can differ in the last decimal** from the whole-region values when an area covers the whole region, because `<region>.json` publishes k rounded to 3 decimals. Harmonized values in these regions come from Aqua and are unaffected.
- The region's static-source mask and quality labels are reused unchanged.

## Known limits

- **Hawaiʻi is refused.** 73,595 of 80,102 standard MODIS detections there (91.9%) are type 1 (volcano). VIIRS files give no `type` for near-real-time months, and the static-source mask that replaces it wrongly removes 90.2% of Hawaiʻi's vegetation detections in the in-sample check (California 2.2%, Vietnam region 4.1%). Only Aqua is shown.
- **The conversion is less accurate from 2022.** Monthly-k error rises from 14.0% to 21.2% (California) and 10.5% to 15.8% (Vietnam region). The coefficients pool 2012–2026 and do not follow the falling VIIRS:Aqua ratio seen in recent Vietnam Novembers.
- **Some calendar months are much less certain than the average.** Leave-one-year-out error by calendar month ranges from 5.4% (September) to 26.1% (December) in California and from 8.2% (February) to 23.9% (July) in the Vietnam region. Only the all-month figures are shown on the page.
- **Near-real-time months are provisional.** Standard data ends 31 Aug 2026 (MODIS) and 31 Jul 2026 (VIIRS). Later months use near-real-time files, which have no `type` column.
- **`<region>.json` publishes k rounded to 3 decimals.** VIIRS values on the Aqua scale recomputed in the browser for a chosen area can differ in the last decimal from the pipeline's values.
- **The static-source mask is built from every file in `data/raw/`.** Its total cell count (4,518 with all three regions' downloads present; 1,415 before the Vietnam files were added) is shared by all regions. Cells are 2 km and the regions do not overlap, so a region's counts are unaffected; the in-region check rates above are per region.
- **Vietnam region file sizes.** Its hotspot files total 114 MB compressed (up to 11 MB a year) and its grid 9.95 MB uncompressed. Individual detections and the area download read the year files as a stream; on a slow connection a year can still take a while to arrive.
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
- DSWx keeps separate codes for not water, masked, cloud and no data. Here statuses stay distinct and are never collapsed to 0: measured, provisional, partial month, not on this scale, not converted, satellite not flying (`status` in `monthly_series.csv`; `STATUS` in [docs/index.html](docs/index.html)).
- DSWx ships simple, confidence and diagnostic layers. The month detail shows the value, its status, the conversion's tested error for that period and the per-sensor counts, and the same columns are in the monthly table download ([docs/index.html](docs/index.html), `drawDetail()`, `downloadMonthly()`).
- Radar shadow is masked as a known false source. Here the static-source mask removes known non-fire heat and reports its measured hit and false-removal rates ([pipeline/ingest.py](pipeline/ingest.py), trust card on the page).
- NISAR data is released as provisional before validated reprocessing. Near-real-time months are labelled provisional ([pipeline/calibrate.py](pipeline/calibrate.py), `provisional_nrt`).

**NISAR Surface Displacement, part 1**
- Loss of coherence means unknown, not "no movement". A region that fails validation is shown with its numbers and its VIIRS values are left unconverted, not hidden or forced (Hawaiʻi banner and trust card).
- Urgent-response products are faster and less accurate. The page states that trade next to every provisional value (`STATUS.provisional_nrt` in [docs/index.html](docs/index.html)).
- Different products suit different magnitudes. Each region gets its own coefficients; none are borrowed from another region ([pipeline/calibrate.py](pipeline/calibrate.py), run per region).

**Geostationary Remote Sensing of Aerosols** (with the team's own GOES-18 analysis of the 2023 Lahaina fire)
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
```

`export.py` also writes `docs/data/<region>_daily.json` (counted detections per day, per satellite and data quality; 42 to 149 kB). It stops and writes nothing if the days do not add up, per satellite and per month, to `monthly_series.csv`. `--skip-hotspots` rewrites only the two summary files without reading `data/raw/` again.

Hawaiʻi uses `--bbox -160.6 18.7 -154.5 22.5`; the Vietnam region `--bbox 102.1 8.4 109.5 23.4`.

The web app is the static folder `docs/`: `python3 -m http.server -d docs 8000`, then open http://localhost:8000. It requests only its own files, Leaflet from cdnjs, and basemap tiles: NASA GIBS (Blue Marble with coastline, border and label overlays) up to zoom 8, and from zoom 9 Esri World Imagery with Esri's reference labels (its two libraries load from jsDelivr only then), falling back to OpenStreetMap if Esri is unavailable. No FIRMS or other data API is called from the page.

The `ESRI_API_KEY` in `docs/index.html` is a public basemap key: ArcGIS Location Platform, basemap privileges only, restricted to the referrers https://nguyenhuulong2222.github.io and http://localhost. It is meant to be shipped in a web page and is not a secret. Leave it empty and the page uses OpenStreetMap at close zoom.

### Reading the page

- Page order: title, map, "What you are looking at", "Fire activity over time", the full record (the month-by-year calendar), how far to trust it, downloads, method and sources.
- **One selection.** All years, one year, one month or one day. The map, the timeline, the charts, the calendar and the page address (`#region=…&year=…`, `&month=…` or `&day=…`) all read and write it through one function, `select()`.
- **What you are looking at** is generated for the selection from the same series as the calendar: what a square is, the count with its unit and how it compares with the usual, and what the colours mean. A refused region (Hawaiʻi), provisional months and incomplete periods get their own sentences. A "How to read this" box defines each term once.
- **Fire activity over time** drills down: a bar per year (hatched when the year lacks twelve months of final data), then twelve monthly bars over the lowest-to-highest band and median of final data since 2003 (the same "usual" as the calendar), then daily bars from `<region>_daily.json`. Daily bars show one satellite as recorded; where VIIRS is converted it appears as dots labelled "indicative: tested by month, not by day", because the conversion was validated on monthly totals only. Daily counts are for the whole region, also when an area is chosen. Every bar is a button with its value in words; a table gives each satellite's daily counts.
- **A day on the map** is drawn as individual detections from that year's hotspot file, loaded on demand, with the 4,000-square cap.
- **A year on the map** adds up the year's months on a scale fixed across years (`max_cell_year` in the grid index).
- **Play** steps at the level of the selection (years, months or days) at slow, normal or fast speed. It never starts by itself, waits for each frame to be drawn instead of skipping, preloads the next grid file, keeps the colour scale fixed, stops at the last step, and is paused by any choice on the timeline, calendar, charts or map. Screen readers hear "Playing" and "Paused", not every frame. Space toggles it while the slider has focus.
- **Empty states** are in words on the map: "not flying yet" or "no longer sending data", with the satellite's first or last date and a button back to the harmonized view, is kept apart from "was flying but recorded no detection", which is never called no fire.

### Map display

- The map opens on **All years**; selecting a calendar month shows that month, and the All years button returns to the total.
- Colours: one fire ramp for the calendar and the map, low to high: deep maroon, red, orange, yellow (`FIRE` in `docs/index.html`). Lightness rises at every step (L* 14 to 92), and still does under simulated protanopia, deuteranopia and tritanopia (Machado et al. 2009 matrices); every step carries white or near-black text at 4.5:1 or better. Calendar cells keep their printed numbers, and provisional, partial, Terra-only and refused keep their borders, hatching and wording, so nothing depends on colour alone.
- Map cells use the upper seven steps of that ramp on the same log scale: the darkest steps disappear on the dark satellite imagery.
- Individual detections are red squares with a dark edge; detections that were not counted are hollow dashed squares. The legend lists the count range of each step, worked out with the same function that colours the cells.
- Cells are drawn without gaps at 82% opacity so coastlines show through. Pointing at a cell, tapping it, or focusing a row of the "cells with the most detections" table outlines the cell and shows its count, so no value is given by colour alone.
- Outside the region box the map is dimmed slightly; nothing is drawn there.
- Layout: the map sits at the top of the page, full width, with the timeline along its bottom edge (about 70% of the window together). "Expand map" fills the window with the browser's Fullscreen API, or with a fixed-position fallback where that API is missing (iPhone Safari); Esc or "Close full screen" returns.
- The timeline steps at the level of the selection: years (with an "All years" position), the months of the record, or the days of a month, with Play, a speed choice, and buttons for the next coarser step. It and the calendar and charts drive the same selection, so each moves the others.
- The Layers panel (top left) holds the basemap choice, the satellite switch, grid cells or individual detections, and the region outline. The legend (bottom right) gives the colour steps and units; a scale bar and the latitude and longitude under the pointer (or of the map centre) are at bottom left.
- Individual detections are drawn as squares of the sensor's nadir footprint, about 1 km for MODIS and 375 m for VIIRS, never smaller than 5 pixels.

## License

See [LICENSE](LICENSE). Third-party components: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Acknowledgments

Fire data: NASA FIRMS. The official FIRMS acknowledgment statement is reproduced in [SOURCES.md](SOURCES.md). This project is not endorsed by NASA.
