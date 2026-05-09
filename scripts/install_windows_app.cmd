@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_windows_app.ps1" -DesktopShortcut
set "INSTALL_EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%INSTALL_EXIT_CODE%"=="0" (
    echo MPLGallery install failed.
    echo You can close this window after reading the error above.
    pause
    exit /b %INSTALL_EXIT_CODE%
)

echo MPLGallery was installed. Search for MPLGallery in the Windows Start menu.
pause
