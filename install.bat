@echo off
:: ═══════════════════════════════════════════════════════════════
::  Smart Traffic AI – Windows Installer
::  Double-click or run:  install.bat
:: ═══════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║         SMART TRAFFIC AI – WINDOWS INSTALLER                ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

:: Virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated

:: Upgrade pip silently
pip install --upgrade pip --quiet

:: Install deps
echo [INFO] Installing dependencies - please wait...
pip install -r requirements.txt

:: Create dirs
if not exist "violations" mkdir violations
if not exist "static\css"  mkdir static\css
if not exist "static\js"   mkdir static\js

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║  Installation complete!                                      ║
echo ║                                                              ║
echo ║  Run the system:   python run.py                             ║
echo ║  Dashboard:        http://127.0.0.1:8000                     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
pause
