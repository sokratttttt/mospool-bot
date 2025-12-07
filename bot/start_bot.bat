@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   MOS-POOL Telegram Bot
echo ========================================
echo.

cd /d "%~dp0"

REM Создаём папку data если нет
if not exist "data" mkdir data

REM Создаём venv если нет
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Активируем venv
call venv\Scripts\activate.bat

REM Устанавливаем зависимости
echo Installing dependencies...
pip install -r requirements.txt -q

REM Проверяем .env
if not exist ".env" (
    echo.
    echo ⚠️  Файл .env не найден!
    echo.
    echo 1. Скопируйте .env.example в .env
    echo 2. Заполните TELEGRAM_BOT_TOKEN и другие настройки
    echo.
    pause
    exit /b 1
)

echo.
echo Starting bot...
echo.

python main.py

pause
