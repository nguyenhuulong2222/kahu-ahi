# Third-Party Notices

Add each dependency when it is first used. Versions come from the lock files.

## Python (data pipeline)

None. The pipeline (`pipeline/*.py`) uses only the Python standard library.

## JavaScript (web app)

| Library | License | Used for |
|---|---|---|
| [Leaflet](https://leafletjs.com) 1.9.4, loaded from cdnjs (`https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js` and `leaflet.min.css`) with Subresource Integrity hashes | BSD 2-Clause. Copyright (c) 2010-2023, Volodymyr Agafonkin; Copyright (c) 2010-2011, CloudMade. Full text: https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE | The map: basemap display, grid cells, detections, the area rectangle |

The SRI hashes in `docs/index.html` were computed from the files cdnjs served on 14 Nov 2026 (HST). The page uses no Leaflet default marker icons or layer control, so Leaflet's bundled images are never requested.

## Map tiles and basemap data

| Source | Terms | Attribution shown in app |
|---|---|---|
| NASA GIBS, layer `BlueMarble_ShadedRelief_Bathymetry` ("Blue Marble Shaded Relief and Bathymetry (MODIS)"), WMTS EPSG:3857, tile matrix set `GoogleMapsCompatible_Level8`: `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`. Shown at zoom 8 and below. | NASA imagery; no key. GIBS asks users to add this acknowledgment: "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)." (https://nasa-gibs.github.io/gibs-api-docs/). NASA does not endorse this project. | In the map corner: "Imagery: NASA GIBS Blue Marble" linked to the GIBS API page. The full acknowledgment sentence is in the page footer. |
| NASA GIBS reference overlays `Reference_Features` ("Reference Features (OSM)": coastlines and borders) and `Reference_Labels` ("Reference Labels (OSM)": place names), tile matrix set `GoogleMapsCompatible_Level9`, PNG. Shown at zoom 8 and below. | Served by GIBS; built from OpenStreetMap data, so the OpenStreetMap terms below apply as well. | Covered by the same "© OpenStreetMap contributors" line, plus the GIBS acknowledgment. |
| OpenStreetMap standard tile layer, `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | Map data © OpenStreetMap contributors, available under the Open Data Commons Open Database License (ODbL): https://www.openstreetmap.org/copyright. Tile use follows the OSMF Tile Usage Policy: https://operations.osmfoundation.org/policies/tiles/ (HTTPS only, visible attribution, no bulk or offline download, no API key). Shown in colour at zoom 9 and above, where GIBS imagery runs out. | In the map corner: "© OpenStreetMap contributors" linked to https://www.openstreetmap.org/copyright, and "Report a map issue" linked to https://www.openstreetmap.org/fixthemap. Also in the page footer. |

No tile is changed or stored by the page.

The `_15m` versions of the GIBS reference layers were tried first and not used: on 14 Nov 2026 they returned HTTP 500 for some tiles and blank tiles for others, while the `GoogleMapsCompatible_Level9` versions answered every request.

CARTO basemaps were considered and not used: their terms (last updated 29 September 2026) tie free use to a CARTO-issued API key and allow watermarking requests without one, and this project uses no API keys.

## Fonts, icons, images

None. The page uses the reader's system fonts and no icon or image files.
