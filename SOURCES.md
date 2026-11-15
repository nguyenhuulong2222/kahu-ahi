# Sources

Every source used in this project is listed here, including free and open ones. Access dates are in HST.

## NASA data

| Product | Description | Access | Date accessed |
|---|---|---|---|
| MCD14ML (MODIS Collection 6.1) | Standard monthly active fire locations, Terra + Aqua | FIRMS Archive Download — https://firms.modaps.eosdis.nasa.gov/download/ | 14 Nov 2026 |
| MCD14DL | MODIS near-real-time active fire, Terra + Aqua (in the same archive download, months after the standard data) | FIRMS Archive Download | 14 Nov 2026 |
| VNP14IMGML | VIIRS 375 m standard active fire, Suomi NPP | FIRMS Archive Download | 14 Nov 2026 |
| VNP14IMGTDL_NRT | VIIRS 375 m near-real-time active fire, Suomi NPP | FIRMS Archive Download | 14 Nov 2026 |
| VJ114IMGML | VIIRS 375 m standard active fire, NOAA-20 | FIRMS Archive Download | 14 Nov 2026 |
| VJ114IMGTDL_NRT | VIIRS 375 m near-real-time active fire, NOAA-20 | FIRMS Archive Download | 14 Nov 2026 |

One archive download per sensor family and region (twelve in all). The three for the contiguous United States are FIRMS downloads by country (United States; request ids 850141 MODIS, 850143 VIIRS Suomi NPP, 850142 VIIRS NOAA-20), made on 14 Nov 2026 and kept in `data/raw/usa/`; file names, row counts and SHA-256 hashes are in [data/manifest.json](data/manifest.json). Access dates are the dates of those downloads.

### FIRMS acknowledgment

