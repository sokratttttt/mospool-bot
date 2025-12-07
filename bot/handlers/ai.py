"""
MOS-POOL Bot - AI генерация контента
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import get_user_by_telegram_id, get_session, Post
from keyboards import ai_options_keyboard, ai_result_keyboard, cancel_keyboard, main_menu_keyboard
from utils.mistral_client import get_mistral_client
from config import PostStatus

logger = logging.getLogger(__name__)

# Состояния
AI_SELECT_TYPE, AI_INPUT_DATA, AI_RESULT = range(3)


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ai - AI генерация"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.can_create_posts():
        await update.message.reply_text("❌ У вас нет прав на создание постов.")
        return ConversationHandler.END
    
    client = get_mistral_client()
    if not client.is_configured():
        await update.message.reply_text(
            "⚠️ AI генерация не настроена.\n\n"
            "Добавьте MISTRAL_API_KEY в .env файл."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🤖 **AI генерация контента**\n\n"
        "Выберите тип поста:",
        reply_markup=ai_options_keyboard(),
        parse_mode="Markdown"
    )
    
    return AI_SELECT_TYPE


async def ai_select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор типа поста"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "cancel":
        await query.edit_message_text("❌ Генерация отменена.")
        return ConversationHandler.END
    
    if data.startswith("ai_type:"):
        post_type = data.split(":")[1]
        context.user_data["ai_type"] = post_type
        
        type_prompts = {
            "project": "🏊 Опишите проект:\nТип бассейна, размер, особенности",
            "tip": "💡 Введите тему совета:",
            "promo": "🎁 Опишите акцию:",
            "case": "📸 Опишите кейс:",
        }
        
        prompt = type_prompts.get(post_type, "Введите описание:")
        
        await query.edit_message_text(
            f"✏️ {prompt}\n\n"
            "Или отправьте /cancel для отмены"
        )
        
        return AI_INPUT_DATA
    
    elif data == "ai_improve":
        context.user_data["ai_mode"] = "improve"
        await query.edit_message_text(
            "✏️ Отправьте текст, который нужно улучшить:"
        )
        return AI_INPUT_DATA
    
    elif data == "ai_hashtags":
        context.user_data["ai_mode"] = "hashtags"
        await query.edit_message_text(
            "✏️ Отправьте текст для подбора хештегов:"
        )
        return AI_INPUT_DATA


async def ai_input_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение данных для генерации"""
    text = update.message.text
    
    if text.startswith("/"):
        if text == "/cancel":
            user = get_user_by_telegram_id(update.effective_user.id)
            await update.message.reply_text(
                "❌ Генерация отменена.",
                reply_markup=main_menu_keyboard(
                    is_admin=user.is_admin() if user else False,
                    is_editor=user.is_editor() if user else False
                )
            )
            return ConversationHandler.END
        return AI_INPUT_DATA
    
    context.user_data["ai_input"] = text
    
    await update.message.reply_text("⏳ Генерирую контент...")
    
    # Генерация
    client = get_mistral_client()
    result = None
    
    ai_type = context.user_data.get("ai_type")
    ai_mode = context.user_data.get("ai_mode")
    
    if ai_mode == "improve":
        result = client.improve_text(text)
    elif ai_mode == "hashtags":
        result = client.generate_hashtags(text)
    elif ai_type:
        # Парсим данные для генерации
        result = client.generate_post(
            post_type=ai_type,
            pool_type=text if ai_type == "project" else None,
            topic=text if ai_type == "tip" else None,
            promo_text=text if ai_type == "promo" else None,
        )
    
    if not result:
        await update.message.reply_text(
            "❌ Не удалось сгенерировать контент.\n"
            "Попробуйте ещё раз: /ai"
        )
        return ConversationHandler.END
    
    context.user_data["ai_result"] = result
    
    await update.message.reply_text(
        f"✨ **Результат:**\n\n{result}",
        reply_markup=ai_result_keyboard(),
        parse_mode="Markdown"
    )
    
    return AI_RESULT


async def ai_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка результата генерации"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    result = context.user_data.get("ai_result", "")
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if data.startswith("ai_use:"):
        # Создаём пост из результата
        session = get_session()
        try:
            post = Post(
                content=result,
                title=result[:50] + "..." if len(result) > 50 else result,
                author_id=user.id,
                status=PostStatus.DRAFT,
                channels=["telegram"],
                ai_generated=True
            )
            session.add(post)
            session.commit()
            post_id = post.id
        finally:
            session.close()
        
        context.user_data.clear()
        
        await query.edit_message_text(
            f"✅ Пост #{post_id} создан из AI-генерации!\n\n"
            f"Теперь вы можете:\n"
            f"• Отредактировать: /drafts\n"
            f"• Отправить на проверку\n"
            f"• Опубликовать"
        )
        return ConversationHandler.END
    
    elif data == "ai_regenerate":
        await query.edit_message_text("⏳ Генерирую новый вариант...")
        
        client = get_mistral_client()
        ai_type = context.user_data.get("ai_type", "project")
        ai_input = context.user_data.get("ai_input", "")
        
        result = client.generate_post(post_type=ai_type, pool_type=ai_input)
        
        if result:
            context.user_data["ai_result"] = result
            await query.edit_message_text(
                f"✨ **Новый вариант:**\n\n{result}",
                reply_markup=ai_result_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Ошибка генерации. Попробуйте /ai")
            return ConversationHandler.END
    
    elif data == "ai_edit":
        await query.edit_message_text(
            f"✏️ Текущий текст:\n\n{result}\n\n"
            "Отправьте отредактированную версию:"
        )
        context.user_data["ai_editing"] = True
        return AI_INPUT_DATA
    
    elif data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Генерация отменена.")
        return ConversationHandler.END


async def ai_quick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ai_quick - быстрая генерация"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.can_create_posts():
        await update.message.reply_text("❌ Нет доступа.")
        return
    
    args = " ".join(context.args) if context.args else "бассейн под ключ"
    
    await update.message.reply_text("⏳ Генерирую...")
    
    client = get_mistral_client()
    result = client.generate_post(post_type="project", pool_type=args)
    
    if result:
        await update.message.reply_text(
            f"✨ **Результат:**\n\n{result}",
            reply_markup=ai_result_keyboard(),
            parse_mode="Markdown"
        )
        context.user_data["ai_result"] = result
    else:
        await update.message.reply_text("❌ Ошибка генерации.")


async def ai_improve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ai_improve - улучшение текста"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.can_create_posts():
        await update.message.reply_text("❌ Нет доступа.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Использование: /ai_improve [текст]\n\n"
            "Или ответьте на сообщение с текстом командой /ai_improve"
        )
        return
    
    text = " ".join(context.args)
    
    await update.message.reply_text("⏳ Улучшаю текст...")
    
    client = get_mistral_client()
    result = client.improve_text(text)
    
    if result:
        await update.message.reply_text(
            f"✨ **Улучшенный текст:**\n\n{result}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Ошибка.")


async def ai_hashtags_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ai_hashtags - генерация хештегов"""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user or not user.can_create_posts():
        await update.message.reply_text("❌ Нет доступа.")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /ai_hashtags [текст поста]")
        return
    
    text = " ".join(context.args)
    
    client = get_mistral_client()
    result = client.generate_hashtags(text)
    
    if result:
        await update.message.reply_text(f"#️⃣ Хештеги:\n\n{result}")
    else:
        await update.message.reply_text("❌ Ошибка.")
