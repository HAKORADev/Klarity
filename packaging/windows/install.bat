@echo off
setlocal enabledelayedexpansion

REM Klarity - Install desktop shortcut, Start Menu entry, and PATH

set "KLARITY_DIR=%~dp0"
set "KLARITY_EXE=%KLARITY_DIR%klarity.exe"
set "KLARITY_ICON=%KLARITY_DIR%logo.ico"

if not exist "%KLARITY_EXE%" (
    echo ERROR: klarity.exe not found at %KLARITY_EXE%
    pause
    exit /b 1
)

echo Creating desktop shortcut...
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Klarity.lnk"

powershell -Command "$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut(%SHORTCUT_PATH%); $s.TargetPath = %KLARITY_EXE%; $s.WorkingDirectory = %KLARITY_DIR%; $s.IconLocation = %KLARITY_ICON%,0; $s.Description = Klarity; $s.Save()"

set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%STARTMENU%\Klarity" mkdir "%STARTMENU%\Klarity"
set "SM_PATH=%STARTMENU%\Klarity\Klarity.lnk"

powershell -Command "$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut(%SM_PATH%); $s.TargetPath = %KLARITY_EXE%; $s.WorkingDirectory = %KLARITY_DIR%; $s.IconLocation = %KLARITY_ICON%,0; $s.Description = Klarity; $s.Save()"

echo Adding Klarity to user PATH...
set "PATH_KEY=HKCU\Environment"
set "CURRENT_PATH="

for /f "tokens=2*" %%A in ('reg query "%PATH_KEY%" /v Path 2^>nul') do set "CURRENT_PATH=%%B"

echo %CURRENT_PATH% | findstr /I /C:"%KLARITY_DIR%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Klarity directory already in PATH - skipping
) else (
    if defined CURRENT_PATH (
        reg add "%PATH_KEY%" /v Path /t REG_EXPAND_SZ /d "%CURRENT_PATH%;%KLARITY_DIR%" /f >nul 2>&1
    ) else (
        reg add "%PATH_KEY%" /v Path /t REG_EXPAND_SZ /d "%KLARITY_DIR%" /f >nul 2>&1
    )
    echo Added to user PATH
)

echo.
echo ============================================================
echo  Klarity installed successfully!
echo ============================================================
echo.
echo  Desktop shortcut:  %SHORTCUT_PATH%
echo  Start Menu:        %SM_PATH%
echo  PATH:              %KLARITY_DIR%
echo.
echo  Open a NEW terminal and run: klarity info
echo.
echo ============================================================
echo.
pause
