@echo off
rem ============================================================
rem  Token Estimator - drag & drop entry
rem  Drag file(s) onto this .cmd to see how many tokens they cost.
rem  Double-click it with no file to just see this hint.
rem  (ASCII-only on purpose, see start_gui.cmd for the reason.)
rem ============================================================
chcp 65001 >nul 2>nul
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title Token Estimator

set "SCRIPT=%~dp0estimate.py"
set "VENV=%~dp0.venv\Scripts\python.exe"

if "%~1"=="" (
    echo.
    echo   Drag file^(s^) onto this icon to estimate their token cost.
    echo.
    echo   Supported: .zip  .7z  .docx  .pdf  .xlsx  .txt  .md  .csv
    echo              and source code / Keil projects.
    echo   You can drag several files at once, or a whole folder.
    echo.
    echo   For a windowed version, run start_gui.cmd instead.
    echo.
    pause
    exit /b 0
)

echo.
if exist "%VENV%" (
    "%VENV%" "%SCRIPT%" %*
) else (
    python "%SCRIPT%" %*
)

echo.
pause
