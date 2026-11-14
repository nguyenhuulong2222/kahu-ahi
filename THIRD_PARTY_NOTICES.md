# Third-Party Notices

Add each dependency when it is first used. Versions come from the lock files.

## Python (data pipeline)

None. The pipeline (`pipeline/*.py`) uses only the Python standard library.

## JavaScript (web app)

| Library | License | Used for |
|---|---|---|
| [Leaflet](https://leafletjs.com) 1.9.4, loaded from cdnjs (`https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js` and `leaflet.min.css`) with Subresource Integrity hashes | BSD 2-Clause. Copyright (c) 2010-2023, Volodymyr Agafonkin; Copyright (c) 2010-2011, CloudMade. Full text: https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE | The map: basemap display, grid cells, detections, the area rectangle |

| [esri-leaflet](https://github.com/Esri/esri-leaflet) 3.0.19, from jsDelivr (`https://cdn.jsdelivr.net/npm/esri-leaflet@3.0.19/dist/esri-leaflet.js`) with an SRI hash | Apache License 2.0, Copyright Esri | Required by esri-leaflet-vector; adds Esri's attribution |
| [esri-leaflet-vector](https://github.com/Esri/esri-leaflet-vector) 4.3.2, from jsDelivr (`https://cdn.jsdelivr.net/npm/esri-leaflet-vector@4.3.2/dist/esri-leaflet-vector.js`) with an SRI hash. Bundles [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) (BSD 3-Clause) | Apache License 2.0, Copyright (c) 2025 Esri | Draws the Esri `arcgis/imagery` basemap style at zoom 9 and closer. Loaded only when the map first reaches zoom 9 |

The SRI hashes in `docs/index.html` were computed from the files cdnjs and jsDelivr served on 14 Nov 2026 (HST). The page uses no Leaflet default marker icons or layer control, so Leaflet's bundled images are never requested.

## Map tiles and basemap data

| Source | Terms | Attribution shown in app |
|---|---|---|
| NASA GIBS, layer `BlueMarble_ShadedRelief_Bathymetry` ("Blue Marble Shaded Relief and Bathymetry (MODIS)"), WMTS EPSG:3857, tile matrix set `GoogleMapsCompatible_Level8`: `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`. Shown at zoom 8 and below. | NASA imagery; no key. GIBS asks users to add this acknowledgment: "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)." (https://nasa-gibs.github.io/gibs-api-docs/). NASA does not endorse this project. | In the map corner: "Imagery: NASA GIBS Blue Marble" linked to the GIBS API page. The full acknowledgment sentence is in the page footer. |
| NASA GIBS reference overlays `Reference_Features` ("Reference Features (OSM)": coastlines and borders) and `Reference_Labels` ("Reference Labels (OSM)": place names), tile matrix set `GoogleMapsCompatible_Level9`, PNG. Shown at zoom 8 and below. | Served by GIBS; built from OpenStreetMap data, so the OpenStreetMap terms below apply as well. | Covered by the same "© OpenStreetMap contributors" line, plus the GIBS acknowledgment. |
| Esri World Imagery, through the ArcGIS basemap styles service (style `arcgis/imagery`, https://basemapstyles-api.arcgis.com/arcgis/rest/services/styles/v2/styles/arcgis/imagery). The style combines World Imagery raster tiles (`ibasemaps-api.arcgis.com`) with Esri's vector reference layer of boundaries, roads and place names (`basemaps-api.arcgis.com`). Shown at zoom 9 and closer. | ArcGIS Location Platform, used with a public basemap API key restricted by referrer. Terms: Esri Master Agreement https://www.esri.com/en-us/legal/terms/full-master-agreement and Product-Specific Terms https://www.esri.com/en-us/legal/terms/product-specific-scope-of-use. Attribution guidance: https://developers.arcgis.com/documentation/esri-and-data-attribution/ (the page renders in a browser only; its text could not be read on 14 Nov 2026, so the attribution follows Esri's own esri-leaflet implementation). | While the Esri layer is on the map, esri-leaflet adds "Powered by Esri" and the credits for the area in view, for example "California State Parks, Esri, Earthstar Geographics, TomTom, Garmin, …" or "Vantor, Esri, TomTom, Garmin, METI/NASA, USGS". They are removed when the layer is. |
| OpenStreetMap standard tile layer, `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | Map data © OpenStreetMap contributors, available under the Open Data Commons Open Database License (ODbL): https://www.openstreetmap.org/copyright. Tile use follows the OSMF Tile Usage Policy: https://operations.osmfoundation.org/policies/tiles/ (HTTPS only, visible attribution, no bulk or offline download, no API key). Shown in colour at zoom 9 and above when Esri imagery is unavailable (no key, refused, or not loaded within 15 seconds), and underneath the imagery until it has drawn. | In the map corner: "© OpenStreetMap contributors" linked to https://www.openstreetmap.org/copyright, and "Report a map issue" linked to https://www.openstreetmap.org/fixthemap. Also in the page footer. |

No tile is changed or stored by the page.

The `_15m` versions of the GIBS reference layers were tried first and not used: on 14 Nov 2026 they returned HTTP 500 for some tiles and blank tiles for others, while the `GoogleMapsCompatible_Level9` versions answered every request.

CARTO basemaps were considered and not used: their terms (last updated 29 September 2026) tie free use to a CARTO-issued API key and allow watermarking requests without one. At that point the project used no API keys; the one key it now uses is Esri's public basemap key described above.

The Esri static basemap tiles service was tried first for imagery: on 14 Nov 2026 its `arcgis/imagery` style returned HTTP 404 ("Path not found"), and only the labels style `arcgis/imagery/labels` was offered, so imagery comes from the basemap styles service instead.

## Fonts, icons, images

None. The page uses the reader's system fonts and no icon or image files.
