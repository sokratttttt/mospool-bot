"""
MOS-POOL Bot - Обработчик /start и базовая навигация
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import get_user_by_telegram_id, create_user, get_session, User
from keyboards import main_menu_keyboard
from config import ADMIN_TELEGRAM_ID, Role, UserStatus

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    telegram_id = user.id
    
    # Проверяем, есть ли пользователь в БД
    db_user = get_user_by_telegram_id(telegram_id)
    
    if db_user is None:
        # Первый админ
        if telegram_id == ADMIN_TELEGRAM_ID:
            session = get_session()
            try:
                new_user = User(
                    telegram_id=telegram_id,
                    username=user.username,
                    full_name=user.full_name,
                    role=Role.ADMIN,
                    status=UserStatus.ACTIVE
                )
                session.add(new_user)
                session.commit()
                db_user = new_user
            finally:
                session.close()
            
            await update.message.reply_text(
                f"👋 Добро пожаловать, {user.first_name}!\n\n"
                "Вы зарегистрированы как **администратор**.\n\n"
                "Используйте меню ниже для управления ботом.",
                reply_markup=main_menu_keyboard(is_admin=True),
                parse_mode="Markdown"
            )
        else:
            # Новый пользователь - предлагаем регистрацию
            await update.message.reply_text(
                f"👋 Привет, {user.first_name}!\n\n"
                "🏊 Это бот для управления соцсетями компании **MOS-POOL**.\n\n"
                "Для получения доступа отправьте команду /register",
                parse_mode="Markdown"
            )
        return
    
    # Пользователь существует
    if db_user.status == UserStatus.PENDING:
        await update.message.reply_text(
            "⏳ Ваша заявка на рассмотрении.\n\n"
            "Администратор скоро её проверит."
        )
        return
    
    if db_user.status == UserStatus.BLOCKED:
        await update.message.reply_text(
            "🚫 Ваш доступ заблокирован.\n\n"
            "Обратитесь к администратору."
        )
        return
    
    # Активный пользователь
    is_admin = db_user.is_admin()
    is_editor = db_user.is_editor()
    
    role_text = {
        Role.ADMIN: "👑 Администратор",
        Role.EDITOR: "✏️ Редактор",
        Role.VIEWER: "👁️ Наблюдатель",
    }.get(db_user.role, "")
    
    await update.message.reply_text(
        f"👋 С возвращением, {user.first_name}!\n\n"
        f"Ваша роль: {role_text}\n\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard(is_admin=is_admin, is_editor=is_editor),
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📚 **Справка по боту MOS-POOL**

**Основные команды:**
/start - Главное меню
/help - Эта справка
/register - Запрос доступа

**Работа с постами:**
/new - Создать новый пост
/drafts - Мои черновики
/templates - Шаблоны постов

**AI генерация:**
/ai - Сгенерировать пост с ИИ
/ai_improve - Улучшить текст
/ai_hashtags - Подобрать хештеги

**Публикация:**
/publish - Опубликовать пост
/schedule - Запланировать
/queue - Очередь публикаций

**Администрирование:**
/users - Управление пользователями
/stats - Статистика
/settings - Настройки

/cancel - Отменить текущую операцию
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cancel"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if user and user.is_active():
        await update.message.reply_text(
            "❌ Операция отменена.",
            reply_markup=main_menu_keyboard(
                is_admin=user.is_admin(),
                is_editor=user.is_editor()
            )
        )
    else:
        await update.message.reply_text("❌ Операция отменена.")
    
    # Очищаем user_data
    context.user_data.clear()
    
    return ConversationHandler.END


async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок главного меню"""
    text = update.message.text
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.is_active():
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    # Маппинг кнопок на команды
    button_handlers = {
        "📝 Создать пост": "new_post",
        "🤖 AI генерация": "ai_menu",
        "📋 Мои черновики": "drafts",
        "📅 Очередь": "queue",
        "📊 Статистика": "stats",
        "📁 Шаблоны": "templates",
        "👥 Пользователи": "users",
        "⚙️ Настройки": "settings",
        "❓ Помощь": "help",
        "❌ Отмена": "cancel",
        "⬅️ Назад": "back",
    }
    
    action = button_handlers.get(text)
    
    if action == "help":
        await help_command(update, context)
    elif action == "cancel":
        await cancel_command(update, context)
    elif action:
        # Сохраняем действие для обработки в других хендлерах
        context.user_data["pending_action"] = action
        await update.message.reply_text(f"Загрузка {text}...")
