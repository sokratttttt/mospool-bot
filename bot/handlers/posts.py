"""
MOS-POOL Bot - Работа с постами
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import get_user_by_telegram_id, get_session, Post, get_user_posts
from keyboards import (
    main_menu_keyboard, post_actions_keyboard, cancel_keyboard,
    channels_keyboard, posts_list_keyboard
)
from config import PostStatus, MIN_POST_LENGTH, MAX_POST_LENGTH

logger = logging.getLogger(__name__)

# Состояния
WAITING_TITLE, WAITING_CONTENT, WAITING_MEDIA, WAITING_CHANNELS = range(4)


async def new_post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /new - создание нового поста"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.can_create_posts():
        await update.message.reply_text("❌ У вас нет прав на создание постов.")
        return ConversationHandler.END
    
    context.user_data["new_post"] = {}
    
    await update.message.reply_text(
        "📝 **Создание нового поста**\n\n"
        "Введите текст поста (можно добавить эмодзи и хештеги):\n\n"
        f"_Минимум {MIN_POST_LENGTH} символов_",
        reply_markup=cancel_keyboard(),
        parse_mode="Markdown"
    )
    
    return WAITING_CONTENT


async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение текста поста"""
    content = update.message.text
    
    if content == "❌ Отмена":
        return await cancel_post_creation(update, context)
    
    if len(content) < MIN_POST_LENGTH:
        await update.message.reply_text(
            f"❌ Текст слишком короткий. Минимум {MIN_POST_LENGTH} символов.\n\n"
            "Введите текст поста:"
        )
        return WAITING_CONTENT
    
    if len(content) > MAX_POST_LENGTH:
        await update.message.reply_text(
            f"❌ Текст слишком длинный. Максимум {MAX_POST_LENGTH} символов.\n\n"
            f"Ваш текст: {len(content)} символов. Сократите его:"
        )
        return WAITING_CONTENT
    
    context.user_data["new_post"]["content"] = content
    
    await update.message.reply_text(
        "✅ Текст сохранён!\n\n"
        "📷 Отправьте фото для поста или нажмите «Пропустить»:",
        reply_markup=cancel_keyboard()
    )
    
    # Для простоты пока пропускаем медиа
    # TODO: Добавить обработку медиа
    
    await update.message.reply_text(
        "🌐 Выберите каналы для публикации:",
        reply_markup=channels_keyboard()
    )
    
    return WAITING_CHANNELS


async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение медиа"""
    # TODO: Реализовать загрузку фото/видео
    pass


async def select_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора каналов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("channel_toggle:"):
        channel = data.split(":")[1]
        selected = context.user_data.get("selected_channels", [])
        
        if channel in selected:
            selected.remove(channel)
        else:
            selected.append(channel)
        
        context.user_data["selected_channels"] = selected
        
        await query.edit_message_reply_markup(
            reply_markup=channels_keyboard(selected)
        )
    
    elif data == "channels_done":
        selected = context.user_data.get("selected_channels", [])
        
        if not selected:
            await query.answer("⚠️ Выберите хотя бы один канал!", show_alert=True)
            return
        
        # Сохраняем пост
        await save_post(update, context)
        return ConversationHandler.END
    
    elif data == "cancel":
        await cancel_post_creation(update, context)
        return ConversationHandler.END


async def save_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение поста в БД"""
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    post_data = context.user_data.get("new_post", {})
    content = post_data.get("content", "")
    channels = context.user_data.get("selected_channels", [])
    
    session = get_session()
    try:
        post = Post(
            content=content,
            title=content[:50] + "..." if len(content) > 50 else content,
            author_id=user.id,
            status=PostStatus.DRAFT,
            channels=channels,
            media_urls=[]
        )
        session.add(post)
        session.commit()
        post_id = post.id
    finally:
        session.close()
    
    # Очищаем данные
    context.user_data.clear()
    
    await query.edit_message_text(
        f"✅ **Пост #{post_id} создан!**\n\n"
        f"📝 {content[:100]}{'...' if len(content) > 100 else ''}\n\n"
        f"📢 Каналы: {', '.join(channels)}\n"
        f"📊 Статус: Черновик\n\n"
        "Что делать дальше?",
        reply_markup=post_actions_keyboard(post_id, PostStatus.DRAFT, user.can_publish()),
        parse_mode="Markdown"
    )


