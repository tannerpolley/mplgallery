@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_windows_app.ps1" -DesktopShortcut
exit /b %ERRORLEVEL%
