"""
MOS-POOL Bot - Клавиатуры
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


# ============ REPLY KEYBOARDS ============

def main_menu_keyboard(is_admin: bool = False, is_editor: bool = False):
    """Главное меню"""
    buttons = [
        ["📝 Создать пост", "🤖 AI генерация"],
        ["📋 Мои черновики", "📅 Очередь"],
    ]
    
    if is_editor:
        buttons.append(["📊 Статистика", "📁 Шаблоны"])
    
    if is_admin:
        buttons.append(["👥 Пользователи", "⚙️ Настройки"])
    
    buttons.append(["❓ Помощь"])
    
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def cancel_keyboard():
    """Клавиатура отмены"""
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)


def back_keyboard():
    """Клавиатура назад"""
    return ReplyKeyboardMarkup([["⬅️ Назад", "❌ Отмена"]], resize_keyboard=True)


def confirm_keyboard():
    """Клавиатура подтверждения"""
    return ReplyKeyboardMarkup([["✅ Подтвердить", "❌ Отмена"]], resize_keyboard=True)


# ============ INLINE KEYBOARDS ============

def post_actions_keyboard(post_id: int, status: str, can_publish: bool = False):
    """Действия с постом"""
    buttons = []
    
    if status == "draft":
        buttons.append([
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"post_edit:{post_id}"),
            InlineKeyboardButton("📤 На проверку", callback_data=f"post_submit:{post_id}"),
        ])
        buttons.append([
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"post_delete:{post_id}"),
        ])
    
    elif status == "pending":
        if can_publish:
            buttons.append([
                InlineKeyboardButton("✅ Одобрить", callback_data=f"post_approve:{post_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"post_reject:{post_id}"),
            ])
        buttons.append([
            InlineKeyboardButton("👁️ Просмотр", callback_data=f"post_view:{post_id}"),
        ])
    
    elif status == "approved":
        buttons.append([
            InlineKeyboardButton("🚀 Опубликовать", callback_data=f"post_publish:{post_id}"),
            InlineKeyboardButton("📅 Запланировать", callback_data=f"post_schedule:{post_id}"),
        ])
    
    buttons.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="posts_list"),
    ])
    
    return InlineKeyboardMarkup(buttons)


def channels_keyboard(selected: list = None):
    """Выбор каналов для публикации"""
    selected = selected or []
    
    tg_check = "✅" if "telegram" in selected else "⬜"
    vk_check = "✅" if "vk" in selected else "⬜"
    
    buttons = [
        [
            InlineKeyboardButton(f"{tg_check} Telegram", callback_data="channel_toggle:telegram"),
            InlineKeyboardButton(f"{vk_check} VK/Max", callback_data="channel_toggle:vk"),
        ],
        [
            InlineKeyboardButton("✅ Готово", callback_data="channels_done"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def ai_options_keyboard():
    """Опции AI генерации"""
    buttons = [
        [
            InlineKeyboardButton("🏊 Новый проект", callback_data="ai_type:project"),
            InlineKeyboardButton("💡 Совет", callback_data="ai_type:tip"),
        ],
        [
            InlineKeyboardButton("🎁 Акция", callback_data="ai_type:promo"),
            InlineKeyboardButton("📸 Кейс", callback_data="ai_type:case"),
        ],
        [
            InlineKeyboardButton("✨ Улучшить текст", callback_data="ai_improve"),
            InlineKeyboardButton("#️⃣ Хештеги", callback_data="ai_hashtags"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def ai_result_keyboard(post_id: int = None):
    """Результат AI генерации"""
    buttons = [
        [
            InlineKeyboardButton("✅ Использовать", callback_data=f"ai_use:{post_id or 'new'}"),
            InlineKeyboardButton("🔄 Другой вариант", callback_data="ai_regenerate"),
        ],
        [
            InlineKeyboardButton("✏️ Редактировать", callback_data="ai_edit"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def schedule_keyboard():
    """Выбор времени публикации"""
    buttons = [
        [
            InlineKeyboardButton("🕐 Через 1 час", callback_data="schedule:1h"),
            InlineKeyboardButton("🕒 Через 3 часа", callback_data="schedule:3h"),
        ],
        [
            InlineKeyboardButton("📅 Завтра 10:00", callback_data="schedule:tomorrow"),
            InlineKeyboardButton("📅 Завтра 18:00", callback_data="schedule:tomorrow_evening"),
        ],
        [
            InlineKeyboardButton("🗓️ Выбрать дату", callback_data="schedule:custom"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def user_management_keyboard(user_id: int, status: str, role: str):
    """Управление пользователем"""
    buttons = []
    
    if status == "pending":
        buttons.append([
            InlineKeyboardButton("✅ Одобрить (editor)", callback_data=f"user_approve:{user_id}:editor"),
            InlineKeyboardButton("✅ Одобрить (viewer)", callback_data=f"user_approve:{user_id}:viewer"),
        ])
        buttons.append([
            InlineKeyboardButton("❌ Отклонить", callback_data=f"user_reject:{user_id}"),
        ])
    elif status == "active":
        if role != "admin":
            buttons.append([
                InlineKeyboardButton("⬆️ Повысить", callback_data=f"user_promote:{user_id}"),
                InlineKeyboardButton("⬇️ Понизить", callback_data=f"user_demote:{user_id}"),
            ])
        buttons.append([
            InlineKeyboardButton("🚫 Заблокировать", callback_data=f"user_block:{user_id}"),
        ])
    elif status == "blocked":
        buttons.append([
            InlineKeyboardButton("🔓 Разблокировать", callback_data=f"user_unblock:{user_id}"),
        ])
    
    buttons.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="users_list"),
    ])
    
    return InlineKeyboardMarkup(buttons)


def posts_list_keyboard(posts: list, page: int = 0, per_page: int = 5):
    """Список постов с пагинацией"""
    buttons = []
    
    start = page * per_page
    end = start + per_page
    page_posts = posts[start:end]
    
    for post in page_posts:
        status_emoji = {
            "draft": "📝",
            "pending": "⏳",
            "approved": "✅",
            "published": "📤",
            "rejected": "❌",
        }.get(post.status, "📄")
        
        title = post.title or post.content[:30] + "..."
        buttons.append([
            InlineKeyboardButton(f"{status_emoji} {title}", callback_data=f"post_view:{post.id}")
        ])
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"posts_page:{page-1}"))
    if end < len(posts):
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"posts_page:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([
        InlineKeyboardButton("➕ Создать пост", callback_data="new_post"),
        InlineKeyboardButton("🏠 Меню", callback_data="main_menu"),
    ])
    
    return InlineKeyboardMarkup(buttons)


def confirmation_keyboard(action: str, item_id: int):
    """Подтверждение действия"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm:{action}:{item_id}"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel"),
        ]
    ])
