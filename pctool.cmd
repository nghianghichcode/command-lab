@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0pctool.exe" (
    "%~dp0pctool.exe" %*
) else (
    python -B "%~dp0terminal_ui.py" %*
)
