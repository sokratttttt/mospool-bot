#!/bin/bash
# Pool Social Media Automation - Linux Startup Script

echo "========================================"
echo " Pool Social Media Automation System"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Create logs directory
mkdir -p logs

# Run migrations if database doesn't exist
if [ ! -f "db.sqlite3" ]; then
    echo ""
    echo "Initializing database..."
    python manage.py makemigrations posts
    python manage.py migrate
    echo ""
    echo "Creating superuser..."
    python manage.py createsuperuser
fi

echo ""
echo "Starting server..."
echo "Open http://127.0.0.1:8000 in your browser"
echo "Press Ctrl+C to stop"
echo ""

python manage.py runserver 0.0.0.0:8000
