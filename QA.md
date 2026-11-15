# QA: whole-site consistency pass

Date: 14 Nov 2026. Page: `docs/index.html` served locally from `docs/`. Browser: Chromium through Playwright.
No count, coefficient, acceptance rule or validation figure was changed in this pass; `python3 audit/recompute.py`
was re-run afterwards and reports 0 differences for the four regions and for the 49 states.

Screenshots are in `qa/` (git-ignored, so they are on the machine that ran the pass, not in the repository).

## What was run, and what was not

1. **Matrix, 147 cells.** 7 regions x 7 levels x 3 sizes, each loaded from its own address, screenshot of the top of
   the page saved as `qa/<region>_<level>_<size>.png`, and the checks of the next section run on the loaded page.
   - Regions: `us` (Contiguous United States, whole), `california`, `texas`, `newyork` (not harmonized),
     `westvirginia` (small accepted state), `hawaii` (not harmonized), `vietnam`.
   - Levels: `day-busy` (the day with the most MODIS Aqua detections), `day-quiet` (a recent day with 2 to 6),
     `day-one` (a recent day with exactly 1), `day-latest` (the day the page opens on), `month` (Aug 2021; Apr 2021
     for New York, Aug 2023 for Hawaiʻi), `year` (2021), `all` (all years).
   - Sizes: `desk` 1440x900, `mid` 1024x768, `phone` 390x844.
2. **Control tour, 7 cells x 3 sizes, 250 steps per size.** Every control was exercised in these cells, not in all
   147: `us_day-latest`, `california_month`, `newyork_year`, `westvirginia_day-one`, `hawaii_all`,
   `vietnam_day-busy`, `texas_month`. After each step the same checks were run again, so a stale heading, list,
   marker count or address after a click sequence would show. Steps: Layers panel (each basemap, each satellite and
   back, outline, grid or detections where offered); timeline (each step button, play and pause, speed, slider to
   both ends, each level, Go to, month row); record switch; Show 5/10/20; area row, preview card, Next to the last,
   Zoom, Esc; day row and its card; "List"; detections table (every column sort, Show more, CSV download, a row, the
   detection card, the report, Esc); by-state table sorts; keyboard order of the timeline against its reading order.
   One screenshot per opened panel: `qa/<cell>_<size>_<panel>.png` with panel one of `layers`, `most`,
   `preview-area`, `preview-day`, `table`, `card`, `report`, `drill`, `calendar`, `trust`, `compare`, `bystate`,
   `downloads`, `footer`.
3. **Links.** The 70 distinct URLs in `docs/index.html`, `README.md`, `SOURCES.md` and `THIRD_PARTY_NOTICES.md`
   were requested with curl.
4. **By eye.** A sample of the screenshots was looked at, not all of them: the before and after pairs listed below
   and a handful of matrix cells at 1024 and 390. The automated checks carry the rest.

Not verified: other browsers (Safari, Firefox) and real phones; a screen reader; print of the report in this pass;
the drawn-area tool (draw a rectangle on the map) was not exercised in the tour; the full-year hotspot download
button was not pressed in the tour (the table CSV was); play was run for 1.6 seconds per cell, not to the end.

## Checks run on every cell and after every tour step

- No "undefined", "NaN" or "[object Object]" in the text; no "1 detections", "1 areas", "1 days", "1 rows", ...
- No horizontal scroll; no clipped heading, button or table header.
- The map sentence starts with the period shown; the timeline label equals it; the address bar holds the same
  region, state and level as the page; the region and state lists show the view.
- "Harmonization result", "Where and when it burned most", "Fire activity over time", the calendar, the month so
  far, the season, the trust section and the downloads name the region or state; "burned most" also names the
  period and the satellite; the detections heading names the day.
- Show: a value is pressed, it is not a disabled one, the heading says "Top N" only when N rows are listed and N is
  the pressed value; the number in the heading equals the rows; the listed areas have markers.
- Every visible control has a text, a label or an accessible name. In the tour: every disabled button states why.
- The legend lists detections exactly when detections are drawn.
- Console: errors and warnings collected.

## Result

| Run | Cells or steps | Failing before the fixes | Failing after |
|---|---|---|---|
| Matrix, desk | 49 | 24 | 0 |
| Matrix, mid | 49 | not run before the first fixes | 0 |
| Matrix, phone | 49 | not run before the first fixes | 0 |
| Control tour, desk | 250 steps | 3 kinds of issue (below) | 0 |
| Control tour, mid | 250 steps | not run before | 0 |
| Control tour, phone | 250 steps | not run before | 0 |

