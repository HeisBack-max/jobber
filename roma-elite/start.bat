@echo off
REM Roma Elite - launcher (Windows). Requires Node.js 20+; no dependencies.
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed.
  echo Install it from https://nodejs.org ^(version 20 or newer^), then run this again.
  echo.
  echo You can also just open dist\RomaElite.html in a browser - no install needed.
  pause
  exit /b 1
)

echo Starting Roma Elite on http://localhost:3000  (press Ctrl+C to stop)
node server\index.js
pause
