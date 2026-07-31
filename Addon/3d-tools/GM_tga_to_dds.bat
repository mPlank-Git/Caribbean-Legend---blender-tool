@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Drag and drop one or more .gm files onto this BAT.
    pause
    exit /b
)

set "OUTDIR=%~dp0DDS_CONVERTED"

if not exist "%OUTDIR%" (
    mkdir "%OUTDIR%"
)

:loop
if "%~1"=="" goto done

set "SRC=%~1"
set "EXT=%~x1"
set "NAME=%~nx1"
set "DST=%OUTDIR%\%NAME%"

if /I not "%EXT%"==".gm" (
    echo Skipped: "%SRC%" is not a .gm file
    shift
    goto loop
)

echo.
echo ========================================
echo File: "%NAME%"
echo ========================================

copy /Y "%SRC%" "%DST%" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = '%DST%';" ^
  "$b = [System.IO.File]::ReadAllBytes($p);" ^
  "$enc = [System.Text.Encoding]::ASCII;" ^
  "$text = $enc.GetString($b);" ^
  "$matches = [regex]::Matches($text, '[A-Za-z0-9_./\\-]+\.tga', 'IgnoreCase');" ^
  "$seen = @{};" ^
  "foreach ($m in $matches) {" ^
  "  $old = $m.Value;" ^
  "  if ($seen.ContainsKey($old)) { continue }" ^
  "  $seen[$old] = $true;" ^
  "  $new = [regex]::Replace($old, '\.tga$', '.dds', 'IgnoreCase');" ^
  "  Write-Host ('  ' + $old + '  ->  ' + $new);" ^
  "}" ^
  "if ($seen.Count -eq 0) { Write-Host '  No .tga textures found.' }" ^
  "for ($i = 0; $i -le $b.Length - 4; $i++) {" ^
  "  if ($b[$i] -eq 46 -and $b[$i+1] -eq 116 -and $b[$i+2] -eq 103 -and $b[$i+3] -eq 97) { $b[$i+1]=100; $b[$i+2]=100; $b[$i+3]=115 }" ^
  "  elseif ($b[$i] -eq 46 -and $b[$i+1] -eq 84 -and $b[$i+2] -eq 71 -and $b[$i+3] -eq 65) { $b[$i+1]=68; $b[$i+2]=68; $b[$i+3]=83 }" ^
  "}" ^
  "[System.IO.File]::WriteAllBytes($p, $b);"

echo.
echo Saved to: "%DST%"

shift
goto loop

:done
echo.
echo Done.
pause