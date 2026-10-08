@echo off
rem ============================================================
rem  Token Estimator - GUI launcher
rem  Double-click this file to open the graphical tool.
rem
rem  (All text in this .cmd is ASCII on purpose: cmd.exe parses
rem   the file using the console codepage, so non-ASCII here
rem   would show up garbled on Chinese Windows.)
rem ============================================================
setlocal
set "SCRIPT=%~dp0gui.py"
set "PYW=%~dp0.venv\Scripts\pythonw.exe"

if exist "%PYW%" (
    start "" "%PYW%" "%SCRIPT%"
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%SCRIPT%"
    exit /b 0
)

echo.
echo [ERROR] No usable Python with a GUI runtime was found.
echo.
echo Expected either:
echo   %PYW%
echo   or "pythonw" on your PATH
echo.
echo Easiest fix: double-click  setup_env.cmd  once to create
echo the environment automatically.
echo.
pause
exit /b 1
