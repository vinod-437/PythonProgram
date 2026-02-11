@echo off
set "SOURCE_DIR=%~dp0\dist"
set "TARGET_DIR=C:\TpayBiometricProgram"
set "EXE_NAME=TanhkapayBiometricSync.exe"

echo Installing Tpay Biometric Program...

if not exist "%SOURCE_DIR%\%EXE_NAME%" (
    echo Source executable not found. Please build the project first.
    pause
    exit /b 1
)

if not exist "%TARGET_DIR%" (
    echo Creating target directory: %TARGET_DIR%
    mkdir "%TARGET_DIR%"
)

echo Copying files...
xcopy /E /I /Y "%SOURCE_DIR%\*" "%TARGET_DIR%\"

echo Creating Desktop Shortcut...
set "SCRIPT=%TEMP%\CreateShortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%SCRIPT%"
echo sLinkFile = "%USERPROFILE%\Desktop\Tpay Biometric Program.lnk" >> "%SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%SCRIPT%"
echo oLink.TargetPath = "%TARGET_DIR%\%EXE_NAME%" >> "%SCRIPT%"
echo oLink.WorkingDirectory = "%TARGET_DIR%" >> "%SCRIPT%"
echo oLink.Save >> "%SCRIPT%"

cscript /nologo "%SCRIPT%"
del "%SCRIPT%"

echo Installation Complete!
pause
