"""
MOS-POOL Telegram Bot
=====================
Бот для управления публикациями в социальных сетях компании MOS-POOL.

Запуск: python main.py
"""
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)

from config import TELEGRAM_BOT_TOKEN
from database import init_db
from handlers import (
    # Start & Help
    start_command, help_command, cancel_command, handle_menu_button,
    # Auth
    register_command, receive_fullname, receive_position, cancel_registration,
    users_command, approve_command, reject_command,
    WAITING_FULLNAME, WAITING_POSITION,
    # Posts
    new_post_command, receive_content, drafts_command, queue_command,
    post_callback, select_channels_callback, cancel_post_creation,
    WAITING_CONTENT, WAITING_CHANNELS,
    # AI
    ai_command, ai_select_type, ai_input_data, ai_result_callback,
    ai_quick_command, ai_improve_command, ai_hashtags_command,
    AI_SELECT_TYPE, AI_INPUT_DATA, AI_RESULT,
    # Publish
    publish_command, schedule_command, schedule_callback,
    queue_scheduled_command, test_publish_command,
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('data/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Запуск бота"""
    
    # Проверка токена
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не настроен!")
        print("\n⚠️  Добавьте TELEGRAM_BOT_TOKEN в файл .env")
        print("   Получить токен: @BotFather в Telegram\n")
        return
    
    # Инициализация БД
    init_db()
    logger.info("✅ Database initialized")
    
    # Создание приложения
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ============ CONVERSATION HANDLERS ============
    
    # Регистрация
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_command)],
        states={
            WAITING_FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_fullname)],
            WAITING_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_position)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_registration),
            MessageHandler(filters.Regex("^❌ Отмена$"), cancel_registration),
        ],
    )
    
    # Создание поста
    new_post_handler = ConversationHandler(
        entry_points=[
            CommandHandler("new", new_post_command),
            MessageHandler(filters.Regex("^📝 Создать пост$"), new_post_command),
        ],
        states={
            WAITING_CONTENT: [MessageHandler(filters.TEXT, receive_content)],
            WAITING_CHANNELS: [CallbackQueryHandler(select_channels_callback)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_post_creation),
            MessageHandler(filters.Regex("^❌ Отмена$"), cancel_post_creation),
        ],
    )
    
    # AI генерация
    ai_handler = ConversationHandler(
        entry_points=[
            CommandHandler("ai", ai_command),
            MessageHandler(filters.Regex("^🤖 AI генерация$"), ai_command),
        ],
        states={
            AI_SELECT_TYPE: [CallbackQueryHandler(ai_select_type)],
            AI_INPUT_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_input_data)],
            AI_RESULT: [CallbackQueryHandler(ai_result_callback)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
        ],
    )
    
    # ============ COMMAND HANDLERS ============
    
    # Основные команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    # Регистрация и авторизация
    app.add_handler(registration_handler)
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("reject", reject_command))
    
    # Работа с постами
    app.add_handler(new_post_handler)
    app.add_handler(CommandHandler("drafts", drafts_command))
    app.add_handler(CommandHandler("queue", queue_command))
    
    # AI генерация
    app.add_handler(ai_handler)
    app.add_handler(CommandHandler("ai_quick", ai_quick_command))
    app.add_handler(CommandHandler("ai_improve", ai_improve_command))
    app.add_handler(CommandHandler("ai_hashtags", ai_hashtags_command))
    
    # Публикация
    app.add_handler(CommandHandler("publish", publish_command))
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CommandHandler("test_publish", test_publish_command))
    
    # ============ CALLBACK HANDLERS ============
    
    app.add_handler(CallbackQueryHandler(post_callback, pattern="^post_"))
    app.add_handler(CallbackQueryHandler(schedule_callback, pattern="^schedule:"))
    app.add_handler(CallbackQueryHandler(select_channels_callback, pattern="^channel"))
    
    # ============ MESSAGE HANDLERS ============
    
    # Обработка кнопок меню
    app.add_handler(MessageHandler(
        filters.Regex("^(📝 Создать пост|🤖 AI генерация|📋 Мои черновики|📅 Очередь|"
                     "📊 Статистика|📁 Шаблоны|👥 Пользователи|⚙️ Настройки|❓ Помощь)$"),
        handle_menu_button
    ))
    
    # ============ ЗАПУСК ============
    
    logger.info("🚀 Bot starting...")
    print("\n" + "="*50)
    print("  🏊 MOS-POOL Telegram Bot")
    print("="*50)
    print("\n✅ Бот запущен!")
    print("📱 Откройте бота в Telegram и отправьте /start")
    print("\n🛑 Для остановки нажмите Ctrl+C\n")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
