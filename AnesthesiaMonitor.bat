@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHONW=%SCRIPT_DIR%.venv\Scripts\pythonw.exe"

start "" "%PYTHONW%" "%SCRIPT_DIR%main.py"