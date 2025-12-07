"""
MOS-POOL Bot - Публикация и планирование
"""
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from database import get_user_by_telegram_id, get_session, Post, Publication, get_scheduled_posts
from keyboards import channels_keyboard, schedule_keyboard, post_actions_keyboard
from utils.vk_client import get_vk_client
from config import PostStatus, TELEGRAM_CHANNEL_ID, TELEGRAM_TEST_CHANNEL_ID

logger = logging.getLogger(__name__)


async def publish_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /publish - публикация поста"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.can_publish():
        await update.message.reply_text("❌ У вас нет прав на публикацию.")
        return
    
    args = context.args
    
    if not args:
        # Показываем одобренные посты
        session = get_session()
        try:
            posts = session.query(Post).filter(
                Post.status == PostStatus.APPROVED
            ).order_by(Post.created_at.desc()).limit(10).all()
            
            if not posts:
                await update.message.reply_text(
                    "📭 Нет одобренных постов для публикации.\n\n"
                    "Сначала создайте и одобрите пост."
                )
                return
            
            text = "📤 **Посты, готовые к публикации:**\n\n"
            for post in posts:
                text += f"• #{post.id}: {post.content[:40]}...\n"
            
            text += "\nДля публикации: /publish [ID]"
            
            await update.message.reply_text(text, parse_mode="Markdown")
        finally:
            session.close()
        return
    
    # Публикуем конкретный пост
    try:
        post_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Неверный ID поста.")
        return
    
    await publish_post(update, context, post_id)


async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE, post_id: int):
    """Публикация поста"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    session = get_session()
    try:
        post = session.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            await update.message.reply_text("❌ Пост не найден.")
            return
        
        if post.status != PostStatus.APPROVED:
            await update.message.reply_text("❌ Пост не одобрен для публикации.")
            return
        
        channels = post.channels or ["telegram"]
        results = []
        
        # Публикация в Telegram
        if "telegram" in channels and TELEGRAM_CHANNEL_ID:
            try:
                message = await context.bot.send_message(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    text=post.content,
                    parse_mode="HTML"
                )
                
                pub = Publication(
                    post_id=post.id,
                    channel_type="telegram",
                    channel_id=TELEGRAM_CHANNEL_ID,
                    status="success",
                    external_id=str(message.message_id),
                    published_at=datetime.utcnow()
                )
                session.add(pub)
                results.append(f"✅ Telegram: опубликовано")
                
            except Exception as e:
                logger.error(f"Telegram publish error: {e}")
                pub = Publication(
                    post_id=post.id,
                    channel_type="telegram",
                    channel_id=TELEGRAM_CHANNEL_ID,
                    status="failed",
                    error_message=str(e)
                )
                session.add(pub)
                results.append(f"❌ Telegram: {e}")
        
        # Публикация в VK
        if "vk" in channels:
            vk_client = get_vk_client()
            
            if vk_client.is_configured():
                result = vk_client.publish_post(post.content)
                
                if result:
                    pub = Publication(
                        post_id=post.id,
                        channel_type="vk",
                        channel_id=str(vk_client.group_id),
                        status="success",
                        external_id=str(result["post_id"]),
                        external_url=result["url"],
                        published_at=datetime.utcnow()
                    )
                    session.add(pub)
                    results.append(f"✅ VK: {result['url']}")
                else:
                    results.append("❌ VK: ошибка публикации")
            else:
                results.append("⚠️ VK: не настроен")
        
        # Обновляем статус поста
        post.status = PostStatus.PUBLISHED
        post.published_at = datetime.utcnow()
        session.commit()
        
        result_text = "\n".join(results)
        await update.message.reply_text(
            f"📤 **Пост #{post_id} опубликован!**\n\n{result_text}",
            parse_mode="Markdown"
        )
        
    finally:
        session.close()


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /schedule - планирование публикации"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.can_publish():
        await update.message.reply_text("❌ У вас нет прав на планирование.")
        return
    
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Использование: /schedule [post_id]\n\n"
            "Пример: /schedule 5"
        )
        return
    
    try:
        post_id = int(args[0])
        context.user_data["schedule_post_id"] = post_id
        
        await update.message.reply_text(
            f"📅 Когда опубликовать пост #{post_id}?",
            reply_markup=schedule_keyboard()
        )
    except ValueError:
        await update.message.reply_text("❌ Неверный ID поста.")


async def schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора времени"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    post_id = context.user_data.get("schedule_post_id")
    
    if not post_id:
        await query.edit_message_text("❌ Ошибка. Попробуйте /schedule снова.")
        return
    
    if data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Планирование отменено.")
        return
    
    now = datetime.now()
    scheduled_time = None
    
    if data == "schedule:1h":
        scheduled_time = now + timedelta(hours=1)
    elif data == "schedule:3h":
        scheduled_time = now + timedelta(hours=3)
    elif data == "schedule:tomorrow":
        scheduled_time = now.replace(hour=10, minute=0, second=0) + timedelta(days=1)
    elif data == "schedule:tomorrow_evening":
        scheduled_time = now.replace(hour=18, minute=0, second=0) + timedelta(days=1)
    elif data == "schedule:custom":
        await query.edit_message_text(
            "📅 Введите дату и время в формате:\n"
            "`ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
            "Например: `25.12.2024 15:00`",
            parse_mode="Markdown"
        )
        context.user_data["waiting_schedule_time"] = True
        return
    
    if scheduled_time:
        await set_schedule(query, post_id, scheduled_time)
        context.user_data.clear()


async def set_schedule(query, post_id: int, scheduled_time: datetime):
    """Установка времени публикации"""
    session = get_session()
    try:
        post = session.query(Post).filter(Post.id == post_id).first()
        
        if post:
            post.scheduled_for = scheduled_time
            session.commit()
            
            await query.edit_message_text(
                f"✅ Пост #{post_id} запланирован на:\n\n"
                f"📅 {scheduled_time.strftime('%d.%m.%Y %H:%M')}"
            )
    finally:
        session.close()


async def queue_scheduled_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать очередь запланированных постов"""
    posts = get_scheduled_posts()
    
    if not posts:
        await update.message.reply_text("📭 Очередь публикаций пуста.")
        return
    
    text = "📅 **Запланированные публикации:**\n\n"
    
    for post in posts:
        time_str = post.scheduled_for.strftime("%d.%m %H:%M") if post.scheduled_for else "—"
        channels = ", ".join(post.channels or [])
        
        text += f"🕐 {time_str}\n"
        text += f"   #{post.id}: {post.content[:30]}...\n"
        text += f"   📢 {channels}\n\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def test_publish_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая публикация в тестовый канал"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.is_editor():
        await update.message.reply_text("❌ Нет доступа.")
        return
    
    if not TELEGRAM_TEST_CHANNEL_ID:
        await update.message.reply_text("⚠️ Тестовый канал не настроен.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /test_publish [post_id]")
        return
    
    try:
        post_id = int(args[0])
        
        session = get_session()
        try:
            post = session.query(Post).filter(Post.id == post_id).first()
            
            if not post:
                await update.message.reply_text("❌ Пост не найден.")
                return
            
            message = await context.bot.send_message(
                chat_id=TELEGRAM_TEST_CHANNEL_ID,
                text=f"🧪 ТЕСТ\n\n{post.content}",
                parse_mode="HTML"
            )
            
            await update.message.reply_text(
                f"✅ Тестовая публикация отправлена в {TELEGRAM_TEST_CHANNEL_ID}"
            )
            
        finally:
            session.close()
    
    except ValueError:
        await update.message.reply_text("❌ Неверный ID поста.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
