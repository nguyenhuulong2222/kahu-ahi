# UI and quality review before submission

Date: 14 Nov 2026 (HST). Reviewer: outside the build team. Commit reviewed: `bd57e3d`.
Page: http://localhost:8000 (served from `docs/`), Chromium 131 through Playwright 1.49, at 1440x900 (desk),
1024x768 (mid) and 390x844 (phone, touch and mobile viewport). Nothing under `docs/` or `pipeline/` was changed.

Screenshots are in `review/` (not committed; excluded locally). File names are given with each finding.

README.md, QA.md and AUDIT.md were read first. Items they already record (teal with two meanings, the native date
field's format, the gold focus ring on white, totals that differ by design for a state, the preview card over its
own marker at 1024x768, the grid-cell popup under the zoom buttons, the AUDIT "Remains" list) are not repeated here.

Route followed, as a first-time visitor, at each size: first screen; select a detection on the map; Zoom in here and
Back; Esc; Play for about 8 s and pause; Months, Years, All years, Days; State = Texas, then New York; "Where and
when it burned most" for Texas, Nov 2026; preview card, Next, Zoom to this area, Open the busiest day; the detections
table, a row, its card, "Report for this place and day"; the calendar (a cell, "Compared with the usual", the
VIIRS-only record); This month so far; By state; trust and compare; both downloads (2025 hotspots, 67 MB, and the
monthly table, 43 kB: both arrived); footer.

Not covered: Hawaiʻi and the Vietnam region, Layers, Expand map, drawing an area, keyboard-only use, a screen
reader, print, other browsers, real phones. Console: no errors from the page at any size (only Chromium's own
software-WebGL warnings, which come from the headless test machine).

---

## 1. First impression (first 10 seconds)

**What a visitor understands**

- This is about satellite fire detections, with a map of the United States and red squares on it.
- There is a time slider and a date (14 Nov 2026), so it is a history that can be stepped through.
- NASA is retiring the older satellites (the grey lede at 1440 and 1024; on the phone the lede is hidden).
- It is a NASA-data project with a Hawaiian name, and it is serious and careful (many caveats).

**What a visitor would not understand**