The matrix was run on the desk size before any fix (24 of 49 cells failed: every day or month with fewer areas
than the Show value, and every one-detection day), then on all three sizes after the first fixes, and once more on
all three sizes on the final page. All 147 cells pass. Console: clean in every matrix run and in the desk and phone
tours; the mid tour logged one warning from the third-party basemap library while a basemap was being switched
("AbortError: signal is aborted without reason", esri-leaflet-vector 4.3.2), which is a cancelled tile request and
not a fault of the page.

## Inconsistencies found and fixed

| # | What was wrong | Fix | Before | After |
|---|---|---|---|---|
| 1 | Show set to 10 (or 5), heading "Top 1 places of the day" / "Top 3 areas" / "Top 2 days", fewer rows than the value. 24 of 49 desk cells. | The heading states what is listed: "Top 5 areas" only when there are more; otherwise "All 3 areas with detections in Aug 2021" or "The only area with detections on 7 Jan 2024". A choice that would list the same as a smaller one is disabled, and a line beside the control says why. The pressed value is the smallest that gives the lists on screen. The sentence about the busiest days follows the same rule. | `before_show-control_desk.png`, `before_show-control-month_phone.png` | `after_show-control_desk.png`, `after_show-control-month_phone.png` |
| 2 | "1 detections", "1 areas", "1 rows (CSV)", "Download these 1 ..." in the share line, table caption, month sentences, chart labels, download buttons. | One helper writes a count with its noun; 20 places use it, 4 more were corrected by hand. Buttons read "Download the 1 row (CSV)". | `before_show-control_desk.png` | `after_show-control_desk.png` |
| 3 | Percentages in two formats: "772%" beside "34.2%", "16808.2%" without a separator, shares of the season with no decimal. | Every measured percentage has one decimal and thousands separators ("772.0%", "16,808.2%"). The 50% limit of the acceptance rule stays as it is defined. | `before_percent-format_desk.png` | `after_percent-format_desk.png` |
| 4 | Two names for one region: "United States" in the list, "Contiguous United States" in every heading. | The list says "Contiguous United States". | `before_region-name_desk.png` | `after_region-name_desk.png` |
| 5 | Two names for one satellite: "VIIRS Suomi NPP" in sentences, "VIIRS S-NPP" in the Layers list, tables and cards. | "VIIRS Suomi NPP" everywhere on the page. | `us_day-latest_desk_layers.png` (after only) | same |
| 6 | "places of the day" for what the same section calls "areas" at the other levels. | "areas" everywhere; "place" is kept for a named town. Vocabulary listed in README, "Words the page uses". | `before_show-control_desk.png` | `after_show-control_desk.png` |
| 7 | Headings without the region: the calendar, the month so far, the season, the trust section, the downloads, "Fire activity over time". "Burned most" did not name the satellite. | Each names the region or state; "burned most" names period, region and satellite; "This month so far" names the month. | `before_headings_desk.png` | `after_headings_desk.png` |
| 8 | "Data through 2026-11-14" beside dates written "14 Nov 2026". | "Data through 14 Nov 2026 (UTC)". | `before_region-name_desk.png` | `after_region-name_desk.png` |
| 9 | Legend said "Supported region" for a state outline, and had no entry for the numbered markers and dashed squares. Blank cells were explained in three wordings. | "Outline of West Virginia" or "Region with data: ..."; an entry for the numbered markers, shown only when they are drawn; one wording: "no detection recorded, which is not the same as no fire". | `before_legend_desk.png` | `after_legend_desk.png` |
| 10 | Disabled buttons that did not say why: the timeline's step buttons at the ends of the record, Previous and Next in the preview card, a month outside the record, "Whole region", the table's CSV button with no rows, the card's actions while loading, "Open the busiest day" at the all-years level (which stayed off with no reason). | Each carries the reason as its title and in its accessible name. | found by the tour, no screenshot | `hawaii_all_desk_preview-area.png` |
| 11 | Esc closed only the preview card. | Esc closes, newest first: the preview card, the report, the detection card, the Layers panel when focus is in it. The address drops `report=`. | found by the tour | tour steps "report", "detection card" |
| 12 | Phone: the timeline was laid out in an order the keyboard did not follow (play, slider, speed on screen; play, speed, steps, slider by Tab). | The phone layout follows the document order: play and speed, then the steps around the slider, then Go to, then the levels. Height unchanged (198 px). | `before_timeline-order_phone.png` | `after_timeline-order_phone.png` |
| 13 | The two sections under the timeline had their own spacing (12 px above, 14 px inside) against 20 px everywhere else. | 20 px, as every other section. | `before_spacing_desk.png` | `after_spacing_desk.png` |
| 14 | The trust section's period read "all years (refused, not converted)"; the page's word is "not harmonized". | "all years (not harmonized, VIIRS not converted)". | not captured | not captured |

