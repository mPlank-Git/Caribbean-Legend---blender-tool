@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "NVTT=%~dp0nvtt_export.exe"
set "OUTPUT=%~dp0output_combine"

if not exist "%NVTT%" (
    echo ERROR: nvtt_export.exe not found:
    echo "%NVTT%"
    echo.
    echo Put this BAT file near nvtt_export.exe.
    pause
    exit /b
)

if "%~1"=="" (
    echo Drag and drop texture files onto this BAT.
    echo.
    echo Rules:
    echo *_nom.*  = BC3 / DXT5
    echo *_rma.*  = BC3 / DXT5
    echo others   = BC1 / DXT1
    echo.
    pause
    exit /b
)

if not exist "%OUTPUT%" mkdir "%OUTPUT%"

echo Converting dropped textures...
echo Output folder:
echo "%OUTPUT%"
echo.

:loop
if "%~1"=="" goto done

set "FILE=%~1"
set "NAME=%~n1"
set "EXT=%~x1"
set "SUFFIX=!NAME:~-4!"

if /I "!SUFFIX!"=="_nom" (
    echo [BC3 / DXT5] %~nx1
    "%NVTT%" "%FILE%" --format bc3 --output "%OUTPUT%\%~n1.dds"
) else if /I "!SUFFIX!"=="_rma" (
    echo [BC3 / DXT5] %~nx1
    "%NVTT%" "%FILE%" --format bc3 --output "%OUTPUT%\%~n1.dds"
) else (
    echo [BC1 / DXT1] %~nx1
    "%NVTT%" "%FILE%" --format bc1 --output "%OUTPUT%\%~n1.dds"
)

shift
goto loop

:done
echo.
echo Done.
echo Output folder:
echo "%OUTPUT%"
pause