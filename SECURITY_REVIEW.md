# Security review before submission

Date: 15 Nov 2026 (14 Nov HST). Read-only review: nothing under `docs/` or `pipeline/` was changed, and nothing was fixed.

- **Commit reviewed:** `74dcde0` on `main` ("Merge pull request #1 from nguyenhuulong2222/fix/ui-tiffanie"), fetched explicitly from `origin/main`. This branch, `review/security-tiffanie`, starts there.
- **PR #1 is merged into it.** GitHub reports PR #1 as merged on 15 Nov 2026 08:58 UTC with merge commit `74dcde0`, and the branch's last commit `c27ee23` is an ancestor of `74dcde0`.
- **The clone is shallow.** Only 17 commits are available, the oldest dated 14 Nov 2026. Older history was **not** scanned (see "Not checked").
- **Page tested:** `docs/index.html` at `74dcde0`, served at http://localhost:8000 (the server shows whichever branch is checked out; this one was), in Chromium 131 through Playwright.

## Summary

No leaked secret was found: no FIRMS MAP_KEY, token, password, private key or `.env` file in the working tree or in the 681 blobs of the available history. The one credential in the repository is the Esri basemap key, which is meant to be public (F1).

No path from data or user input to script execution was found. Static reading found every DOM write either text-only or built from numbers and the page's own strings. Eleven hostile links (HTML and `javascript:` payloads in every hash parameter) were tried in the browser: none ran, none inserted an element.

| # | Finding | Severity | Where |
|---|---|---|---|
| F1 | Public Esri API key in the page; its referrer restriction and usage limits could not be verified | Low | `docs/index.html:612` |
| F2 | Bundled MapLibre GL JS 4.7.1 is in the range of a critical advisory (GHSA-jrc7-96c5-q579); the vulnerable path is not used by this page | Low | `docs/index.html:1968` (esri-leaflet-vector 4.3.2) |
| F3 | CSV formula injection is possible in principle for town names in the detections-table CSV; no current value triggers it | Low | `docs/index.html:3455`, `3457` |
| F4 | No Content-Security-Policy | Low (hardening) | `docs/index.html:3–4` (head) |
| F5 | Pipeline inputs are hashed but not checked against the recorded hashes | Low | `pipeline/ingest.py:144`, `pipeline/places.py:86` |
| F6 | Visitors' viewed locations go to third-party services | Info (privacy) | `docs/index.html:3109` and the tile/imagery hosts |

---

## Findings

### F1. Public Esri API key: restriction and limits not verifiable from here (Low)

- **Where:** `docs/index.html:612` (`ESRI_API_KEY`). The same single key value is in every version of the file in the available history (16 occurrences, one distinct value, compared by hash; the value is not reproduced here).
- **What it is:** an ArcGIS Location Platform basemap key. README ("How to run") states it has basemap privileges only and is restricted to the referrers `https://nguyenhuulong2222.github.io` and `http://localhost`. A browser basemap key has to be in the page to work, so this is not a leak in itself.
- **How it could be abused:** anyone can copy the key from the public page or repository. A referrer restriction stops other web pages from using it in a browser, but a script outside a browser can send any `Referer` header. Such a script could spend the account's basemap quota, or run up charges if the account is billed. The `http://localhost` referrer also lets anyone use the key from a page on their own machine.
- **Not verified:** whether the restriction is actually set, and whether the account has a usage cap or alerts. That needs the ArcGIS dashboard. The key was not used from another origin to test it.
- **Smallest fix:** in the ArcGIS dashboard, confirm the two referrers and the basemap-only privilege, set a monthly usage limit or alert, and consider dropping `http://localhost` from the published key (use a separate local key). Rotate the key if the restriction turns out to be missing.

### F2. MapLibre GL JS 4.7.1 inside esri-leaflet-vector is within a critical advisory's range, but the vulnerable path is not used (Low)

- **Where:** `docs/index.html:1968` loads `esri-leaflet-vector@4.3.2` from jsDelivr, at map zoom 9 and closer. The file bundles MapLibre GL JS **4.7.1** (version string in the bundle; README and the code comment at line 1966 say MapLibre is bundled).
- **Advisory:** GHSA-jrc7-96c5-q579 (CVE-2026-85061), "XSS Sanitizer Bypass in DOM.sanitize() via Live NamedNodeMap Removal Skip". Severity critical, affects `maplibre-gl <= 6.4.0`, patched in 6.4.1. `npm audit` on the three pinned libraries reports it through `esri-leaflet-vector`; its suggested fix (esri-leaflet-vector 3.1.5) is a downgrade, not a fix.
- **Why it does not apply here as used:** the advisory's attack is a hostile *attribution string* in a map style source, rendered by MapLibre's attribution control.
  - On this page MapLibre's attribution control is never created (0 `.maplibregl-ctrl-attrib` elements at zoom 10, measured).
  - The Esri attribution is shown by Leaflet's control instead. Its text comes only from Esri's style service over HTTPS.
  - The bundle does not contain the `DOM.sanitize` function the advisory describes (no `sanitize`, `parseFromString` or `NamedNodeMap` in the file).
  - The page adds no style source or attribution of its own to MapLibre.