## Checked and found consistent (no change)

- One focus ring (3 px gold outline) on every control; pressed state is navy on light surfaces and gold on the
  dark timeline bar.
- Loading and failure messages: "Loading ..." and "... could not be loaded" throughout.
- Links: 65 of 70 URLs return 200. The other five are not links a reader follows: `doi.org/10.1109/TVCG.2009.113`
  answers 202 to an automated client and opens in a browser; `nominatim.openstreetmap.org/reverse` (400) and
  `basemapstyles-api.arcgis.com/.../imagery` (401) are API endpoints named without their parameters or key;
  `cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/` (404) is the folder of the library files, which load;
  `nguyenhuulong2222.github.io` (404) is the origin named for the key's referrer restriction, the page itself is
  under `/kahu-ahi/`.

## Not fixed, and why

- **Teal has two meanings.** It is the colour of action buttons and links, of NOAA-20 in charts, and of the error
  ramp of the by-state map. Each use is labelled where it appears, but the rule "one colour, one meaning" is not
  met. Changing it means re-choosing the chart palette and checking it for colour-blind separation, which is more
  than a consistency fix; left as it is and recorded here and in AUDIT.md.
- **The date field shows the browser's own format** ("10/27/2026" in a US-English browser) beside "27 Oct 2026" in
  the text. A native date input cannot be told how to write the date; replacing it with a custom control would be
  a new feature.
- **Gold focus ring on white** has low contrast against the white panels (it is clear on the dark timeline and on
  the map). Not changed in this pass.
- **Totals that differ by design**: for a state, the map sums grid cells whose centre is in the state
  (Texas, all years: 88,215) while the season sentence sums detections by position (88,447). The map sentence says
  so ("A cell on the border also holds detections of the neighbour"); the two figures still sit close together in
  "burned most".
- **README and the method notes still say "refused" and "S-NPP"** where they describe the acceptance rule and the
  data fields; the page itself does not. The vocabulary table in README says which word is used where.
- The open items of AUDIT.md ("Remains") are unchanged by this pass.

## Second pass: nine design defects found by looking at the screenshots

Date: 14 Nov 2026. No count or coefficient was changed; `python3 audit/recompute.py` was re-run and reports
0 differences for the four regions and the 49 states. The "before" screenshots were copied to `qa/before9/` before
any change; the "after" ones were re-shot on the final page and looked at.

