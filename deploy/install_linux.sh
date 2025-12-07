#!/bin/bash
# Pool Social Media Automation - Linux Installation Script
# Run as root: sudo bash install_linux.sh

set -e

APP_DIR="/opt/pool-social"
SERVICE_FILE="/etc/systemd/system/pool-social.service"
LOG_DIR="/var/log/pool-social"

echo "========================================"
echo " Installing Pool Social Media System"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo bash install_linux.sh"
    exit 1
fi

# Install Python if not installed
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3..."
    apt update
    apt install -y python3 python3-pip python3-venv
fi

# Create application directory
echo "Creating application directory..."
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"

# Copy application files (assumes script is run from project directory)
echo "Copying application files..."
cp -r . "$APP_DIR/"

# Set permissions
chown -R www-data:www-data "$APP_DIR"
chown -R www-data:www-data "$LOG_DIR"

# Create virtual environment and install dependencies
echo "Setting up Python environment..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env from example if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit $APP_DIR/.env with your API keys!"
    echo ""
fi

# Run migrations
echo "Running database migrations..."
python manage.py makemigrations posts
python manage.py migrate

# Create logs directory for Django
mkdir -p logs

# Install systemd service
echo "Installing systemd service..."
cp deploy/pool-social.service "$SERVICE_FILE"

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable pool-social

echo ""
echo "========================================"
echo " Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit config: nano $APP_DIR/.env"
echo "2. Create admin user: cd $APP_DIR && source venv/bin/activate && python manage.py createsuperuser"
echo "3. Start service: systemctl start pool-social"
echo "4. Check status: systemctl status pool-social"
echo "5. View logs: tail -f /var/log/pool-social/app.log"
echo ""
echo "Web interface: http://YOUR_SERVER_IP:8000"
echo ""
