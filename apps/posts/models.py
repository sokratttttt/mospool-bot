"""
Database models for social media automation system.
Модели базы данных для системы автоматизации публикаций.
"""
from django.db import models
from django.utils import timezone


class Platform(models.Model):
    """
    Социальная платформа для публикации
    (Telegram, VK/Max)
    """
    PLATFORM_CHOICES = [
        ('telegram', 'Telegram'),
        ('vk', 'VK / Max'),
    ]
    
    name = models.CharField(
        max_length=50, 
        choices=PLATFORM_CHOICES,
        verbose_name='Платформа'
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name='Отображаемое имя'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    api_token = models.CharField(
        max_length=500,
        verbose_name='API Token',
        help_text='Токен для доступа к API платформы'
    )
    channel_id = models.CharField(
        max_length=100,
        verbose_name='ID канала/группы',
        help_text='ID канала Telegram или группы VK'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Платформа'
        verbose_name_plural = 'Платформы'
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"


class PostCategory(models.Model):
    """
    Категории постов
    """
    CATEGORY_TYPES = [
        ('project', '🏊 Новый проект'),
        ('tip', '💡 Полезный совет'),
        ('promo', '🎁 Акция/Скидка'),
        ('case', '📸 Кейс/Отзыв'),
        ('edu', '📚 Образовательный'),
        ('news', '📰 Новости компании'),
    ]
    
    slug = models.CharField(
        max_length=50, 
        choices=CATEGORY_TYPES,
        unique=True,
        verbose_name='Тип'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Название'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    default_hashtags = models.TextField(
        blank=True,
        verbose_name='Хештеги по умолчанию',
        help_text='Каждый хештег с новой строки'
    )
    
    class Meta:
        verbose_name = 'Категория постов'
        verbose_name_plural = 'Категории постов'
    
    def __str__(self):
        return self.name


class PostTemplate(models.Model):
    """
    Шаблоны постов для генерации контента.
    Используются как база для ИИ-генерации.
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Название шаблона'
    )
    category = models.ForeignKey(
        PostCategory,
        on_delete=models.CASCADE,
        related_name='templates',
        verbose_name='Категория'
    )
    template_text = models.TextField(
        verbose_name='Текст шаблона',
        help_text='Используйте {title}, {description}, {size}, {features}, {location} как плейсхолдеры'
    )
    ai_prompt = models.TextField(
        blank=True,
        verbose_name='Промпт для ИИ',
        help_text='Инструкция для DeepSeek при генерации текста'
    )
    hashtags = models.TextField(
        blank=True,
        verbose_name='Хештеги'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    
    class Meta:
        verbose_name = 'Шаблон поста'
        verbose_name_plural = 'Шаблоны постов'
    
    def __str__(self):
        return f"{self.name} ({self.category})"


class Post(models.Model):
    """
    Пост для публикации в социальных сетях
    """
    STATUS_CHOICES = [
        ('draft', '📝 Черновик'),
        ('pending', '⏳ На модерации'),
        ('approved', '✅ Одобрен'),
        ('scheduled', '📅 Запланирован'),
        ('publishing', '🔄 Публикуется'),
        ('published', '✔️ Опубликован'),
        ('failed', '❌ Ошибка'),
    ]
    
    title = models.CharField(
        max_length=200,
        verbose_name='Заголовок',
        help_text='Для внутреннего использования'
    )
    content = models.TextField(
        verbose_name='Текст поста'
    )
    content_telegram = models.TextField(
        blank=True,
        verbose_name='Текст для Telegram',
        help_text='Если пустой, используется основной текст'
    )
    content_vk = models.TextField(
        blank=True,
        verbose_name='Текст для VK',
        help_text='Если пустой, используется основной текст'
    )
    
    image = models.ImageField(
        upload_to='posts/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )
    
    category = models.ForeignKey(
        PostCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Категория'
    )
    template = models.ForeignKey(
        PostTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Использованный шаблон'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Статус'
    )
    
    platforms = models.ManyToManyField(
        Platform,
        blank=True,
        verbose_name='Платформы для публикации'
    )
    
    scheduled_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время публикации'
    )
    
    # AI generation metadata
    ai_generated = models.BooleanField(
        default=False,
        verbose_name='Сгенерирован ИИ'
    )
    ai_prompt_used = models.TextField(
        blank=True,
        verbose_name='Использованный промпт'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата публикации'
    )
    
    # Author tracking
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_posts',
        verbose_name='Создал'
    )
    
    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def get_content_for_platform(self, platform_name: str) -> str:
        """Получить текст поста для конкретной платформы"""
        if platform_name == 'telegram' and self.content_telegram:
            return self.content_telegram
        elif platform_name == 'vk' and self.content_vk:
            return self.content_vk
        return self.content
    
    def mark_as_published(self):
        """Отметить пост как опубликованный"""
        self.status = 'published'
        self.published_at = timezone.now()
        self.save()


class Publication(models.Model):
    """
    Лог публикаций - записи о каждой публикации поста
    """
    STATUS_CHOICES = [
        ('success', '✅ Успешно'),
        ('failed', '❌ Ошибка'),
        ('pending', '⏳ В процессе'),
    ]
    
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='publications',
        verbose_name='Пост'
    )
    platform = models.ForeignKey(
        Platform,
        on_delete=models.CASCADE,
        verbose_name='Платформа'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='ID в соцсети',
        help_text='ID сообщения в Telegram или поста в VK'
    )
    external_url = models.URLField(
        blank=True,
        verbose_name='Ссылка на пост'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    published_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время публикации'
    )
    
    class Meta:
        verbose_name = 'Публикация'
        verbose_name_plural = 'Публикации'
        ordering = ['-published_at']
    
    def __str__(self):
        return f"{self.post.title} → {self.platform.name} ({self.get_status_display()})"


class ProjectData(models.Model):
    """
    Данные о проектах бассейнов для генерации контента.
    Может заполняться вручную или парситься с сайта.
    """
    POOL_TYPES = [
        ('concrete', 'Бетонный'),
        ('composite', 'Композитный'),
        ('frame', 'Каркасный'),
        ('inflatable', 'Надувной'),
        ('indoor', 'Крытый'),
        ('outdoor', 'Открытый'),
    ]
    
    title = models.CharField(
        max_length=200,
        verbose_name='Название проекта'
    )
    pool_type = models.CharField(
        max_length=50,
        choices=POOL_TYPES,
        verbose_name='Тип бассейна'
    )
    size = models.CharField(
        max_length=50,
        verbose_name='Размеры',
        help_text='Например: 8x4 м, глубина 1.5-2 м'
    )
    features = models.TextField(
        blank=True,
        verbose_name='Особенности',
        help_text='Противоток, подсветка, джакузи и т.д.'
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Локация',
        help_text='Город или район'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание проекта'
    )
    
    images = models.JSONField(
        default=list,
        verbose_name='Изображения',
        help_text='Список URL изображений'
    )
    main_image = models.ImageField(
        upload_to='projects/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Главное изображение'
    )
    
    source_url = models.URLField(
        blank=True,
        verbose_name='Источник',
        help_text='URL страницы проекта на сайте'
    )
    
    is_published = models.BooleanField(
        default=False,
        verbose_name='Пост создан',
        help_text='Был ли уже создан пост по этому проекту'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Проект бассейна'
        verbose_name_plural = 'Проекты бассейнов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_pool_type_display()})"
    
    def get_features_list(self) -> list:
        """Получить список особенностей"""
        if not self.features:
            return []
        return [f.strip() for f in self.features.split(',')]


class ScheduleSlot(models.Model):
    """
    Расписание публикаций - слоты времени для автопубликации
    """
    DAYS_OF_WEEK = [
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
        (5, 'Суббота'),
        (6, 'Воскресенье'),
    ]
    
    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK,
        verbose_name='День недели'
    )
    time = models.TimeField(
        verbose_name='Время'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    platforms = models.ManyToManyField(
        Platform,
        verbose_name='Платформы'
    )
    preferred_category = models.ForeignKey(
        PostCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Предпочтительная категория'
    )
    
    class Meta:
        verbose_name = 'Слот расписания'
        verbose_name_plural = 'Расписание публикаций'
        ordering = ['day_of_week', 'time']
        unique_together = ['day_of_week', 'time']
    
    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.time.strftime('%H:%M')}"
