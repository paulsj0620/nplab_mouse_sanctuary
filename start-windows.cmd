@echo off
setlocal
cd /d "%~dp0"
if not exist "data\lab.sqlite" (
  echo Missing data\lab.sqlite. Extract the complete transfer ZIP first.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import openpyxl,xlrd,numpy,scipy; assert tuple(map(int,scipy.__version__.split('.')[:2])) >= (1,16)" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements\requirements.txt
  if errorlevel 1 goto failed
)
echo Open http://127.0.0.1:8000/ in your browser after the server starts.
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m scripts.app.server --host 127.0.0.1 --port 8000 --db data\lab.sqlite
if errorlevel 1 goto failed
exit /b 0
:failed
echo Startup failed. Install Python 3.12 with the Python launcher, then retry.
echo If port 8000 is occupied, stop the other server before retrying.
pause
exit /b 1
