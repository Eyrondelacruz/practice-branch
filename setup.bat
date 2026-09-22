@echo off
echo ============================================
echo  Smart School ID Attendance Scanner Setup
echo ============================================

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause & exit /b 1
)

:: Create virtual environment
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate and install
call .venv\Scripts\activate.bat
echo Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q

:: pyzbar on Windows needs the zbar DLL — install via wheel
pip install pyzbar --find-links https://github.com/NaturalHistoryMuseum/pyzbar/releases -q 2>nul

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Edit .env with your Supabase / Twilio / Gmail credentials
echo   2. Run:  .venv\Scripts\activate  ^&^&  python -m uvicorn main:app --reload
echo   3. Open: http://localhost:8000
echo.
pause
