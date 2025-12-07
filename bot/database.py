"""
MOS-POOL Bot - Модели базы данных
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import DATABASE_URL

# База
engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class User(Base):
    """Пользователь бота"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    role = Column(String(20), default="viewer")  # admin, editor, viewer
    status = Column(String(20), default="pending")  # pending, active, blocked
    position = Column(String(100))  # Должность
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    posts = relationship("Post", back_populates="author")
    logs = relationship("Log", back_populates="user")
    
    def is_admin(self) -> bool:
        return self.role == "admin"
    
    def is_editor(self) -> bool:
        return self.role in ("admin", "editor")
    
    def is_active(self) -> bool:
        return self.status == "active"
    
    def can_publish(self) -> bool:
        return self.role == "admin"
    
    def can_create_posts(self) -> bool:
        return self.role in ("admin", "editor") and self.is_active()


class Post(Base):
    """Пост для публикации"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    content = Column(Text, nullable=False)
    media_urls = Column(JSON, default=list)  # Список путей к медиафайлам
    
    status = Column(String(20), default="draft")  # draft, pending, approved, published, rejected
    rejection_reason = Column(Text)
    
    author_id = Column(Integer, ForeignKey("users.id"))
    approved_by_id = Column(Integer, ForeignKey("users.id"))
    
    channels = Column(JSON, default=list)  # ["telegram", "vk"]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_for = Column(DateTime)
    published_at = Column(DateTime)
    
    ai_generated = Column(Boolean, default=False)
    template_id = Column(Integer, ForeignKey("templates.id"))
    
    # Связи
    author = relationship("User", foreign_keys=[author_id], back_populates="posts")
    publications = relationship("Publication", back_populates="post")
    template = relationship("Template")
    
    def is_draft(self) -> bool:
        return self.status == "draft"
    
    def is_pending(self) -> bool:
        return self.status == "pending"
    
    def is_approved(self) -> bool:
        return self.status == "approved"
    
    def is_published(self) -> bool:
        return self.status == "published"


class Publication(Base):
    """Запись о публикации"""
    __tablename__ = "publications"
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    
    channel_type = Column(String(20))  # telegram, vk
    channel_id = Column(String(100))
    
    status = Column(String(20), default="pending")  # pending, success, failed
    external_id = Column(String(100))  # ID сообщения в канале
    external_url = Column(String(500))
    error_message = Column(Text)
    
    published_at = Column(DateTime, default=datetime.utcnow)
    stats = Column(JSON, default=dict)  # Статистика: views, likes и т.д.
    
    # Связи
    post = relationship("Post", back_populates="publications")


class Template(Base):
    """Шаблон поста"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50))  # project, tip, promo, case
    
    ai_prompt = Column(Text)  # Промпт для AI генерации
    variables = Column(JSON, default=list)  # Список переменных: ["pool_type", "size"]
    
    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class Log(Base):
    """Лог действий"""
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="logs")


class ScheduledPost(Base):
    """Запланированная публикация"""
    __tablename__ = "scheduled_posts"
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    channels = Column(JSON, default=list)
    
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# Создание таблиц
def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(engine)


def get_session():
    """Получить сессию БД"""
    return Session()


# Вспомогательные функции
def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """Получить пользователя по Telegram ID"""
    session = get_session()
    try:
        return session.query(User).filter(User.telegram_id == telegram_id).first()
    finally:
        session.close()


def create_user(telegram_id: int, username: str = None, full_name: str = None) -> User:
    """Создать нового пользователя"""
    session = get_session()
    try:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            status="pending"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def get_pending_users() -> List[User]:
    """Получить пользователей, ожидающих подтверждения"""
    session = get_session()
    try:
        return session.query(User).filter(User.status == "pending").all()
    finally:
        session.close()


def approve_user(user_id: int, role: str = "editor") -> bool:
    """Подтвердить пользователя"""
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.status = "active"
            user.role = role
            session.commit()
            return True
        return False
    finally:
        session.close()


def get_user_posts(user_id: int, status: str = None) -> List[Post]:
    """Получить посты пользователя"""
    session = get_session()
    try:
        query = session.query(Post).filter(Post.author_id == user_id)
        if status:
            query = query.filter(Post.status == status)
        return query.order_by(Post.created_at.desc()).all()
    finally:
        session.close()


def get_pending_posts() -> List[Post]:
    """Получить посты на модерацию"""
    session = get_session()
    try:
        return session.query(Post).filter(Post.status == "pending").order_by(Post.created_at.desc()).all()
    finally:
        session.close()


def get_scheduled_posts() -> List[Post]:
    """Получить запланированные посты"""
    session = get_session()
    try:
        return session.query(Post).filter(
            Post.status == "approved",
            Post.scheduled_for != None,
            Post.published_at == None
        ).order_by(Post.scheduled_for).all()
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    print("✅ Database initialized!")
