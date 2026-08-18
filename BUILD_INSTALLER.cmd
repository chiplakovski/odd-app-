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

if not exist "packaging\vendor\clawPDF_setup.msi" (
  echo.
  echo Downloading clawPDF (oddprint virtual printer engine, needed for the installer
  echo to compile even if you don't check the oddprint option)...
  powershell -NoProfile -Command ^
    "$ErrorActionPreference='Stop'; New-Item -ItemType Directory -Force -Path packaging\vendor | Out-Null; Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/clawsoftware/clawPDF/0.9.3/src/_MSI/clawPDF_0.9.3_setup.msi' -OutFile 'packaging\vendor\clawPDF_setup.msi'; $hash = (Get-FileHash -Path 'packaging\vendor\clawPDF_setup.msi' -Algorithm SHA256).Hash; if ($hash -ne '4B8102955E7A75149C45EFC968643DB87B3AED85753136B186734EE1C614298C') { Write-Error \"checksum mismatch: $hash\"; exit 1 }"
  if errorlevel 1 (
    echo.
    echo Could not download clawPDF_setup.msi - check your internet connection and re-run.
    pause
    exit /b 1
  )
)

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
