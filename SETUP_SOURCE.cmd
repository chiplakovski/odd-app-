@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python_missing
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto failed
echo.
echo Setup completed.
echo Run RUN_FROM_SOURCE.cmd to start the app.
pause
exit /b 0
:python_missing
echo Python was not found. Install Python 3.10+ first.
pause
exit /b 1
:failed
echo Setup failed.
pause
exit /b 1