| # | Defect | Fix | Before | After |
|---|---|---|---|---|
| 1 | The open legend covered the map's zoom-out button. | The legend is never taller than the room under the zoom buttons and scrolls inside it, with a shadow at the edge that has more. Layers is never taller than the map; the scale and the coordinates move aside while it is open. On a phone one panel is open at a time, and Layers stops short of the Expand button. | `before9/us_day-latest_desk.png` | `us_day-latest_desk.png` |
| 2 | Detection card: the place wrapped one word per line beside the locator; the card's bottom was cut at the map edge and it lay over the zoom and Expand buttons. | The place is the first row at full width with the locator right-aligned under it. The card is 380 px wide, scrolls inside the map, and the zoom buttons, Expand and the attribution move left of it; the legend is put away while it is open. On a phone the card is a block under the timeline instead of a sheet over the map. | `before9/us_day-latest_desk_card.png` | `us_day-latest_desk_card.png`, `us_day-latest_mid_card.png`, `us_day-latest_phone_card.png` |
| 3 | Layers started open on desktop and was cut mid-row. | It starts as a "Layers" button at every width. Open at 1440x900 it shows all of its content (324 px, no scroll); at 1024x768 and on the phone the map is shorter than the content (341 px against 320, 383 against 169), so it scrolls with a shadow cue. The legend starts open only when it covers neither the region box nor a control. | `before9/us_day-latest_desk_layers.png` | `us_day-latest_desk_layers.png`, `us_day-latest_mid_layers.png`, `us_day-latest_phone_layers.png` |
| 4 | Grouped markers read "1+3". | The marker shows the lowest rank with a small "+3" badge; its accessible name is "Areas 1, 2, 8 and 10"; the legend has a line for it. Clicking opens area 1, and Next goes 1, 2, 8, 10 and then the rest (checked in the browser). Opening from a list row keeps the list order. | `before9/us_day-latest_desk.png` | `us_day-latest_desk_markers.png` |
| 5 | Trust section, United States: "Other parts of the country were not measured this way", and the old rectangle called "this page's California region". | The section now says every one of the 49 is measured with the national factors, gives the range read from the state file (14.8%, Idaho, to 129.7%, Vermont; one with no computable error) and links to the By state table. The rectangle is "California test box" everywhere. Other sentences changed, listed below. | `before9/us_day-latest_desk_trust.png` | `us_day-latest_desk_trust.png` |
| 6 | "New York: not harmonized (only 8 of 12 ... (9 needed)), so only MODIS Aqua is shown." | "New York: not harmonized. Only 8 of 12 calendar months have enough detections for a factor; 9 are needed. Only MODIS Aqua is shown." Hawaiʻi: "... The tested error is 256.2%, over the 50% limit. Only 5 of 12 ...". | `before9/newyork_year_desk.png` | `newyork_year_desk.png` |
| 7 | Phone timeline: speed was a full-width field; the "Centre ..." box sat on the small map. | Speed is a compact select (110 px) beside Play and the four step buttons; the slider has its own row; the coordinates box is not shown on phones. The timeline is 194 px tall inside its 200 px, with the level switch fully visible. The slider now follows the step buttons in the document and on screen at every width, so keyboard order still equals reading order. | `before9/us_day-latest_phone.png` | `us_day-latest_phone_timeline.png` |
| 8 | Sections below the fold used the left half only at 1440. | At 1100 px and wider the page body is as wide as the two sections under the timeline. Text sits beside its chart (activity over time), its table (calendar with the selected month beside it, by state), its form (choose an area); "What you are looking at", the detections notes, the trust section, the compare notes, the downloads and the limits take two columns. Lines stay at 68 characters or fewer; the header text is held to 78. | `before9/us_day-latest_desk_trust.png`, `before9/us_day-latest_desk_drill.png`, `before9/us_day-latest_desk_calendar.png` | `us_day-latest_desk_what.png`, `_table`, `_drill`, `_calendar`, `_area`, `_trust`, `_downloads`, `_limits` |
| 9 | By state legend did not say which end is better. | "Lighter = smaller error; from best to worst:" before the steps, which run from "up to 10%" to "over 35% to 50%", then the hatched "Not harmonized". | `before9/us_day-latest_desk_bystate.png` | `us_day-latest_desk_bystate.png` |

### Sentences made untrue by the state split, and what they say now (item 5)

Page:
- Trust section: "Measured for one part: applied to this page's California region ... Other parts of the country were not
  measured this way." is now the two paragraphs described in item 5.
- "Choose an area": "as in California, Hawaiʻi and the contiguous United States" is now "as in Hawaiʻi and the
  contiguous United States" (California is no longer a region of the page).
- Method paragraph: "For each region, the months when ..." is now "For each region, and for each state of the contiguous
  United States, ...".
- Limits: "An area you choose inside a region uses that region's conversion ..." now also says each of the 48 states
  and DC is checked on its own data, and that a drawn area uses its region's or state's conversion.
- Compare note: "in the State list under United States" is now "under Contiguous United States".

README:
- "No other part of the country was measured this way." is now a sentence saying every state is measured by
  `pipeline/states.py`, with a pointer to the By state table.
- "this project's California region" is now "the California test box".
- The rectangle is named "California test box" in the month-to-date table and notes, the validation tables, the
  forward test, the sizes, the browser check, the limits (2022 onward, calendar months, static-source mask, county
  of the nearest town) and the "Compare regions" entry. The `--name "California"` argument of the pipeline command
  is unchanged, because it is the name written in the data file.

### Found on the way and fixed

- The compare table wrote percentages as stored ("168%", "12%", "16808.2%"); it now uses the page's one format
  ("168.0%", "12.0%", "16,808.2%"). Its column "NOAA-20 in place of S-NPP" is now "... Suomi NPP".
