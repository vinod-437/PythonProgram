
@echo off
cd /d "%~dp0"

REM 1. Try Virtual Environment
if exist "venv\Scripts\activate.bat" (
    echo Using Virtual Environment...
    call venv\Scripts\activate.bat
    python src\main.py
    pause
    exit /b
)

REM 2. Try System Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using System Python...
    python src\main.py
    pause
    exit /b
)

REM 3. Try Known Fallback (pgAdmin Python)
if exist "C:\Program Files\pgAdmin 4\python\python.exe" (
    echo Using pgAdmin Python Fallback...
    "C:\Program Files\pgAdmin 4\python\python.exe" src\main.py
    pause
    exit /b
)

echo Error: Python not found in PATH, venv, or known fallback locations.
echo Please install Python 3.x and add it to PATH.
pause
