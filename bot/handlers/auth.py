"""
MOS-POOL Bot - Регистрация и авторизация
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import (
    get_user_by_telegram_id, create_user, get_session, User,
    get_pending_users, approve_user
)
from keyboards import main_menu_keyboard, user_management_keyboard
from config import ADMIN_TELEGRAM_ID, Role, UserStatus

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
WAITING_FULLNAME, WAITING_POSITION = range(2)


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /register - начало регистрации"""
    user = update.effective_user
    telegram_id = user.id
    
    # Проверяем, есть ли уже пользователь
    db_user = get_user_by_telegram_id(telegram_id)
    
    if db_user:
        if db_user.status == UserStatus.ACTIVE:
            await update.message.reply_text("✅ Вы уже зарегистрированы!")
            return ConversationHandler.END
        elif db_user.status == UserStatus.PENDING:
            await update.message.reply_text("⏳ Ваша заявка уже отправлена и ожидает проверки.")
            return ConversationHandler.END
        elif db_user.status == UserStatus.BLOCKED:
            await update.message.reply_text("🚫 Ваш доступ заблокирован.")
            return ConversationHandler.END
    
    await update.message.reply_text(
        "📝 **Регистрация в боте MOS-POOL**\n\n"
        "Введите ваше ФИО:",
        parse_mode="Markdown"
    )
    
    return WAITING_FULLNAME


async def receive_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение ФИО"""
    fullname = update.message.text.strip()
    
    if len(fullname) < 3:
        await update.message.reply_text("❌ Имя слишком короткое. Введите ФИО полностью:")
        return WAITING_FULLNAME
    
    context.user_data["fullname"] = fullname
    
    await update.message.reply_text(
        f"👋 Приятно познакомиться, {fullname}!\n\n"
        "Введите вашу должность в компании:"
    )
    
    return WAITING_POSITION


async def receive_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение должности и завершение регистрации"""
    position = update.message.text.strip()
    user = update.effective_user
    
    fullname = context.user_data.get("fullname", user.full_name)
    
    # Создаём пользователя
    session = get_session()
    try:
        new_user = User(
            telegram_id=user.id,
            username=user.username,
            full_name=fullname,
            position=position,
            role=Role.VIEWER,
            status=UserStatus.PENDING
        )
        session.add(new_user)
        session.commit()
        user_id = new_user.id
    finally:
        session.close()
    
    await update.message.reply_text(
        "✅ **Заявка отправлена!**\n\n"
        f"👤 ФИО: {fullname}\n"
        f"💼 Должность: {position}\n\n"
        "Администратор рассмотрит вашу заявку в ближайшее время.",
        parse_mode="Markdown"
    )
    
    # Уведомляем админа
    if ADMIN_TELEGRAM_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=f"📩 **Новая заявка на регистрацию!**\n\n"
                     f"👤 ФИО: {fullname}\n"
                     f"💼 Должность: {position}\n"
                     f"📱 Username: @{user.username or 'нет'}\n"
                     f"🆔 ID: `{user.id}`\n\n"
                     f"Для одобрения: /approve {user_id}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
    
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации"""
    await update.message.reply_text("❌ Регистрация отменена.")
    context.user_data.clear()
    return ConversationHandler.END


# ============ АДМИН ФУНКЦИИ ============

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /users - список пользователей"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.is_admin():
        await update.message.reply_text("❌ Только для администраторов.")
        return
    
    # Получаем пользователей
    session = get_session()
    try:
        users = session.query(User).order_by(User.created_at.desc()).all()
        
        if not users:
            await update.message.reply_text("📭 Нет пользователей.")
            return
        
        text = "👥 **Пользователи:**\n\n"
        
        for u in users:
            status_emoji = {
                UserStatus.PENDING: "⏳",
                UserStatus.ACTIVE: "✅",
                UserStatus.BLOCKED: "🚫",
            }.get(u.status, "❓")
            
            role_emoji = {
                Role.ADMIN: "👑",
                Role.EDITOR: "✏️",
                Role.VIEWER: "👁️",
            }.get(u.role, "")
            
            text += f"{status_emoji}{role_emoji} {u.full_name or u.username or u.telegram_id}\n"
            text += f"   └ ID: {u.id} | @{u.username or 'none'}\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    finally:
        session.close()


async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /approve [user_id] [role] - одобрить пользователя"""
    admin = get_user_by_telegram_id(update.effective_user.id)
    
    if not admin or not admin.is_admin():
        await update.message.reply_text("❌ Только для администраторов.")
        return
    
    args = context.args
    
    if not args:
        pending = get_pending_users()
        if not pending:
            await update.message.reply_text("✅ Нет заявок на рассмотрении.")
            return
        
        text = "⏳ **Заявки на рассмотрении:**\n\n"
        for u in pending:
            text += f"👤 {u.full_name}\n"
            text += f"   💼 {u.position or 'не указано'}\n"
            text += f"   📱 @{u.username or 'нет'}\n"
            text += f"   → /approve {u.id}\n\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
        return
    
    try:
        user_id = int(args[0])
        role = args[1] if len(args) > 1 else Role.EDITOR
        
        if role not in (Role.ADMIN, Role.EDITOR, Role.VIEWER):
            role = Role.EDITOR
        
        session = get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            
            if not user:
                await update.message.reply_text("❌ Пользователь не найден.")
                return
            
            user.status = UserStatus.ACTIVE
            user.role = role
            session.commit()
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"🎉 **Ваша заявка одобрена!**\n\n"
                         f"Роль: {role}\n\n"
                         f"Используйте /start для начала работы.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")
            
            await update.message.reply_text(
                f"✅ Пользователь {user.full_name} одобрен с ролью {role}."
            )
        
        finally:
            session.close()
    
    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя.")


async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reject [user_id] - отклонить заявку"""
    admin = get_user_by_telegram_id(update.effective_user.id)
    
    if not admin or not admin.is_admin():
        await update.message.reply_text("❌ Только для администраторов.")
        return
    
    args = context.args
    
    if not args:
        await update.message.reply_text("Использование: /reject [user_id]")
        return
    
    try:
        user_id = int(args[0])
        
        session = get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            
            if not user:
                await update.message.reply_text("❌ Пользователь не найден.")
                return
            
            # Удаляем или помечаем как отклоненного
            session.delete(user)
            session.commit()
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text="❌ К сожалению, ваша заявка отклонена."
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")
            
            await update.message.reply_text(f"❌ Заявка пользователя отклонена.")
        
        finally:
            session.close()
    
    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя.")