- The share of faint cells in "What you are looking at" had no decimal; it has one.

### Check that no panel covers a map control (item 1)

All 147 cells (7 regions x 7 levels x 1440x900, 1024x768, 390x844) were loaded and measured in four states: as
loaded; legend opened; Layers opened after it; and, on the busy day of each region, a detection card open, then
Layers reopened with the card open. Measured: any overlap of the Layers panel, the legend, the card or the
satellite chip with the zoom buttons, Expand, the scale bar, the coordinates box or the attribution, with each
other, or beyond the map's edge. First run: clean at 1440 in every state; at 1024, Layers lay over the attribution
when a card was open; on the phone, Layers and the legend open together overlapped each other and Layers reached
Expand. After the fixes: 0 overlaps in 147 cells, console clean. The top-of-page screenshots of the matrix were
re-shot in that run.

Not verified in this second pass: the 250-step control tour of the first pass was not repeated in full after these
layout changes (the panel states, the card, the grouped markers and the phone timeline were exercised by the
checks above); the full-screen map; print of the report; other browsers and real phones. With the card open on
desktop, a long Esri attribution is shortened with an ellipsis rather than wrapped.

## Third pass: three layout fixes seen in the screenshots

Date: 14 Nov 2026. Layout only; no count or data file was touched, so `audit/recompute.py` was not run again after
this pass (its last run, after the second pass, reported 0 differences). "Before" shots are in `qa/before3/`; the
"after" shots were re-shot at 1440x900 and 390x844 and looked at. Console clean in both.

| # | Defect | Fix | Before | After |
|---|---|---|---|---|
| 1 | Detection card: an empty block between the place note and the locator; no cue that the card scrolls; the last visible line cut in half at the bottom edge. | The locator sits right-aligned directly under the place lines, with the small note beside it, so the row has no empty block (measured: the locator starts 2 px below the top of the note, flush with the right edge). While the card holds more than it shows, its bottom edge fades the text out under the same shadow the legend uses, so no line is cut hard; the cue goes when the end is reached (checked by scrolling to the end). On the phone the card is not a scrolling box, so it has no cue. | `before3/us_day-latest_desk_card.png`, `before3/us_day-latest_phone_card.png` | `us_day-latest_desk_card.png`, `us_day-latest_desk_card_end.png`, `us_day-latest_phone_card.png` |
| 2 | "Record shown in the calendar and charts": the first choice sat beside the label and the second wrapped under it. | The label is on its own line; the two choices are on one line under it, level with each other (measured at 1440: same top, 889 and 1070 px from the left); on a phone they are stacked and left-aligned. Same in both places the switch appears. | `before3/us_day-latest_desk_calendar.png` | `us_day-latest_desk_calendar.png`, `us_day-latest_desk_recordbar.png`, `us_day-latest_phone_calendar.png`, `us_day-latest_phone_recordbar.png` |
| 3 | Calendar section at 1100 px and wider: an empty block between "Colour shows" and the calendar. | The calendar starts 10 px under the control. The right column (what the record is, the record switch, the note on the area, the selected month) starts level with the top of the calendar (measured: both at the same offset). Below 1100 px the order is unchanged. | `before3/us_day-latest_desk_calendar.png` | `us_day-latest_desk_calendar.png`, `us_day-latest_phone_calendar.png` |

Not verified in this pass: the 147-cell overlap check and the control tour were not repeated (the changes are
inside the card, the record switch and the calendar section); 1024x768 was not re-shot.

## Fourth pass: selecting shows information and moves nothing

Date: 14 Nov 2026. Behaviour and layout only; no count or data file was touched, so `audit/recompute.py` was not
run again (last run: 0 differences).

The rule: selecting something shows its information and moves nothing; only a button that says so moves the map.

### What was changed

