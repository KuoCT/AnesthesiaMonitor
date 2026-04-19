@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "AM_SHORTCUT_TARGET=%SCRIPT_DIR%AnesthesiaMonitor.bat"
set "AM_SHORTCUT_ICON_ICO=%SCRIPT_DIR%asset\logo.ico"

if not exist "%AM_SHORTCUT_TARGET%" (
    echo AnesthesiaMonitor.bat was not found in this folder.
    pause
    exit /b 1
)

if not exist "%AM_SHORTCUT_ICON_ICO%" (
    echo asset\logo.ico was not found.
    echo Please run convert_svg_to_ico.py first, then run this file again.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$target = $env:AM_SHORTCUT_TARGET; " ^
    "$iconIco = $env:AM_SHORTCUT_ICON_ICO; " ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$linkPath = Join-Path $desktop 'Anesthesia Monitor.lnk'; " ^
    "$shell = New-Object -ComObject WScript.Shell; " ^
    "$shortcut = $shell.CreateShortcut($linkPath); " ^
    "$shortcut.TargetPath = $target; " ^
    "$shortcut.WorkingDirectory = Split-Path -Parent $target; " ^
    "$shortcut.Description = 'Anesthesia Monitor'; " ^
    "$shortcut.IconLocation = $iconIco; " ^
    "$shortcut.Save(); " ^
    "Write-Host ('Shortcut created: ' + $linkPath)"

if errorlevel 1 (
    pause
    exit /b 1
)

pause
