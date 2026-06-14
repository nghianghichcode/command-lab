@echo off
setlocal
set "APP_DIR=%~dp0"
where wt.exe >nul 2>nul
if %errorlevel% equ 0 (
    start "" wt.exe new-tab --title "Command Lab" -d "%APP_DIR%" cmd /k cmdlab.cmd
) else (
    start "Command Lab" cmd /k "%APP_DIR%cmdlab.cmd"
)
