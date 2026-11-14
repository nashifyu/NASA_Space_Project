@echo off
cd /d "%~dp0"
echo Installing Python packages needed to build the slope layer...
py -m pip install -r requirements.txt
if errorlevel 1 goto failed

echo.
echo Looking for data\MSL_Gale_DEM_Mosaic_1m_v3.tif ...
py build_slope.py --dem "data\MSL_Gale_DEM_Mosaic_1m_v3.tif"
if errorlevel 1 goto failed

echo.
echo Slope layer generated. Refresh http://localhost:8000 in your browser.
pause
exit /b 0
:failed
echo.
echo Slope generation did not finish. Read README.md for setup and troubleshooting.
pause
exit /b 1
