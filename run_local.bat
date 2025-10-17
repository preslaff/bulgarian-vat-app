@echo off
echo Starting Bulgarian VAT System Locally...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo Setting up backend environment...
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt

REM Start backend in background
echo Starting FastAPI backend on port 8000...
start "VAT Backend" cmd /c "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

cd ..\frontend

REM Install frontend dependencies
if not exist "node_modules" (
    echo Installing frontend dependencies...
    npm install
)

REM Start frontend
echo Starting Svelte frontend on port 5173...
start "VAT Frontend" cmd /c "npm run dev"

echo.
echo ========================================
echo   Bulgarian VAT System Started!
echo ========================================
echo   Frontend: http://localhost:5173
echo   Backend API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to stop all services...
pause >nul

REM Kill background processes
taskkill /f /im python.exe 2>nul
taskkill /f /im node.exe 2>nul

echo Services stopped.
pause