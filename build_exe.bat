
@echo off
echo Building PaythonProgram Executable...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Activate Virtual Environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Install dependencies if needed (including pyinstaller)
pip install -r requirements.txt

REM Run PyInstaller
echo Creating executable...
pyinstaller --noconfirm --onefile --console --name "PaythonProgram" --add-data "config;config" --paths "src" src/main.py

echo Build Complete. Checking dist folder...
if exist "dist\PaythonProgram.exe" (
    echo Executable created successfully at dist\PaythonProgram.exe
) else (
    echo Build failed.
)
pause
