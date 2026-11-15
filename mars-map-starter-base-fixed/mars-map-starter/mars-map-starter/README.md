# Mount Sharp Explorer — starter map

This is a small, single-page web app showing the global Viking MDIM 2.1 colorized Mars mosaic centered on the landing-ellipse reference coordinate cited in Calef et al. (2015):

- Longitude: `137.4019° E`
- Latitude: `4.5965° S` (`-4.5965`)

## Run it

1. Extract the project folder.
2. Open PowerShell in the `mars-map-starter` folder.
3. Run `py -m http.server 8000`.
4. Visit `http://localhost:8000`.

Keep the PowerShell window open while using the app. The base map and ArcGIS JavaScript SDK are loaded from the internet.

## Base map

The base surface uses the USGS/NASA Viking MDIM 2.1 colorized global mosaic through this ArcGIS cached MapServer:

`https://tiles.arcgis.com/tiles/lqRTrQp2HrfnJt8U/arcgis/rest/services/mars_viking_mosaic/MapServer`

The service advertises the MarsEC0 equidistant-cylindrical projection and its own cached tile matrix. The application now uses the service's native projection and native `TileLayer` rather than constructing a custom tile matrix. The landing marker is converted from the paper's longitude/latitude to MarsEC0 coordinates.

Source metadata: https://tiles.arcgis.com/tiles/lqRTrQp2HrfnJt8U/arcgis/rest/services/mars_viking_mosaic/MapServer?f=pjson

## Current scope

- Viking global color mosaic base map
- Landing-ellipse reference marker
- Pan, zoom and recenter controls
- Copy reference coordinates

MOLA and slope overlays are temporarily paused while the base imagery is verified. The previous slope-processing scripts and data folders remain in the project, but the slope image is not currently displayed in this build.

## Data credit

USGS Astrogeology Science Center, NASA Ames, NASA/JPL and Esri; Viking MDIM 2.1 Colorized Global Mosaic. The original global color mosaic has a native resolution of approximately 231 m/pixel at the equator.
