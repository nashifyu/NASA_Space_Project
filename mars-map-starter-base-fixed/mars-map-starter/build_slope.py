#!/usr/bin/env python3
"""Build a browser-ready Mars slope overlay from the USGS Gale DEM mosaic.

The USGS source is a Mars equirectangular DEM in metres. This script clips a
regional bounding box, averages it to a practical analysis grid, calculates
slope with Horn's 3x3 method, and writes a transparent PNG plus its map extent.

Source metadata: USGS Astrogeology, Mars MSL Gale Merged DEM 1m, v3.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds

MARS_RADIUS_M = 3_396_190.0
DEG_TO_RAD = math.pi / 180.0

# A useful first region around the landing-ellipse reference and lower Mount
# Sharp. The full official mosaic extent is roughly 137.124–137.681 E and
# 5.099–4.130 S; this crop stays within that coverage.
DEFAULT_BBOX = (137.22, -5.02, 137.62, -4.22)  # west, south, east, north

# Display classes are visualization categories, not validated astronaut
# mobility/safety thresholds.
PALETTE = [
    (5.0,  (48, 150, 91, 205)),    # 0–5°: green
    (10.0, (158, 183, 65, 205)),  # 5–10°: yellow-green
    (20.0, (239, 183, 61, 210)),  # 10–20°: amber
    (30.0, (225, 105, 53, 215)),  # 20–30°: orange-red
    (90.0, (174, 48, 55, 220)),   # >30°: dark red
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a slope PNG overlay from the USGS Gale DEM GeoTIFF."
    )
    parser.add_argument(
        "--dem",
        type=Path,
        default=Path("data/MSL_Gale_DEM_Mosaic_1m_v3.tif"),
        help="Path to the downloaded USGS DEM GeoTIFF (default: %(default)s)",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=25.0,
        help="Output grid spacing in metres (default: %(default)s).",
    )
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        default=DEFAULT_BBOX,
        help="Crop bounds in Mars longitude/latitude degrees east/north.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("slope-overlay"),
        help="Output folder (default: %(default)s).",
    )
    return parser.parse_args()


def mars_lonlat_to_equirectangular(lon: float, lat: float) -> tuple[float, float]:
    """Convert Mars lon/lat to equirectangular x/y metres (clon=0, clat=0)."""
    return (
        MARS_RADIUS_M * math.radians(lon),
        MARS_RADIUS_M * math.radians(lat),
    )


def safe_mask(masked: np.ma.MaskedArray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(masked.filled(np.nan), dtype=np.float32)
    valid = np.isfinite(values)
    return values, valid


def horn_slope(
    elevation: np.ndarray,
    valid: np.ndarray,
    pixel_x_m: float,
    pixel_y_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return slope degrees and a mask requiring a valid 3x3 neighborhood."""
    h, w = elevation.shape
    padded = np.pad(elevation, 1, mode="edge")
    vp = np.pad(valid, 1, mode="constant", constant_values=False)

    z1 = padded[0:h, 0:w]
    z2 = padded[0:h, 1:w + 1]
    z3 = padded[0:h, 2:w + 2]
    z4 = padded[1:h + 1, 0:w]
    z6 = padded[1:h + 1, 2:w + 2]
    z7 = padded[2:h + 2, 0:w]
    z8 = padded[2:h + 2, 1:w + 1]
    z9 = padded[2:h + 2, 2:w + 2]

    dz_dx = ((z3 + 2 * z6 + z9) - (z1 + 2 * z4 + z7)) / (8.0 * pixel_x_m)
    dz_dy = ((z7 + 2 * z8 + z9) - (z1 + 2 * z2 + z3)) / (8.0 * pixel_y_m)
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy))).astype(np.float32)

    neighborhood_valid = np.ones((h, w), dtype=bool)
    for row_offset in range(3):
        for col_offset in range(3):
            neighborhood_valid &= vp[row_offset:row_offset + h, col_offset:col_offset + w]
    return slope, neighborhood_valid


def colorize_slope(slope: np.ndarray, valid: np.ndarray) -> np.ndarray:
    rgba = np.zeros((*slope.shape, 4), dtype=np.uint8)
    lower = 0.0
    for upper, color in PALETTE:
        chosen = valid & (slope >= lower) & (slope < upper if upper < 90 else slope <= upper)
        rgba[chosen] = color
        lower = upper
    # Values outside the expected physical range are transparent rather than
    # silently assigned to a class.
    valid &= (slope >= 0.0) & (slope <= 90.0)
    rgba[~valid] = (0, 0, 0, 0)
    return rgba


