@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PY=
for %%c in (py python) do (
  if not defined PY (
    %%c -c "import sys" >nul 2>nul && (
      for /f "delims=" %%p in ('%%c -c "import sys; print(sys.executable)"') do set "PY=%%p"
    )
  )
)
if not defined PY for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%d\python.exe" set "PY=%%d\python.exe"
if not defined PY (
  echo Python saknas. Kor start.bat forst.
  pause
  exit /b 1
)
if "%ODDS_API_KEY%"=="" set /p ODDS_API_KEY=Klistra in nyckeln for The Odds API och tryck Enter: 
"%PY%" -m propsbot bolag
pause