async def cancel_post_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания поста"""
    context.user_data.clear()
    
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if update.callback_query:
        await update.callback_query.edit_message_text("❌ Создание поста отменено.")
    else:
        await update.message.reply_text(
            "❌ Создание поста отменено.",
            reply_markup=main_menu_keyboard(
                is_admin=user.is_admin() if user else False,
                is_editor=user.is_editor() if user else False
            )
        )
    
    return ConversationHandler.END


async def drafts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /drafts - мои черновики"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.is_active():
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    posts = get_user_posts(user.id, status=PostStatus.DRAFT)
    
    if not posts:
        await update.message.reply_text(
            "📭 У вас нет черновиков.\n\n"
            "Создайте новый пост: /new"
        )
        return
    
    await update.message.reply_text(
        "📋 **Ваши черновики:**",
        reply_markup=posts_list_keyboard(posts),
        parse_mode="Markdown"
    )


async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /queue - очередь публикаций"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.is_active():
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    session = get_session()
    try:
        posts = session.query(Post).filter(
            Post.status.in_([PostStatus.APPROVED, PostStatus.PENDING]),
            Post.scheduled_for != None
        ).order_by(Post.scheduled_for).all()
        
        if not posts:
            await update.message.reply_text(
                "📭 Очередь публикаций пуста."
            )
            return
        
        text = "📅 **Очередь публикаций:**\n\n"
        
        for post in posts:
            status_emoji = "⏳" if post.status == PostStatus.PENDING else "✅"
            scheduled = post.scheduled_for.strftime("%d.%m %H:%M") if post.scheduled_for else "—"
            
            text += f"{status_emoji} #{post.id}\n"
            text += f"   📝 {post.content[:40]}...\n"
            text += f"   🕐 {scheduled}\n\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    finally:
        session.close()


async def post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий с постом"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if data.startswith("post_view:"):
        post_id = int(data.split(":")[1])
        await show_post(query, post_id, user)
    
    elif data.startswith("post_edit:"):
        post_id = int(data.split(":")[1])
        # TODO: Редактирование поста
        await query.answer("Редактирование пока не реализовано", show_alert=True)
    
    elif data.startswith("post_submit:"):
        post_id = int(data.split(":")[1])
        await submit_post_for_review(query, post_id, user, context)
    
    elif data.startswith("post_approve:"):
        post_id = int(data.split(":")[1])
        await approve_post(query, post_id, user)
    
    elif data.startswith("post_delete:"):
        post_id = int(data.split(":")[1])
        await delete_post(query, post_id, user)
    
    elif data == "posts_list":
        posts = get_user_posts(user.id) if user else []
        await query.edit_message_text(
            "📋 **Ваши посты:**",
            reply_markup=posts_list_keyboard(posts),
            parse_mode="Markdown"
        )


async def show_post(query, post_id: int, user):
    """Показать детали поста"""
    session = get_session()
    try:
        post = session.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            await query.answer("Пост не найден", show_alert=True)
            return
        
        status_text = {
            PostStatus.DRAFT: "📝 Черновик",
            PostStatus.PENDING: "⏳ На проверке",
            PostStatus.APPROVED: "✅ Одобрен",
            PostStatus.PUBLISHED: "📤 Опубликован",
            PostStatus.REJECTED: "❌ Отклонён",
        }.get(post.status, post.status)
        
        text = f"📄 **Пост #{post.id}**\n\n"
        text += f"📊 Статус: {status_text}\n"
        text += f"📢 Каналы: {', '.join(post.channels or [])}\n"
        text += f"📅 Создан: {post.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        text += f"📝 **Текст:**\n{post.content}"
        
        await query.edit_message_text(
            text,
            reply_markup=post_actions_keyboard(post.id, post.status, user.can_publish() if user else False),
            parse_mode="Markdown"
        )
    finally:
        session.close()


async def submit_post_for_review(query, post_id: int, user, context):
    """Отправить пост на проверку"""
    session = get_session()
    try:
        post = session.query(Post).filter(Post.id == post_id).first()
        
        if post and post.author_id == user.id:
            post.status = PostStatus.PENDING
            session.commit()
            
            await query.edit_message_text(
                f"✅ Пост #{post_id} отправлен на проверку!",
                reply_markup=post_actions_keyboard(post_id, PostStatus.PENDING, False)
            )
            
            # Уведомляем админов
            # TODO: Уведомление админам
    finally:
        session.close()


async def approve_post(query, post_id: int, user):
    """Одобрить пост"""
    if not user or not user.can_publish():
        await query.answer("Нет прав", show_alert=True)
        return
    
    session = get_session()
    try:
        post = session.query(Post).filter(Post.id == post_id).first()
        
        if post:
            post.status = PostStatus.APPROVED
            post.approved_by_id = user.id
            session.commit()
            
            await query.edit_message_text(
                f"✅ Пост #{post_id} одобрен!\n\n"
                "Теперь его можно опубликовать или запланировать.",
                reply_markup=post_actions_keyboard(post_id, PostStatus.APPROVED, True)
            )
    finally:
        session.close()


async def delete_post(query, post_id: int, user):
    """Удалить пост"""
    session = get_session()
    try:
        post = session.query(Post).filter(Post.id == post_id).first()
        
        if post and (post.author_id == user.id or user.is_admin()):
            session.delete(post)
            session.commit()
            
            await query.edit_message_text(f"🗑️ Пост #{post_id} удалён.")
    finally:
        session.close()