- **What the result is.** The bold line under the title is the first thing read and it is three percentages:
  "VIIRS as recorded is off by 563.8%; with one whole-year ratio, 28.2%; with monthly factors, tested on years
  left out, 10.4%." A non-expert cannot tell whether that is good, what "off" is measured against, or that 10.4%
  is the answer. The plain sentence that says what the project does ("The record shown is MODIS Aqua; VIIRS,
  converted to its scale and tested, continues it") is styled as grey small print above it.
- **What MODIS, VIIRS, Aqua, harmonized and "factor" are.** None is defined above the fold; "How to read this"
  is about two screens down.
- **What the numbered circles with yellow "+3", "+2", "+1" badges are.** On the first screen at 1440 they sit on
  the densest group of red squares in the South-east and are the most eye-catching thing on the map
  (`01_first_desk.png`). The explanation is the fourth line of the legend.
- **That 14 Nov is an incomplete day.** The page opens on it with "64 detections" and no word that the day was
  still being observed when the files were made (see defect 2).
- **On the phone, that there is more to the page sideways**: it scrolls horizontally by 12 px (defect 1).

---

## 2. Defects, most serious first

### D1. Phone: the page is wider than the screen, and fixed cards run off its right edge

- **Size:** 390x844.
- **Steps:** open http://localhost:8000/ on the phone; swipe left. Then open any detection card or preview card.
  Then open a report ("Report for this place and day").
- **What happens:** the page is 402 px wide on a 390 px screen. The cause is the calendar's "Colour shows" select,
  which is 12 px wider than its column (right edge at 402 px). Because the page is wider, every card fixed to the
  window is 402 px wide too, so its right 12 px are off-screen, and the browser zooms out the layout so the
  preview card's bottom buttons ("Zoom to this area", "List its detections") open below the visible screen.
  With a report open the page grows to **474 px**: the report's "Address of this report:" link is one unbroken URL
  (437 px wide) and pushes the whole page sideways.
- **Screenshots:** `01_first_phone.png` (layout), `02_phone_hscroll.png` (scrolled sideways),
  `15_calendar_phone.png` (the select cut at the right edge), `03_card_phone.png` (card 402 px wide),
  `10_preview_phone.png` (buttons below the screen), `14_report-link-overflow_phone.png` (URL off the edge, page
  shifted).
- **Fix:** `max-width: 100%` on `#mode` (and selects in general); `overflow-wrap: anywhere` on the report's
  address link, or show it as a "Copy link" button.

### D2. The page opens on 14 Nov, a day still being observed, and a state can open on an empty map

- **Size:** all.
- **Steps:** open http://localhost:8000/. Then choose State = Texas, then New York.
- **What happens:** the default view is 14 Nov 2026, the last date in the download. README ("Partial-month
  comparison") says that day is left out of the month-to-date comparison because "that day was still being
  observed when the files were made", and the page's own "This month so far" uses 1 to 13 Nov. Yet the map, the
  timeline and "Where and when it burned most" present 14 Nov as a normal day ("64 detections counted across the
  contiguous United States"), with no word that it is incomplete. Switching to Texas keeps 14 Nov and shows an
  empty map with the box "MODIS Aqua has data for this period but recorded no detection in Texas on 14 Nov 2026".
  The afternoon Aqua pass over Texas may simply not have been in the download yet. New York does the same. The
  first thing a visitor sees after choosing a state is an empty map.
- **Screenshots:** `01_first_desk.png`, `07_state-Texas_desk.png`, `07_state-NewYork_desk.png`,
  `07_state-Texas_phone.png`.
- **Fix:** open on the last *complete* day (data_through minus one, as the month-to-date does). Or label 14 Nov
  "still being received" wherever it appears. Choosing a state should also land on that state's last day with a
  detection, as the whole-country view does.

### D3. Phone: the "no detection" box covers the Legend button and the scale bar

- **Size:** 390x844.
- **Steps:** open `#region=conus&state=TX&day=2026-11-14` (or choose Texas as in D2).
- **What happens:** the empty-period message box spans the map from 512 px to 654 px down. It lies over the scale
  bar and over the Legend button; at the Legend button's centre the top element is the message box, so the
  button cannot be tapped. It also hides most of Texas.
- **Screenshot:** `07_state-Texas_phone.png`.
- **Fix:** on the phone, place the message above the map or as a one-line strip at the top of the map, clear of
  the bottom-corner controls.

### D4. A card opened from a list or table lies over that list or table

- **Size:** 1440x900 and 1024x768 (the map not on screen).
- **Steps (preview card):** open `#region=conus&state=TX&month=2026-11`, scroll to "Where and when it burned
  most", select "near Plum Grove".
- **What happens:** the card is fixed to the right of the window and covers the right half of the area list at
  1440 (the highlighted row's county and dates are cut off under it) and the whole "Top 5 days" list at 1024. To
  compare the card with the list, the visitor has to close it.
- **Steps (detection card):** in the same view, "Open the busiest day", then select the first time in the
  detections table.
- **What happens:** the card covers the table's Counted column and part of Radiative power for the rows below the
  selected one.
- **Screenshots:** `10_preview_desk.png`, `10_preview_mid.png`, `12_rowcard_desk.png`.
- **Note:** QA.md records the preview card over its marker at 1024x768, not over the list it came from.
- **Fix:** when the map is not on screen, place the card in the page's empty margin. Or, where no margin exists,
  give the list a right padding equal to the card's width while the card is open.

### D5. 1024x768: the timeline's level switch is cut by the bottom of the first screen

- **Size:** 1024x768.
- **Steps:** open http://localhost:8000/.
- **What happens:** the timeline wraps to two rows (691 to 791 px), and the second row, with Days, Months, Years
  and All years, is cut in half at 768 px. The control that changes what the whole page shows is half visible
  until the visitor scrolls.
- **Screenshot:** `01_first_mid.png`.
- **Fix:** at this width, reduce the step buttons to arrows (as on the phone) so the timeline fits one row. Or
  take the 100 px from the map's height.

### D6. Detection card: "Close" wraps onto its own line at every size

- **Size:** all.
- **Steps:** select any detection on the map.
- **What happens:** "Zoom in here" and "Report for this place and day" fill the first row, and "Close" drops
  alone to a second row on the right, leaving an empty band on its left. After "Zoom in here", "Back to the
  previous view" takes the first row alone and the other two take the second. QA.md (fourth pass) says the
  three buttons were "made to fit one line"; at 380 px wide they do not.
- **Screenshots:** `03_card_desk.png`, `03_card_phone.png`, `04_zoomed_mid.png`.
- **Fix:** make Close an icon-sized "×" in the card's top-right corner, or shorten "Report for this place and
  day" to "Report".

### D7. The year 2026 has two different totals and the map does not say the year is incomplete

- **Size:** all.
- **Steps:** press Years (2026); then look at the calendar's 2026 row.
- **What happens:** the map sentence says "2026, MODIS Aqua: 51,801 detections …" with no word that the year
  is not over and the last months are provisional (the Months level does say "The month is not complete.
  Provisional data."). The calendar's year total for 2026 is "50,381 (10 mo)". The difference is November,
  counted on the map and left out of the calendar's total; a visitor sees two totals for one year.
- **Screenshots:** `06_level-Years_desk.png`, `15_calendar_desk.png`.
- **Fix:** add "The year is not complete; Sep to Nov are provisional." to the year sentence, and write the same
  rule in both places (either both include the current month, or both say "to Oct").

### D8. By state: the letters on the hatched states cannot be read

- **Size:** all; worst on the phone.
- **Steps:** whole country, scroll to "By state".
- **What happens:** the state letters on the twelve hatched (not harmonized) states are 9 px SVG text, 7 px
  tall on screen, over a diagonal hatch, in the crowded Northeast. "MA", "RI", "CT", "NJ", "DE", "DC" overlap
  the coast and each other.
- **Screenshot:** `20_bystate_desk.png`.
- **Fix:** list the twelve states under the map as text ("Not harmonized: Connecticut, Delaware, …"); keep the
  hatch on the map without letters.

### D9. Smaller inconsistencies

- **Calendar numbers in two formats.** Most cells show the full number ("9,888") while the busiest months show
  "11k", "13k", "17k", "23k". The busiest months are the ones a visitor wants to read exactly.
  `15_calendar_desk.png`. Fix: smaller type in those cells instead of rounding, or "k" everywhere above 9,999
  with the exact value on focus.
- **The card's locator dot sits on the box edge** for a point near the region's edge (Texas, 26.39° N): half of
  the red dot is outside the locator box. `12_rowcard_desk.png`. Fix: 4 px inner padding in the locator's
  projection.
- **Phone step buttons have no words.** At 1440 the steps read "« Month ‹ Day Day › Month »"; on the phone they
  are "« ‹ › »" (and Play is "▶" only), so which arrow steps a day and which a month is not shown.
  `03_card_phone.png`, `06_level-Years_phone.png`. Fix: keep the short words ("Day", "Mo") under the arrows.

---

## 3. Wording a non-expert would not understand

| Where | Now | Suggested |
|---|---|---|
| Bold line under the title (and "See the result") | "Contiguous United States: VIIRS as recorded is off by 563.8%; with one whole-year ratio, 28.2%; with monthly factors, tested on years left out, 10.4%." | "Contiguous United States: the newer VIIRS satellites count about 6.6 times as many fire detections as the older MODIS Aqua. Corrected month by month, VIIRS comes within 10.4% of Aqua in years it was not built from." |
| Harmonization result, step 3 | "Factors run from 4.536 (February) to 9.204 (August) VIIRS detections per Aqua detection" | "VIIRS sees between 4.5 (February) and 9.2 (August) detections for every one that MODIS Aqua sees." |
| Harmonization result, step 2 | "off, tested on years left out; the fair comparison for step 3" | "off, tested the same way. This simpler correction is what step 3 has to beat." |
| "tested on years left out" (headline, band, trust section) | "tested on years left out" | "tested on years the method had not seen" |
| New York (and other refused states), step 3 | "Not harmonized. Off by 49.9%; the limit is 50%. Only 8 of 12 calendar months have enough detections for a factor (9 needed)." Read quickly, 49.9% under a 50% limit looks like a pass. | "Not converted: too few fires here. Only 8 of the 12 months have enough MODIS Aqua detections to work out a correction, and 9 are needed. (The error test, 49.9%, only just passed its 50% limit.)" |
| Calendar and map legends | "(each step is a multiple, not an amount)" | "(each colour covers a wider range than the one before: 1, 2–4, 5–10, …)" |
| Map legend | "Squares show the sensor's footprint at nadir" | "Each square is the size of one satellite pixel (about 1 km for MODIS, 375 m for VIIRS)." |
| How to read this; detections notes | "larger at the edge of the swath" | "larger near the edge of the area the satellite scans" |
| Layers, Satellite | "Harmonized (as the calendar)" | "Combined record (as in the calendar)" |
| How to read this | "Counted detections are those FIRMS types as a presumed vegetation fire with nominal or high confidence" | "Counted detections are those NASA's fire data mark as a likely vegetation fire, leaving out low-confidence ones." |
| What you are looking at | "NOAA-20, converted to the MODIS Aqua scale, gives about 1,784." | "The newer NOAA-20 satellite, corrected to match MODIS Aqua, suggests about 1,784." |
| Detection card, whole country | "Satellite pass, local time: Not shown for this region. It spans four time zones, and this page carries no time-zone boundaries to tell which one a point is in, so times are given in UTC only." | "Local time: not shown (this region spans several time zones). Times are in UTC." |
| Detection card | "Fire radiative power 58.58 MW" | "Heat given off (fire radiative power): 58.6 MW" |
| Detection card | "Confidence, as given by FIRMS" | "How sure the satellite was (NASA FIRMS)" |
| By state table | "Factor months" | "Months with their own correction" |
| By state table | "Error, national factors" | "Error with the whole-country correction" |
| Harmonization result | "Converted VIIRS runs beside it from 2012 as the tested successor" | "Corrected VIIRS data, available from 2012, is ready to take over when Aqua stops." |
| Everywhere a date is given | "UTC date" (first use, unexplained) | "UTC date (Greenwich time; Hawaiʻi is 10 hours behind)" at the first use; "UTC" after that. |

---

## 4. The three weakest points of the visual design

### W1. The first screen gives the plain explanation the least weight and the jargon the most

The one sentence that says what the project does (the lede) is in the same grey (#55627a) and nearly the same size
as the footnotes, footer and name note. Directly under it, the three-percentage headline is bold and dark, so the
eye lands on "563.8%" first. In the harmonization band the three steps are three equal columns, and the largest
number (563.8%) reads as the result.

**Smallest change:** give `.lede` the body text colour and make `.headline` normal weight. In the band, give step 3
a tinted background and a heavier border so the answer stands apart from the two baselines.
(`01_first_desk.png`, `03_card_desk.png`)

### W2. At country zoom the map's data is fainter than its markers

On the whole country at the Months level, the 0.1° cells are one or two pixels wide and the lowest steps are
30% opaque on the dark Blue Marble, so November looks almost empty. The numbered area markers with yellow
badges are the strongest marks on the map. On the opening day view, ten markers and three "+N" badges sit on top
of the very detections they describe.

**Smallest change:** raise the lowest opacity in `STEP_OPACITY` from 30% to about 60%. Default "Show" to 5 for the
whole country (it is 10), so fewer markers and badges are drawn on the first screen.
(`06_level-Months_mid.png`, `01_first_desk.png`)

### W3. Information is shown as long paragraphs in narrow two-column grids

Card, report and preview rows are label/value grids where the value column is about half the card. On the phone
the report's Place cell wraps into a 12-line column of two or three words per line, and the detection card spends
its first visible rows on a three-line note about time zones. Many sections open with a paragraph of caveats in
grey before their content.

**Smallest change:** below 600 px, stack each label above its value (one CSS rule on the card and report `dl`
grids). Move the fixed caveats (time zones, "not the exact spot of the fire") to one line at the bottom of the
card. (`13_report_phone.png`, `03_card_desk.png`, `10_preview_phone.png`)

---

## How the review was run

- Playwright 1.49.1 was installed in a scratch folder with npm. `playwright install chromium` downloaded the
  archive but hung while unpacking it; the archive was checked (no bad entries) and unpacked by hand. The full
  Chromium 131 binary was then used through `executablePath`, not the headless shell.
- Overflow was measured as elements whose right edge passes the window and that no ancestor clips. Overlaps were
  measured with element rectangles and `elementFromPoint` at the covered control's centre.
- Detections were selected by real taps or clicks at their screen positions, computed from the page's own drawn
  rows. One apparent defect, a ring beside the square after "Zoom in here" (`04_zoomed_mid.png`), turned out to be
  two detections 0.8 km apart that overlap at the lower zoom; it is not listed.
