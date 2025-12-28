@echo off
REM Cortensor Agent Auditor - Quick Setup Script (Windows)
REM This script automates the initial setup process

echo ===============================================
echo  Cortensor Agent Auditor - Quick Setup
echo ===============================================
echo.

REM Check prerequisites
echo Checking prerequisites...

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    exit /b 1
)

where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    exit /b 1
)

where psql >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PostgreSQL not found. Please install PostgreSQL 14+
    exit /b 1
)

echo [OK] All prerequisites found!
echo.

REM Create .env if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo [WARNING] Please edit .env with your credentials before continuing!
    echo   Required: PRIVATE_KEY, SESSION_V2_ADDRESS, SESSION_QUEUE_V2_ADDRESS, PINATA_API_KEY
    pause
)

REM Create database
echo Setting up database...
set /p DB_NAME="Enter PostgreSQL database name (default: cortensor_auditor): "
if "%DB_NAME%"=="" set DB_NAME=cortensor_auditor

REM Create database
createdb %DB_NAME% 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Database %DB_NAME% created
) else (
    echo [WARNING] Database might already exist. Continuing...
)

REM Apply schema
echo Applying database schema...
psql %DB_NAME% < database\schema.sql
echo [OK] Schema applied
echo.

REM Backend setup
echo Setting up Python backend...

REM Create virtual environment
if not exist venv (
    python -m venv venv
    echo [OK] Virtual environment created
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo [OK] Python dependencies installed
echo.

REM Frontend setup
echo Setting up React frontend...
cd frontend

REM Install dependencies
echo Installing Node.js dependencies...
call npm install --silent
echo [OK] Node.js dependencies installed

cd ..

REM Summary
echo.
echo ===============================================
echo  Setup complete!
echo ===============================================
echo.
echo Next steps:
echo 1. Ensure .env is configured with your credentials
echo 2. Start backend:  venv\Scripts\activate.bat ^&^& python -m backend.main
echo 3. Start frontend: cd frontend ^&^& npm run dev
echo 4. Visit http://localhost:3000
echo.
echo Happy hacking!
pause