| Where | Before | Now |
|---|---|---|
| A detection on the map | The map flew to zoom 11 and, on a phone, the page scrolled. | The detection is ringed where it is and its card opens. Centre, zoom and scroll stay. |
| The card's actions | "Back to the whole region", "Close", and "Report ..." at the bottom of the card. | "Zoom in here" first (flies to zoom 11, keeps the zoom if already closer, no animation under reduced motion), then "Report for this place and day" and "Close". After zooming the first button reads "Back to the previous view". |
| A row of the detections table | Opened the card, flew the map and scrolled the page up to it. | Opens the card and rings the detection; nothing moves. When the map is not on screen (and on a phone) the card is a panel fixed to the window, so it is readable without scrolling. If the detection is outside the current map view the card says "This detection is outside the current map view. The map has not moved." and its first action reads "Show on the map". |
| A daily bar in "Fire activity over time" | Selected the day and fitted the map to its detections. | Selects the day; the map keeps its view. |
| The Days button | Went to the busiest day and fitted the map to it. | Goes to the busiest day; the map keeps its view. |
| The busy-day links in "What you are looking at" | Fitted the map to the day. | Change the day only. |
| Go to (date field) | Fitted the map to the day. | Changes the day only. |
| "List its detections" in a day's preview card | Fitted the map as well as listing. | Lists; the map keeps its view. |
| A grid cell | Its popup could pan the map to fit itself. | The popup opens without panning. |
| The line "Opened: ..." naming the selected detection | Appeared above the table and pushed the page down by its height (24 px measured on the phone, Vietnam region). | Is under the table, so nothing above the reader's position changes. |
| The locator inset, the list rows of "burned most", the month row, the calendar, the step buttons, Months, Years, All years | Already moved nothing. | Unchanged; measured below. |

Buttons that still move the map, because they say so: "Zoom in here", "Show on the map", "Back to the previous
view", "Zoom to this area", "Open the busiest day", "Open this day and fit the map" (renamed from "Open this day"),
the link "Open this point at zoom 14", and "Whole region" / "Use this area". Choosing a region or a state is
navigation and fits the map to it. The one exception to "nothing moves" is item 4 of the brief: on desktop, if the
card would lie over the ringed detection, the map slides sideways by just enough to clear it.

