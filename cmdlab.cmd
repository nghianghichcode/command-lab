@echo off
setlocal
cd /d "%~dp0"
python -B "%~dp0terminal_ui.py" %*
