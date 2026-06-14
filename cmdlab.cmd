@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0cmdlab.exe" (
    "%~dp0cmdlab.exe" %*
) else (
    python -B "%~dp0terminal_ui.py" %*
)
