# Kahu Ahi

**One consistent satellite fire record across the MODIS → VIIRS transition, honest about what satellites cannot see.**

NASA Space Apps Challenge 2026 · Challenge: *Harmonization of MODIS and VIIRS Hot Spots* · Local Event: Honolulu, HI · Team: Kahu Ahi

> **Status:** in progress. Built during the hackathon (Nov 14–15, 2026, HST). Sections marked `TBD` are filled only with measured results.

## What it does

- Puts VIIRS active-fire detections on a MODIS-Aqua-equivalent scale so monthly fire activity can be compared across sensors.
- Shows a month × year burning calendar for supported regions.
- Compares the current month with the multi-year median for the same range of days.
- Lets you download the underlying hotspot records as CSV.
- Labels every value with its data status (standard, provisional, not calibrated, partial month, unknown coverage).

## What it does not do

- It is not a fire alert, forecast, or real-time detection tool.
- It does not claim that sensors become identical after calibration. Remaining error is reported.
- "No detection" is never shown as "no fire". Clouds, smoke, short fires and overpass timing all hide fires.
- It supports a small set of pre-processed regions, not arbitrary areas worldwide.

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
- Aqua's orbit has drifted in recent years (start year: `TBD — verify`). Validation is reported separately before and after.
- Standard-quality monthly files lag by about 2–3 months. Newer months are near-real-time and labelled provisional.

## Metrics (never mixed)

1. `raw_detection_count` — hotspot records after quality filtering.
2. `grid_day_count` — number of (grid cell, date) pairs with at least one detection. Not a hotspot total.
3. `monthly_density` — the chosen metric divided by region area (per 1,000 km²) per month.

Calibration, calendar, median and validation all use the same metric. `TBD — metric chosen and why`.

## Method

`TBD` — calibration pair, training window, coefficient definition, when calibration is refused for lack of data.

### Partial-month comparison

The current month is compared with the median of the **same day range** (day 1 to D) in earlier years, never with a full-month median. `TBD — implemented / fallback used`.

## Validation

`TBD — real numbers only.`

- Leave-one-year-out error, calibrated vs uncalibrated baseline
- Split before / after Aqua orbital drift
- Number of valid months and months excluded

## Regions

| Region | Role | Bounding box |
|---|---|---|
| California | Calibration and validation | lat 32.5–42.0, lon −124.5–−114.0 |
| Hawaiʻi | Case study of a low-detection region | `TBD` |

## Known limits

`TBD` — updated as limits are found.

## Use of AI

AI tools were used in this project. See [AI_USE.md](AI_USE.md).

## How to run

`TBD`

## License

See [LICENSE](LICENSE). Third-party components: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Acknowledgments

Fire data: NASA FIRMS. The official FIRMS acknowledgment statement is reproduced in [SOURCES.md](SOURCES.md). This project is not endorsed by NASA.