From the FIRMS FAQ (https://www.earthdata.nasa.gov/data/tools/firms/faq, "Are there any restrictions on using data or imagery from FIRMS?"), accessed 14 Nov 2026:

> We acknowledge the use of imagery from the NASA LANCE FIRMS ( https://earthdata.nasa.gov/firms ), part of the NASA Earth Science Data and Information System (ESDIS).

## NASA documentation

- FIRMS overview — https://www.earthdata.nasa.gov/data/tools/firms
- FIRMS FAQ — https://www.earthdata.nasa.gov/data/tools/firms/faq
- Active fire data attributes for MODIS and VIIRS — https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs
- Suomi NPP end of new observations (2 Nov 2026) — https://www.earthdata.nasa.gov/data/alerts-outages/reminder-new-suomi-npp-observations-cease-november-2-2026
- Transitioning from Suomi NPP VIIRS & OMPS: what FIRMS users need to know — https://www.earthdata.nasa.gov/news/blog/transitioning-from-suomi-npp-viirs-omps-what-firms-users-need-know
- Transitioning from Suomi NPP to NOAA-20 and NOAA-21 (LANCE) — https://www.earthdata.nasa.gov/news/blog/transitioning-from-suomi-npp-noaa-20-noaa-21-what-lance-users-need-know
- Dates from which each satellite's fire data are available, and the end of Suomi NPP data (FIRMS FAQ, "For what dates are the fire data available?" and "Are there any missing MODIS fire data?", read 14 Nov 2026): MODIS Terra from 1 November 2000; MODIS Aqua from July 2002 ("starting July 4, 2002"); VIIRS S-NPP "from 20 January 2012 to November 2, 2026"; VIIRS NOAA-20 from 1 April 2018. The same FAQ gives the "2-3 month lag" of standard data. These are the dates in `SAT_FACTS` in `docs/index.html`.
- Launch dates (read 14 Nov 2026): Terra, 18 Dec 1999 — https://science.nasa.gov/mission/terra/ ; Aqua, 4 May 2002 — https://science.nasa.gov/mission/aqua/ ; Suomi NPP, 28 Oct 2011 — https://science.nasa.gov/mission/suomi-npp/ ; JPSS-1, renamed NOAA-20, NASA release of 18 Nov 2017 — https://www.nasa.gov/news-release/nasa-launches-noaa-weather-satellite-aboard-united-launch-alliance-rocket-to-improve-forecasts/
- Aqua's orbit (read 14 Nov 2026): "Due to fuel limitations, Aqua completed the last of its drag makeup maneuvers in December 2021 and is now in a free-drift mode, slowly descending below the A-Train and drifting to later equatorial crossing times, and lower altitudes." — NASA Science, Aqua — https://science.nasa.gov/mission/aqua/ . "Aqua and Aura's equatorial crossing times drifted by +50 and +15 minutes, respectively", as of January 2025, and both orbits had fallen from 704 km to about 690 km — NASA Science, A-Train: The Afternoon Constellation (page updated 21 Aug 2026) — https://science.nasa.gov/mission/a-train/ . Used for: the 2022 split in the validation and the sentence on the page that explains it. Neither page says what the drift does to fire counts; this project does not claim it.
- MODIS to VIIRS transition — https://ladsweb.modaps.eosdis.nasa.gov/learn/modis-to-viirs-transition/MODIS-VIIRS_Transition.pdf

## Challenge and rules

- Challenge statement — https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/
- 2026 Participant Terms and Conditions — https://www.spaceappschallenge.org/legal/

## Scientific references

- Giglio, L., Schroeder, W., & Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. *Remote Sensing of Environment*, 178, 31–41. https://doi.org/10.1016/j.rse.2016.02.054
- Schroeder, W., Oliva, P., Giglio, L., & Csiszar, I. A. (2014). The New VIIRS 375 m active fire detection data product: algorithm description and initial assessment. *Remote Sensing of Environment*, 143, 85–96. https://doi.org/10.1016/j.rse.2013.12.008

- Machado, G. M., Oliveira, M. M., & Fernandes, L. A. F. (2009). A physiologically-based model for simulation of color vision deficiency. *IEEE Transactions on Visualization and Computer Graphics*, 15(6), 1291–1298. https://doi.org/10.1109/TVCG.2009.113 — the matrices used to check the fire colour ramp under simulated colour-vision deficiency.

No other paper was used.

## Training that informed the approach

- NASA ARSET, Fundamentals of Remote Sensing
- NASA ARSET, Monitoring Surface Water with SAR (OPERA DSWx)
- NASA ARSET, NISAR Surface Displacement, part 1
- NASA ARSET, Geostationary Remote Sensing of Aerosols

How each one shaped the project is described in the README, "What NASA ARSET training changed in this project". ARSET and NASA did not review or endorse this work.

## Other projects consulted

Ideas only. No code copied.

- NASA Worldview — https://worldview.earthdata.nasa.gov/ — and the FIRMS Fire Map — https://firms.modaps.eosdis.nasa.gov/map/ — looked at for the layout of a map with a timeline beneath it and a layers panel. No code, logo or icon was taken from either.

No other repository or project was read for reference.

## Basemap and software

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Pages read when choosing them (14 Nov 2026):

- NASA GIBS API documentation, including the acknowledgment text — https://nasa-gibs.github.io/gibs-api-docs/ and https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api
- NASA GIBS WMTS capabilities (EPSG:3857), for layer names, titles and tile matrix sets — https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml
- Esri ArcGIS static basemap tiles service (checked; imagery not offered there) — https://developers.arcgis.com/rest/static-basemap-tiles/
- Esri ArcGIS basemap styles service, used for World Imagery (style `arcgis/imagery`) — https://developers.arcgis.com/rest/basemap-styles/
- Esri attribution guidance — https://developers.arcgis.com/documentation/esri-and-data-attribution/
- Esri terms: Master Agreement — https://www.esri.com/en-us/legal/terms/full-master-agreement; Product-Specific Terms — https://www.esri.com/en-us/legal/terms/product-specific-scope-of-use
- esri-leaflet and esri-leaflet-vector source and licences — https://github.com/Esri/esri-leaflet and https://github.com/Esri/esri-leaflet-vector
- GeoNames gazetteer and its readme with the licence (CC BY 4.0) — https://download.geonames.org/export/dump/ and https://download.geonames.org/export/dump/readme.txt (downloaded 14 Nov 2026 HST; `cities500.zip`, `admin1CodesASCII.txt`, `admin2Codes.txt`, `countryInfo.txt`)
- Nominatim usage policy, read before adding place names — https://operations.osmfoundation.org/policies/nominatim/ ; reverse geocoding endpoint `https://nominatim.openstreetmap.org/reverse` (checked with real requests, 14 Nov 2026)
- NASA GIBS daily Corrected Reflectance layers: names, date ranges and tile matrix set from the capabilities document above; one tile per satellite fetched to confirm (14 Nov 2026)
- NASA Worldview Snapshots — https://wvs.earthdata.nasa.gov/ (`/api/v1/snapshot`, checked with real requests including a day with no imagery)
- NASA Worldview configuration, for the fire layer names used in the links — https://worldview.earthdata.nasa.gov/config/wv.json
- OpenStreetMap copyright and licence — https://www.openstreetmap.org/copyright
- OSMF Tile Usage Policy — https://operations.osmfoundation.org/policies/tiles/
- CARTO basemap terms (not used: free use requires a CARTO API key) — https://carto.com/legal/basemap-terms/ and https://github.com/CartoDB/basemap-styles
- Leaflet 1.9.4 licence — https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE; files and SRI hashes from https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/
