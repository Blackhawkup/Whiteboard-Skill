@echo off
rem Double-click to start an additional Flow Studio panel on a new port for side-by-side video generation. Close this window to stop it.
cd /d "%~dp0"
if not exist dist call npm run build
node dist\studio.js --new
pause