def main() -> int:
    args = parse_args()
    if args.resolution <= 0:
        print("ERROR: --resolution must be greater than zero.", file=sys.stderr)
        return 2
    if not args.dem.exists():
        print(f"ERROR: DEM not found: {args.dem}")
        print("Download the official USGS GeoTIFF first; see README.md for the source link.")
        return 2

    west, south, east, north = args.bbox
    if not (west < east and south < north):
        print("ERROR: --bbox must be WEST SOUTH EAST NORTH with increasing bounds.", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Opening DEM: {args.dem}")
    with rasterio.open(args.dem) as src:
        if src.count < 1 or src.transform is None:
            raise RuntimeError("The source file does not contain a readable raster band/geotransform.")

        # USGS Astropedia describes this mosaic as equirectangular, positive-east,
        # planetocentric latitude, Mars radius 3,396,190 m. Some GIS exports may
        # carry geographic-degree coordinates instead; detect those explicitly.
        coords_are_degrees = (
            abs(src.bounds.left) <= 360
            and abs(src.bounds.right) <= 360
            and abs(src.bounds.bottom) <= 90
            and abs(src.bounds.top) <= 90
        )
        if coords_are_degrees:
            crop_bounds = (west, south, east, north)
        else:
            x_west, y_south = mars_lonlat_to_equirectangular(west, south)
            x_east, y_north = mars_lonlat_to_equirectangular(east, north)
            crop_bounds = (x_west, y_south, x_east, y_north)

        requested = from_bounds(*crop_bounds, transform=src.transform)
        requested = requested.round_offsets().round_lengths()
        try:
            window = requested.intersection(Window(0, 0, src.width, src.height))
        except Exception as exc:
            raise RuntimeError("The requested crop does not overlap the DEM coverage.") from exc
        if window.width < 3 or window.height < 3:
            raise RuntimeError("The requested crop is outside the DEM or too small.")

        # Read directly to the coarser output grid. Average resampling reduces
        # high-frequency noise and keeps the output small enough for a browser.
        src_x_m = abs(src.transform.a)
        src_y_m = abs(src.transform.e)
        if coords_are_degrees:
            approx_lat = (south + north) / 2.0
            metres_per_degree = MARS_RADIUS_M * DEG_TO_RAD
            src_x_m *= metres_per_degree * math.cos(math.radians(approx_lat))
            src_y_m *= metres_per_degree

        out_w = max(3, int(math.ceil(window.width * src_x_m / args.resolution)))
        out_h = max(3, int(math.ceil(window.height * src_y_m / args.resolution)))
        # Keep the image within a conservative GPU-friendly size for ArcGIS MediaLayer.
        scale_down = max(out_w / 2000.0, out_h / 2000.0, 1.0)
        if scale_down > 1.0:
            out_w = max(3, int(out_w / scale_down))
            out_h = max(3, int(out_h / scale_down))

        print(
            f"Reading crop {window.width:.0f} x {window.height:.0f} source pixels; "
            f"resampling to {out_w} x {out_h} ({args.resolution:g} m target grid)."
        )
        dem = src.read(
            1,
            window=window,
            out_shape=(out_h, out_w),
            resampling=Resampling.average,
            masked=True,
        )
        out_transform = src.window_transform(window) * rasterio.Affine.scale(
            window.width / out_w, window.height / out_h
        )

    elevation, valid = safe_mask(dem)
    if valid.sum() < 100:
        raise RuntimeError("Too few valid elevation cells in the selected region.")

    mid_y = (out_transform.f + (out_transform.e * out_h / 2.0))
    if coords_are_degrees:
        mid_lat = mid_y
        metres_per_degree = MARS_RADIUS_M * DEG_TO_RAD
        pixel_x_m = abs(out_transform.a) * metres_per_degree * math.cos(math.radians(mid_lat))
        pixel_y_m = abs(out_transform.e) * metres_per_degree
    else:
        mid_lat = math.degrees(mid_y / MARS_RADIUS_M)
        pixel_x_m = abs(out_transform.a) * math.cos(math.radians(mid_lat))
        pixel_y_m = abs(out_transform.e)

    slope, slope_valid = horn_slope(elevation, valid, pixel_x_m, pixel_y_m)
    rgba = colorize_slope(slope, slope_valid)

    # Raster coordinate edges -> Mars longitude/latitude in the map's WKID 104905.
    x_left = out_transform.c
    x_right = out_transform.c + out_transform.a * out_w
    y_top = out_transform.f
    y_bottom = out_transform.f + out_transform.e * out_h
    if coords_are_degrees:
        xmin, xmax = sorted((x_left, x_right))
        ymin, ymax = sorted((y_bottom, y_top))
    else:
        xmin, xmax = sorted((x_left, x_right))
        ymin, ymax = sorted((y_bottom, y_top))
        xmin = math.degrees(xmin / MARS_RADIUS_M)
        xmax = math.degrees(xmax / MARS_RADIUS_M)
        ymin = math.degrees(ymin / MARS_RADIUS_M)
        ymax = math.degrees(ymax / MARS_RADIUS_M)

    image_path = args.output_dir / "slope.png"
    metadata_path = args.output_dir / "metadata.json"
    Image.fromarray(rgba, mode="RGBA").save(image_path, optimize=True)

    metadata = {
        "extent": {
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
            "wkid": 104905,
        },
        "width": int(out_w),
        "height": int(out_h),
        "analysisGridMeters": float(args.resolution),
        "slopeMethod": "Horn 3x3 finite-difference method",
        "slopeUnits": "degrees",
        "source": "USGS Astrogeology, Mars MSL Gale Merged DEM 1m, v3",
        "sourceUrl": "https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m",
        "sourceNominalPostingMeters": 1,
        "notes": [
            "The source mosaic has variable effective terrain resolution where HiRISE coverage is absent; it falls back to CTX, HRSC and MOLA data.",
            "Slope classes are for visualization only, not validated astronaut or rover safety thresholds.",
            "The layer covers only the requested crop; transparent pixels indicate missing DEM coverage or edge cells without a complete 3x3 neighborhood.",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Created: {image_path}")
    print(f"Created: {metadata_path}")
    print(f"Map extent: {xmin:.6f}, {ymin:.6f}, {xmax:.6f}, {ymax:.6f} (Mars lon/lat)")
    print("Done. Refresh http://localhost:8000 to use the Slope analysis layer.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
