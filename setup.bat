
@echo off
echo Setting up PaythonProgram Environment...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.x.
    pause
    exit /b 1
)

REM Create Virtual Environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

REM Activate and Install Requirements
echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo Setup Complete.
pause
