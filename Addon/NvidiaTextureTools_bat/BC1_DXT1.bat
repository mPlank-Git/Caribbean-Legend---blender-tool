@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "NVTT=%~dp0nvtt_export.exe"
set "OUTPUT=%~dp0output_bc1"

if not exist "%NVTT%" (
    echo ERROR: nvtt_export.exe not found:
    echo "%NVTT%"
    pause
    exit /b
)

if "%~1"=="" (
    echo Drag and drop texture files onto this BAT.
    echo Supported: png, tga, tif, tiff, jpg, jpeg, bmp, psd
    pause
    exit /b
)

if not exist "%OUTPUT%" mkdir "%OUTPUT%"

echo Converting dropped files to BC1 / DXT1 DDS...
echo.

:loop
if "%~1"=="" goto done

echo Converting: %~nx1
"%NVTT%" "%~1" --format bc1 --output "%OUTPUT%\%~n1.dds"

shift
goto loop

:done
echo.
echo Done. Output folder:
echo "%OUTPUT%"
pause