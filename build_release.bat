@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Stop running StudentAnalysis.exe if needed...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Stop-Process -Name StudentAnalysis -Force -ErrorAction SilentlyContinue"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2"

echo [2/3] Build app with StudentAnalysis.spec...
pyinstaller -y StudentAnalysis.spec
if errorlevel 1 (
  echo.
  echo Build failed. Please send the error output above to the developer.
  pause
  exit /b 1
)

echo [3/3] Create clean release zip...
python tools\create_release_package.py
if errorlevel 1 (
  echo.
  echo Release package failed. Please send the error output above to the developer.
  pause
  exit /b 1
)

echo.
echo Done. See the zip file in the release folder.
