@echo off
setlocal
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
set "ENTRY=cmdlab.cmd"
if exist "%APP_DIR%\cmdlab.exe" set "ENTRY=cmdlab.exe"

start "Command Lab" /D "%APP_DIR%" cmd.exe /k "%ENTRY%"