- **Residual risk:** Leaflet's attribution control inserts attribution strings as HTML without sanitizing them (Leaflet's design). Esri's attribution HTML is therefore trusted. That is the same trust as running Esri's library at all; it is not a new exposure.
- **Smallest fix:** none needed for the current use. Do not enable MapLibre's attribution control or add third-party style sources. When esri-leaflet-vector publishes a build bundling MapLibre 6.4.1 or later, update the URL and its `integrity` hash (line 1968).

### F3. CSV formula injection: possible in principle, not triggered by current data (Low)

- **Where:** the detections-table CSV ("Download these rows"). `q()` at `docs/index.html:3455` wraps a cell in double quotes, and line 3457 writes the GeoNames town name (`nearest_town`) and its admin area (`town_is_in`) through it. Quoting does not stop Excel or LibreOffice from reading a cell such as `"=HYPERLINK(...)"` or `"@SUM(...)"` as a formula.
- **The other CSVs:**
  - The report CSV (line 3094), the full-period download (streams the pipeline's hotspot files as they are) and the monthly table (`q()` at line 3683) contain only FIRMS codes, dates, numbers and the page's own words. The hotspot files' columns are `acq_date, acq_time, latitude, longitude, sensor, quality, confidence, frp, daynight, type, counted` in all four regions.
  - Negative values such as `-97.8625` are read as numbers, not formulas.
- **Current data:** none of the 62,728 strings in `docs/data/places/*.json` (all five regions) starts with `=`, `+`, `-`, `@`, tab or carriage return. The Nominatim answer is not written to any CSV.
- **How it could be abused:** GeoNames is community-edited. A place name beginning with `=` or `@` that reached a future data refresh would become a formula in the downloaded CSV, for example a `HYPERLINK` that sends a click to an attacker's site, or a DDE payload in older Excel versions.
- **Smallest fix:** in `q()` (line 3455), prefix a single quote to any text cell that starts with `=`, `+`, `-`, `@`, tab or CR. Or reject such names in `pipeline/places.py` when the list is built. Apply it to text cells only, not numbers.

### F4. No Content-Security-Policy (Low, hardening)

- **Where:** `docs/index.html` head (lines 3–4); there is no `<meta http-equiv="Content-Security-Policy">`, and GitHub Pages cannot send the header.
- **Why it matters:** no injection path was found (see "Checked and found sound"), so a CSP would only be a second line of defence. It would limit the damage if a future change, or a third-party library, introduced one.
- **Smallest fix:** a `<meta http-equiv="Content-Security-Policy">` that limits:
  - `script-src` to `'self'`, `cdnjs.cloudflare.com`, `cdn.jsdelivr.net` and the inline script's hash (or `'unsafe-inline'` as a first step);
  - `connect-src` and `img-src` to the hosts already listed in THIRD_PARTY_NOTICES.md;
  - `worker-src` to `blob:` (MapLibre uses a blob worker).

  It needs testing at zoom 9 and closer and with each basemap.

### F5. Pipeline inputs are hashed but not verified (Low)

- **Where:** `pipeline/ingest.py:144` computes `sha256_of(path)` of each FIRMS zip and writes it to the schema report; `pipeline/places.py:86` and `pipeline/states.py` record the hashes of the GeoNames and Census files in `data/manifest.json`. No step compares a file with a recorded hash before using it.
- **How it could be abused:** a raw file replaced in `data/raw/` (a tampered or wrong download) would be processed without warning, and its new hash simply recorded. The pipeline makes no network requests and runs no downloaded code, so the risk is wrong data, not code execution.
- **Smallest fix:** before reading a raw file, compare its sha256 with the value in `data/manifest.json`, and stop on a mismatch unless a flag such as `--accept-new-download` is given.

### F6. Third parties see which places a visitor looks at (Info, privacy)

- **Where:** `NOMINATIM_URL` at `docs/index.html:3109` (one reverse lookup with the latitude and longitude of each opened detection), plus tiles and images from NASA GIBS, Worldview Snapshots, Esri and OpenStreetMap.
- **What happens:** these services receive the visitor's IP address and the coordinates viewed. README and THIRD_PARTY_NOTICES.md already list the services. No cookie, `localStorage` or tracking is used by the page itself.
- **Smallest fix:** none required. A one-line note in the page's footer ("Looking up a place sends its coordinates to OpenStreetMap Nominatim") would make it visible to visitors.

---

## Checked and found sound

- **Secrets.** A scan of the working tree and every blob in the available history covered FIRMS MAP_KEY patterns, 32-hex keys near "key/token/secret", Esri, AWS, GitHub, Google, Slack, OpenAI/Anthropic keys, private-key blocks, bearer tokens, password assignments and credentials in URLs. Matched values were never printed. Only the Esri key (F1) was found. No file named like `.env`, `*.pem`, `*.key`, `id_rsa`, `.netrc`, `credentials`, `secrets.*`, `.npmrc` or `.pypirc` exists in the tree or the available history; `.gitignore` excludes `.env`. The mentions of "FIRMS", "Earthdata" and "key" in SOURCES.md and THIRD_PARTY_NOTICES.md are URLs and layer names.
- **DOM writes.**
  - `el()` sets text with `textContent` and appends strings as text nodes; nearly the whole page is built with it.
  - The remaining HTML sinks carry no outside input:
    - `innerHTML` at line 3231 (the locator) receives only numbers from arithmetic and `toFixed`;
    - the Leaflet tooltip at line 2933 gets `cellText()`, made of coordinates, counts and the page's own labels;
    - the marker `divIcon` HTML at line 2182 is rank numbers;
    - the popup at line 2927 is built with `el()`.
  - No `eval`, `new Function`, `document.write` or string timers.
  - The Nominatim answer (the only remote text shown) is written as text.
- **URL hash.**
  - `region`, `state` and `sensor` are accepted only when they match a list option or a known state, so they cannot steer a `fetch` path.
  - `day`, `report`, `at` and `area` are parsed as dates or numbers.
  - Links built from them use `URLSearchParams`, which encodes the values.
  - Tested in the browser with HTML and `javascript:` payloads in `region`, `state`, `day`, `month`, `year`, `sensor`, `view`, `record`, `report`, `at` and `area`, both on load and through a hash change: no script ran, no element was injected, no `javascript:` link appeared, no page error.
- **Third-party scripts and styles.** Exactly three scripts and one stylesheet come from other hosts, each pinned to an exact version with an `integrity` hash and `crossorigin="anonymous"`:
  - Leaflet 1.9.4 JS and CSS from cdnjs (lines 17–18);
  - esri-leaflet 3.0.19 and esri-leaflet-vector 4.3.2 from jsDelivr (lines 1967–1968, loaded with `integrity`).

  All four hashes match the files the CDNs serve today (recomputed). The browser's own record of requests at the opening view and at zoom 10 shows no other script, stylesheet or font. The rest of the traffic is map tiles, Esri style and glyph data, and one blob worker.
- **New-tab links.** One link opens a new tab ("Open this day in NASA Worldview", line 3216) and it has `rel="noopener"`. No static `target="_blank"` links.
- **Pipeline and audit scripts.**
  - No file in `pipeline/` opens a network connection, starts a process, or uses `eval`, `exec` or `pickle`.
  - Zip files are read member by member in memory (`ZipFile.open`/`read`); nothing is extracted to disk, so there is no path traversal ("zip slip").
  - The Census URL in `pipeline/states.py:51` is printed and recorded, not fetched.
  - `audit/county_check.py` is the only script that calls out (Nominatim, about 40 requests). It parses the answer with `json.load` and executes nothing.
  - There are no CI workflows (`.github/` does not exist).

## Not checked

- **Older history:** the clone is shallow (17 commits from 14 Nov 2026). Commits before that, and branches not fetched here, were not scanned. A full clone (`git fetch --unshallow`) and a scan of all refs on GitHub would be needed to rule out a secret committed earlier and later removed.
- **Gzip and image files** were skipped by the secret scan: `docs/data/hotspots/**/*.csv.gz` (FIRMS data, whose columns were checked separately) and PNGs.
- **`data/raw/`** is git-ignored and does not exist in this clone, so the raw downloads were not inspected.
- **The Esri account:** referrer restriction, privileges, quotas and billing (F1).
- **Production headers:** the GitHub Pages site itself was not requested; any headers it sends were not checked.
- **CSV behaviour in Excel** was reasoned from the file contents, not tested in Excel or LibreOffice.
- **Vulnerability databases** beyond `npm audit` and the GitHub advisory for MapLibre. The GeoNames, Census and FIRMS input files were not checked for tampering beyond what F5 describes.
- **Browsers other than Chromium**, and the print view of the report.
