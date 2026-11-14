@echo off
cd /d "%~dp0"
if not exist data mkdir data

echo This downloads the official USGS Mars MSL Gale 1m DEM (about 3.6 GB).
echo Make sure you have enough disk space and a stable internet connection.
echo.
pause
curl.exe -L --fail --retry 5 --retry-all-errors --continue-at - "https://planetarymaps.usgs.gov/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif" -o "data\MSL_Gale_DEM_Mosaic_1m_v3.tif"
if errorlevel 1 goto failed

echo.
echo DEM download complete. Next, run process_slope.bat.
pause
exit /b 0
:failed
echo.
echo Download failed or was interrupted. Run this file again to retry/resume if the server supports range requests.
pause
exit /b 1
