# Mount Sharp Explorer — starter map

This is a small, single-page web app that opens an overhead Mars basemap and centers the view on the MSL landing-ellipse reference point cited in Calef et al. (2015):

- Longitude: `137.4019° E`
- Latitude: `4.5965° S` (`-4.5965`)

## Run it

1. Download and unzip the project.
2. Open a terminal in the `mars-map-starter` folder.
3. Start a local web server:

   **Python**
   ```bash
   python -m http.server 8000
   ```

4. Visit `http://localhost:8000` in your browser.

You can also open `index.html` directly, but a local server is more reliable for browser APIs such as clipboard access.

## Base surface layer

The always-on base layer is the USGS Astrogeology / NASA Ames Viking MDIM 2.1 colorized global Mars mosaic, served as an ArcGIS cached map layer. It provides the red-brown Mars surface appearance underneath the optional MOLA relief and slope overlays. Its documented native resolution is approximately 231 m/pixel at the equator. It is a colorized global mosaic assembled from Viking color imagery blended over the Viking-based MDIM 2.1 image model; it is not modern high-resolution local imagery. The web map uses the Mars 2000 / MarsEC0 spatial reference (WKID `104905`).

## Current limitations

- This is an initial regional basemap, not a detailed navigation map.
- The marker represents the center of the final MSL landing ellipse, not the summit of Mount Sharp.
- The page requires an internet connection to load the ArcGIS JavaScript SDK and map tiles.
- The slope control remains unavailable until the source DEM has been downloaded and processed locally.
- It does not yet include routing, geological overlays, elevation profiles, or rover photos.

## Useful sources

- Calef et al. (2015), *Assessing Gale Crater as a Landing Site for the First Human Mission to Mars*: https://www.hou.usra.edu/meetings/explorationzone2015/pdf/1020.pdf
- USGS-hosted Viking mosaic service: https://tiles.arcgis.com/tiles/lqRTrQp2HrfnJt8U/arcgis/rest/services/mars_viking_mosaic/MapServer
- USGS Astropedia Viking colorized global mosaic metadata: https://astrogeology.usgs.gov/search/map/mars_viking_colorized_global_mosaic_232m
- MOLA elevation / color hillshade tile service: https://tiles.arcgis.com/tiles/nzS0F0zdNLvs7nc8/arcgis/rest/services/Mars_MOLA_elevation/MapServer
- NASA Mars Trek layer documentation: https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars

## Slope analysis layer (new)

The app now has a slope-analysis control. It displays a locally generated transparent PNG over the Mars map. The PNG is **derived from real USGS Gale elevation data**, rather than using a decorative hillshade or pretending a roughness map is slope.

### Data source and size

Download the official **Mars MSL Gale Merged DEM 1m, version 3** GeoTIFF from USGS:

<https://planetarymaps.usgs.gov/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif>

The source file is about **3.6 GB**. Save it as:

`data/MSL_Gale_DEM_Mosaic_1m_v3.tif`

USGS describes the product as a one-metre-post Gale DEM assembled from HiRISE, CTX and HRSC data tied to MOLA. The effective source resolution varies where high-resolution stereo coverage is absent; the mosaic falls back to coarser terrain data.

### Generate the overlay on Windows

1. Run `download_dem.bat` from the project folder (or download the GeoTIFF from the link above and place it in `data` using the exact filename shown). The download is about 3.6 GB.
2. Keep the Python server running in one PowerShell window.
3. In a second PowerShell window, navigate to this project folder and run:

   ```powershell
   .\process_slope.bat
   ```

4. The first run installs `rasterio`, `numpy` and `Pillow`. The script clips a regional area around the MSL landing-ellipse point and lower Mount Sharp, resamples it to a 25 m analysis grid, and calculates slope in degrees using Horn's 3×3 method.
5. It writes `slope-overlay/slope.png` and `slope-overlay/metadata.json`. Refresh `http://localhost:8000`; the Slope analysis layer will become available.

The PNG is a small browser-ready image. Do not place the 3.6 GB source GeoTIFF in GitHub; add `data/*.tif` to `.gitignore` if you initialize a repository.

### What the colors mean

- Green: 0–5°
- Yellow-green: 5–10°
- Amber: 10–20°
- Orange-red: 20–30°
- Dark red: above 30°

These are display classes only. They are not validated astronaut/rover safety thresholds. The layer is derived from archived topography and should be used for an early prototype, not operational navigation.

### Technical note

The processing script assumes the USGS mosaic's documented equirectangular projection, positive-east longitude, planetocentric latitude and Mars radius of 3,396,190 m. It converts the output image bounds to the same Mars longitude/latitude map coordinates used by the current app (WKID 104905).

## Data credit

Parker, T. and Calef, F. J. (2016), *Mars MSL Gale Merged DEM 1m*, USGS Astrogeology Science Center, version 3. Please credit the product authors and source when presenting the app.


## Base imagery service

The Viking color base layer is streamed from NASA Trek using its equirectangular Mars 2000 (EPSG:104905) tile service. It is configured as a custom `WebTileLayer` with a Mars-specific tile scheme so the global raster aligns with the Martian longitude/latitude coordinates used by the landing-site marker.

Tile source: `https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg`
