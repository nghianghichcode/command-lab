@echo off
setlocal
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
set "ENTRY=pctool.cmd"
if exist "%APP_DIR%\pctool.exe" set "ENTRY=pctool.exe"

start "Nghia PC Toolkit" /D "%APP_DIR%" cmd.exe /k "%ENTRY%"
