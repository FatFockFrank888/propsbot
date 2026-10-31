@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

call :findpy
if "%PY%"=="" (
  echo Python saknas. Installerar Python 3.12 via winget, det tar en minut...
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
  call :findpy
)
if "%PY%"=="" (
  echo.
  echo Kunde inte installera Python automatiskt.
  echo Installera fran https://www.python.org/downloads/ och kryssa i "Add Python to PATH".
  echo Kor sedan start.bat igen.
  pause
  exit /b 1
)
echo Anvander Python: %PY%

"%PY%" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Kunde inte installera paketen.
  pause
  exit /b 1
)

title propsbot - bevakar odds
echo.
echo Startar bevakningen. Fonstret ska vara oppet - stang det for att avsluta.
echo Resultat sparas i mappen "resultat", felsokning i "diagnos\diagnos.txt".
echo.
"%PY%" -m propsbot bevaka
pause
exit /b 0


rem ---- Hitta en Python som faktiskt fungerar (inte Microsoft Store-genvagen) ----
:findpy
set PY=
for %%c in (py python) do (
  if not defined PY (
    %%c -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>nul && (
      for /f "delims=" %%p in ('%%c -c "import sys; print(sys.executable)"') do set "PY=%%p"
    )
  )
)
if not defined PY (
  for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%d\python.exe" set "PY=%%d\python.exe"
  )
)
exit /b 0
