"""
MOS-POOL Telegram Bot - Конфигурация
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Пути
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
TELEGRAM_TEST_CHANNEL_ID = os.getenv("TELEGRAM_TEST_CHANNEL_ID", "")

# VK
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN", "")
VK_GROUP_ID = os.getenv("VK_GROUP_ID", "")

# Mistral AI
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_API_BASE = "https://api.mistral.ai/v1"
MISTRAL_MODEL = "mistral-small-latest"

# Admin
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/bot.db")

# Лимиты
MAX_POSTS_PER_DAY = 10
MIN_POST_LENGTH = 20
MAX_POST_LENGTH = 4096
MAX_MEDIA_FILES = 10

# Роли
class Role:
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

# Статусы постов
class PostStatus:
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"

# Статусы пользователей
class UserStatus:
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
