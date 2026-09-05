@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   Supermarket POS - Automated Windows Setup Builder
echo ============================================================
echo.

:: 1. Check Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH.
    echo Please install Python 3.11 or 3.12 from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Installing Python requirements...
python -m pip install --upgrade pip
pip install -r supermarket_pos\requirements.txt
pip install pyinstaller
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)

echo.
echo [2/4] Building application package with PyInstaller...
cd supermarket_pos
pyinstaller --noconfirm supermarket_pos.spec
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Main application compilation failed.
    cd ..
    pause
    exit /b 1
)
pyinstaller --noconfirm --onefile --console --name updater updater\updater.py
cd ..
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller compilation failed.
    pause
    exit /b 1
)

echo.
echo [3/4] Locating Inno Setup Compiler (ISCC)...
set "ISCC_PATH="
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\iscc.exe"
) else if exist "C:\Program Files\Inno Setup 6\iscc.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\iscc.exe"
) else (
    where iscc >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        set "ISCC_PATH=iscc"
    )
)

if not defined ISCC_PATH (
    echo.
    echo [WARNING] Inno Setup 6 was not detected on this machine.
    echo The compiled standalone application is ready at:
    echo   supermarket_pos\dist\supermarket_pos\supermarket_pos.exe
    echo.
    echo To compile the Setup.exe installer:
    echo 1. Download and install Inno Setup 6 from: https://jrsoftware.org/isdl.php
    echo 2. Re-run this build_setup.bat script.
    echo.
    pause
    exit /b 0
)

echo Found Inno Setup at: "!ISCC_PATH!"
echo.
echo [4/4] Compiling Supermarket_POS_Setup.exe...
"!ISCC_PATH!" installer\supermarket_pos.iss
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Inno Setup compilation failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   SUCCESS!
echo   Setup installer created successfully at:
echo   dist_installer\Supermarket_POS_Setup.exe
echo ============================================================
echo.
pause
