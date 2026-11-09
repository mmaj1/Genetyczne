@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Pierwsze uruchomienie: tworzy srodowisko wirtualne .venv i instaluje biblioteki.
if not exist ".venv\Scripts\python.exe" (
    echo Tworze srodowisko wirtualne .venv...
    python -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)
".venv\Scripts\python.exe" aplikacja.py %*
if errorlevel 1 goto :error
exit /b 0

:error
pause
exit /b 1
