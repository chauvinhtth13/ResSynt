@echo off
REM Start Celery Worker and Beat for Windows
echo Starting Celery Worker and Beat for ResSync...
echo.

REM Check if Redis is running
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Redis is not running!
    echo Please start Redis first:
    echo   - Install: https://github.com/microsoftarchive/redis/releases
    echo   - Or use Docker: docker run -d -p 6379:6379 redis:latest
    echo.
    pause
    exit /b 1
)

echo [OK] Redis is running
echo.

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start Celery worker with beat
echo Starting Celery worker with beat scheduler...
echo.
echo Press Ctrl+C to stop
echo.

celery -A config worker --beat --loglevel=info --pool=solo

pause
