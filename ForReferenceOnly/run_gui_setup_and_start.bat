@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0

echo ========= QuantDesk GUI launcher =========

REM 1) Create venv if missing
if not exist .venv (
  echo [*] Creating venv...
  py -3 -m venv .venv || (echo [!] Failed to create venv & pause & exit /b 1)
)

REM 2) Activate venv
call .venv\Scripts\activate || (echo [!] Failed to activate venv & pause & exit /b 1)

REM 3) Upgrade pip tooling
echo [*] Upgrading pip/setuptools/wheel...
python -m pip install --upgrade pip setuptools wheel || (echo [!] pip upgrade failed & pause & exit /b 1)

REM 4) Install deps
echo [*] Installing dependencies...
python -m pip install PySide6 backtrader pandas numpy yfinance || (echo [!] deps install failed & pause & exit /b 1)

REM 5) Sanity checks
if not exist main.py (
  echo [!] main.py not found in: %cd%
  dir /b
  pause
  exit /b 1
)
if not exist qml\Main.qml (
  echo [!] qml\Main.qml not found (UI file missing)
  dir /b qml
  pause
  exit /b 1
)

set PYTHONUTF8=1
set QT_QUICK_CONTROLS_STYLE=Material
set QT_DEBUG_PLUGINS=0

echo [*] PySide6 version:
python - <<PYCODE
import sys
try:
    import PySide6
    from PySide6 import QtCore, QtWidgets, QtQml
    print("PySide6", PySide6.__version__)
    print("Qt", QtCore.qVersion())
except Exception as e:
    print("[ImportError]", e)
    sys.exit(1)
PYCODE
if ERRORLEVEL 1 ( echo [!] PySide6 import failed & pause & exit /b 1 )

echo [*] Launching UI (logs -> gui_run.log)...
echo ==== %DATE% %TIME% ==== >> gui_run.log
python main.py >> gui_run.log 2>&1
set rc=%ERRORLEVEL%
echo [*] main.py exited with code %rc%
echo.
echo --- Last 40 lines of gui_run.log ---
for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "Get-Content -Path 'gui_run.log' -Tail 40"`) do echo %%A
echo ------------------------------------
pause
