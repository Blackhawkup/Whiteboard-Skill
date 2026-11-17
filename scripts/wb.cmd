@echo off
rem One command for the whiteboard-explainer skill on Windows: wb help
setlocal
if "%WHITEBOARD_HOME%"=="" set "WHITEBOARD_HOME=%USERPROFILE%\WhiteboardFilms"
set "PYTHONDONTWRITEBYTECODE=1"
set "PY=%WHITEBOARD_HOME%\.tools\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0..\tools\wb.py" %*
