@echo off
rem ============================================================
rem  Token Estimator - one-click environment setup
rem
rem  Creates a local .venv next to this script and installs all
rem  dependencies into it. Run this ONCE, then just double-click
rem  Token_Estimator.pyw (or start_gui.cmd).
rem
rem  ASCII-only on purpose: cmd.exe parses this file using the
rem  console codepage, so non-ASCII would be garbled on Chinese
rem  Windows.
rem ============================================================
chcp 65001 >nul 2>nul
setlocal
cd /d "%~dp0"

set "VENV=%~dp0.venv"
set "REQ=%~dp0requirements.txt"

echo.
echo ============================================================
echo   Token Estimator - environment setup
echo ============================================================
echo.

rem ---- 1. locate a Python interpreter ----------------------
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo [ERROR] Python not found on PATH.
    echo.
    echo   Install Python 3.9+ from https://www.python.org/downloads/
    echo   IMPORTANT: tick "Add python.exe to PATH" during install.
    echo.
    pause
    exit /b 1
)
echo [1/4] Using interpreter: %PY%
%PY% -c "import sys; print('      version', sys.version.split()[0])"

rem ---- 2. tkinter check ------------------------------------
%PY% -c "import tkinter" >nul 2>nul
if errorlevel 1 (
    echo.
    echo [WARN] This Python has no tkinter - the GUI will not start.
    echo        Command-line mode still works.
    echo        On Windows, re-run the python.org installer and tick
    echo        "tcl/tk and IDLE" to add it.
    echo.
)

rem ---- 3. create the virtual environment -------------------
if exist "%VENV%\Scripts\python.exe" (
    echo [2/4] Reusing existing environment: %VENV%
) else (
    echo [2/4] Creating environment: %VENV%
    %PY% -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

set "VPY=%VENV%\Scripts\python.exe"

rem ---- 4. install dependencies -----------------------------
echo [3/4] Upgrading pip ...
"%VPY%" -m pip install --upgrade pip --quiet --disable-pip-version-check

echo [4/4] Installing dependencies from requirements.txt ...
"%VPY%" -m pip install -r "%REQ%" --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo [INFO] Install failed - retrying via the Tsinghua mirror ...
    echo        (common in mainland China when PyPI is slow)
    "%VPY%" -m pip install -r "%REQ%" --disable-pip-version-check -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency install failed. Check your network.
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo   Done. Now double-click one of these:
echo     the .pyw file in this folder  (windowed GUI)
echo     start_gui.cmd                 (same, as a .cmd)
echo     drag_files_here.cmd           (drag files onto the icon)
echo ============================================================
echo.
pause
