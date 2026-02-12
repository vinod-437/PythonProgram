@echo off
echo Building PaythonProgram Executable...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Clean previous build
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM Run PyInstaller
echo Creating executable...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "TanhkapayBiometricSync" --icon "assets\fileicon.ico" --add-data "assets;assets" run_gui.py

if %errorlevel% neq 0 (
    echo PyInstaller failed.
    pause
    exit /b 1
)

echo Copying configuration...
if not exist "dist\config" mkdir "dist\config"
copy "config\.env" "dist\config\.env"
copy "config\*.py" "dist\config\"

echo Build Complete.
if exist "dist\TanhkapayBiometricSync.exe" (
    echo Executable created successfully at dist\TanhkapayBiometricSync.exe
    echo Configuration copied to dist\config
) else (
    echo Build failed.
[diff_block_end]
)
pause
