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
| OpenStreetMap standard tile layer, `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | Map data © OpenStreetMap contributors, available under the Open Data Commons Open Database License (ODbL): https://www.openstreetmap.org/copyright. Tile use follows the OSMF Tile Usage Policy: https://operations.osmfoundation.org/policies/tiles/ (HTTPS only, visible attribution, no bulk or offline download, no API key). | In the map corner: "© OpenStreetMap contributors" linked to https://www.openstreetmap.org/copyright, and "Report a map issue" linked to https://www.openstreetmap.org/fixthemap. Also in the page footer. |

The tiles are shown in greyscale with a CSS filter in the browser; the tile images themselves are not changed or stored.

CARTO basemaps were considered and not used: their terms (last updated 29 September 2026) tie free use to a CARTO-issued API key and allow watermarking requests without one, and this project uses no API keys.

## Fonts, icons, images

None. The page uses the reader's system fonts and no icon or image files.
