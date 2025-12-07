@echo off
echo ========================================
echo  Pool Social Media Automation System
echo ========================================
echo.

cd /d "D:\mos-pool channel"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt --quiet

if not exist "logs" mkdir logs

if not exist "db.sqlite3" (
    echo.
    echo Initializing database...
    python manage.py makemigrations posts
    python manage.py migrate
    echo.
    echo Creating superuser...
    python manage.py createsuperuser
)

echo.
echo Starting server...
echo Open http://127.0.0.1:8000 in your browser
echo Press Ctrl+C to stop
echo.

python manage.py runserver

pause
