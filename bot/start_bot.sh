#!/bin/bash
# MOS-POOL Telegram Bot - Linux/macOS

echo ""
echo "========================================"
echo "  MOS-POOL Telegram Bot"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# Создаём папку data
mkdir -p data

# Создаём venv если нет
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Активируем venv
source venv/bin/activate

# Устанавливаем зависимости
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Проверяем .env
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Файл .env не найден!"
    echo ""
    echo "1. Скопируйте: cp .env.example .env"
    echo "2. Заполните TELEGRAM_BOT_TOKEN и другие настройки"
    echo ""
    exit 1
fi

echo ""
echo "Starting bot..."
echo ""

python main.py
