@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_SOURCE.cmd first.
  pause
  exit /b 1
)

echo Installing PyInstaller...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q pyinstaller
if errorlevel 1 goto failed

echo Building the application with PyInstaller...
".venv\Scripts\python.exe" -m PyInstaller packaging\build.spec --noconfirm
if errorlevel 1 goto failed

echo.
echo App build complete: dist\ODD Inspection Report Generator\

where iscc >nul 2>nul
if errorlevel 1 (
  echo.
  echo Inno Setup's "iscc" was not found on PATH, so the installer was not built.
  echo Install Inno Setup from https://jrsoftware.org/isinfo.php and re-run this script
  echo to also produce the Setup.exe with the Start Menu / Desktop shortcuts.
  pause
  exit /b 0
)

echo Building the installer with Inno Setup...
iscc packaging\installer.iss
if errorlevel 1 goto failed

echo.
echo Installer created: packaging\Output\ODD_Inspection_Report_Generator_Setup.exe
pause
exit /b 0

:failed
echo Build failed.
pause
exit /b 1
