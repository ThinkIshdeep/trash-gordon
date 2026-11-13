@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Install Python 3.12 from python.org and try again.
    pause
    exit /b 1
  )
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed. Check your connection and requirements.txt.
    pause
    exit /b 1
  )
)
echo Open http://127.0.0.1:8765/ in your browser.
echo Keep this window open. Press Ctrl+C to stop.
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
.venv\Scripts\python.exe run.py %*
pause
