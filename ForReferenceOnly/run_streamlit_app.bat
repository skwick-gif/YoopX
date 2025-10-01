@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0

echo ========= Streamlit launcher =========

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
python -m pip install streamlit backtrader pandas numpy matplotlib yfinance || (echo [!] deps install failed & pause & exit /b 1)

REM 5) Check app.py present
if not exist app.py (
  echo [!] app.py not found in: %cd%
  echo     Put this BAT in the same folder as your Streamlit app.py
  dir /b
  pause
  exit /b 1
)

REM 6) Launch Streamlit (keeps console open)
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
echo [*] Starting Streamlit...
streamlit run app.py
set rc=%ERRORLEVEL%
echo [*] Streamlit exited with code %rc%
pause
