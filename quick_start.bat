@echo off
REM Quick start script for Windows
echo ========================================
echo Deep Research Backend - Quick Start
echo ========================================
echo.

echo [1/5] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.11+
    pause
    exit /b 1
)
echo.

echo [2/5] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo [3/5] Checking for .env file...
if not exist .env (
    echo WARNING: .env file not found!
    echo Please create .env file with your configuration.
    echo See .env.example for reference.
    echo.
    pause
)
echo.

echo [4/5] Running database migrations...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Database migration failed!
    echo Please check your database configuration in .env
    pause
    exit /b 1
)
echo.

echo [5/5] Setup complete!
echo.
echo ========================================
echo Next steps:
echo ========================================
echo 1. Make sure PostgreSQL is running
echo 2. Make sure Redis is running
echo 3. Start Django server: python manage.py runserver
echo 4. Start Celery worker: celery -A creston worker --loglevel=info --pool=solo
echo.
echo For detailed instructions, see HOW_TO_RUN.md
echo ========================================
pause