The same sentence is now in the legend ("Select a square or a cell to read about it; the map moves only when you
press a button that says so."), in "How to read this" ("Select to read, press a button to zoom."), in the notes
under the table and the charts, and in README ("Select to read, press a button to zoom").

### Measurements

For each kind of click the map's centre (5 decimals), its zoom and the page's scroll position were read before
and 1.3 s after, at 1440x900 and 390x844, on the whole country, California, Hawaiʻi and the Vietnam region:
168 steps, reduced motion on, console clean.

| Kind of click | Result in all 8 combinations |
|---|---|
| Tap a detection on the map | equal; card open, ring drawn, first action "Zoom in here" |
| "Zoom in here" | moved; button then reads "Back to the previous view" |
| "Back to the previous view" | moved back |
| Esc (closes the card) | equal |
| Select a table row | equal after the fix (first run: 24 px of scroll on phone, Vietnam region; re-measured in all 8: equal) |
| Select a row whose detection is outside the view | equal; card says so; first action "Show on the map" |
| "Show on the map" | moved; the detection is then in view |
| Daily bar, step button, Go to a date, busy-day link, area row, Months, month row, calendar cell, Days, Years, yearly bar, All years | equal |
| Select a grid cell | equal. The popup opened in 7 of 8; on the phone, whole country, the tap fell on a blank cell beside the 2-pixel cell aimed at and no popup opened (nothing moved either). |
| "Zoom to this area" | moved |

Card over its own detection (desktop, whole country): with the detection placed 200 px from the map's right edge,
where the card lands, selecting it slid the map 218 px sideways, leaving the point 28 px left of the card; zoom
unchanged. With the detection clear of the card, selecting it changed nothing.

Screenshots: `still_desk_map-card.png`, `still_phone_map-card.png`, `still_desk_row-card.png`,
`still_phone_row-card.png`, `still_desk_outside-card.png`, `still_phone_outside-card.png`,
`still_desk_card-not-over-point.png`, `still_desk_cell.png`, `still_phone_cell.png`. They were taken before the
last two small changes (the "Opened" line moved under the table; the card's three buttons made to fit one line).

Not verified: 1024x768; with motion allowed (the fly animation itself); a real touch device; the 147-cell
overlap check was not repeated after the card became a fixed panel on phones; other states than California. The
phone card is a fixed sheet over the lower part of the window (at most 55% of its height), which replaces the
block under the timeline described in the second pass, because that block could not be seen without scrolling.

## Fifth pass: two loose ends (grid-cell taps on the phone; cards and panels)

Date: 14 Nov 2026. No count or data file was touched; `audit/recompute.py` was not run again.

### 1. A tap on a drawn grid cell showed nothing on the phone

Cause, found by tapping 40 drawn cells of the whole country at 390x844 (12 of 40 showed nothing at the year level):
two things together.
- Zoomed out, a 0.1° cell is one or two pixels wide. A fingertip, and often a mouse, lands on the blank cell beside
  it, and the page looked up exactly the cell under the press.
- After a tap the browser sends made-up mouse events. The hover handler read them as the pointer resting on a
  blank cell and removed the label the tap had just put up. (The month-level popup is not a hover label, which is
  why months mostly worked.)

Fix: a press now selects the nearest drawn cell within reach (14 px for touch, 6 px for a mouse, plus half a
cell); with none in reach it is the cell under the press, as before. The hover uses the same choice, so what is
labelled is what a click selects, and mouse events that follow a touch are ignored for 1.2 s.

Test (kept as a described procedure; the scripts are not in the repository): three drawn cells per region, clear
of panels and spread through the list, tapped at 390x844 and clicked at 1440x900, in the whole country,
California, Texas, New York, West Virginia, Hawaiʻi and the Vietnam region, at month, year and all-years levels.
- Run after the first half of the fix (nearest cell), before the hover fix: 126 taps, 125 showed a count (124 the
  cell aimed at, 1 the drawn neighbour), 1 showed nothing (phone, whole country, year); none moved the map.
- After the hover fix: the failing case re-run with 40 taps: 40 of 40 show a count. The month popup on the phone
  was re-shot. **The full 126-tap run was not repeated after the hover fix.**

Screenshots: `before5/still_phone_cell.png`; after `still_phone_cell.png` (month popup), `still_phone_cell-year.png`.

### 2. Cards and panels

The phone card had become a sheet fixed to the bottom 55% of the window, which could lie over the map and the
timeline's level switch. Changes:
- Both cards (one detection; the preview card of "burned most") follow one placement. Wide window with the map on
  screen: docked on the map's right edge, map controls moved left of it. Otherwise fixed to the window; while
  part of the map or timeline is on screen the card takes the larger free space above or below them and is no
  taller than that space. Placement is redone when the page scrolls or the window changes.
- Only one of the two cards is open at a time.
- While a detection is ringed the legend is put away at every width (it was already on wide screens).

Check: 147 cells (7 regions x 7 levels x 1440x900, 1024x768, 390x844), 1,970 probes. States: as loaded; legend
open; Layers open; preview card open at four scroll positions (map shell at the top of the window, page top,
shell half out of the window, shell low in the window) and with Layers and legend opened; on day cells a
detection card opened by a tap on the rightmost and the leftmost free detection, at the same four scroll
positions and with Layers and legend opened; a card from a table row. Measured: any card or panel over the zoom
buttons, Expand, scale, coordinates, attribution or any timeline control (the level switch included), over
another panel, a fixed card over the map, a card outside the window, the ringed detection under a card or panel.

Result of that run, made with the new placement but before the legend rule: 26 issues of two kinds, console clean.
- Phone, 14 day cells: with a detection card open, a legend the reader then opened lay over the ring. Fixed by
  the legend rule above.
- 1024x768, 12 day cells: "card did not open on a tap". This was the test, not the page: the first card slid the
  map (the card-over-its-detection rule), and the second tap used coordinates taken before the slide.
No card over the map, a control, the level switch or another panel was found in any cell at any scroll position.

**The full run was started again after the legend fix and the test correction, and was stopped before it finished,
so there is no complete 147-cell result for the final page.** What was checked on the final page instead:
- Phone, whole country, card opened by a tap: legend not displayed; card top 8 px below the map shell's bottom;
  card not over the shell; every button of the level switch is the top element at its own centre.
- 1024x768, whole country: two taps with fresh coordinates, both open the card, ring clear of the card.
Screenshots: `before5/still_phone_map-card.png`; after `still_phone_map-card.png`,
`still_phone_map-card_page-top.png` (card above the map when the map is low in the window; this one was taken
before the legend rule and still shows an open legend).

Not fixed, noted: at 1024x768 in 4 cells (Texas month, year, all years; Hawaiʻi all years) the docked preview
card lies over the highlighted marker of the area it describes. The map is not slid for a preview, because the
preview's rule is that it moves nothing and Next would make the map jump at every step.
The grid-cell popup opens upward and, near the top right of a small map, part of it sits under the zoom buttons;
the buttons stay usable.
