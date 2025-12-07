"""
Content Generator - генератор контента для постов.
Использует DeepSeek AI + fallback на шаблоны.
"""
import random
import logging
from typing import Optional, Dict, Any
from django.utils import timezone

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Шаблонный движок для генерации постов.
    Используется как fallback когда ИИ недоступен.
    """
    
    # Шаблоны для разных категорий
    TEMPLATES = {
        'project': [
            """🏊 Новый проект завершён!

{description}

📐 Размер: {size}
✨ Тип: {pool_type}
🎯 Особенности: {features}

Хотите такой же? Напишите нам! 📱

{hashtags}""",
            
            """💎 Мы создали ещё один бассейн мечты!

{description}

Параметры:
• Тип: {pool_type}
• Размеры: {size}
• Фишки: {features}

📍 {location}

{hashtags}""",
            
            """🌊 Свежий проект от нашей команды!

{pool_type} бассейн {size} — это не просто вода, это стиль жизни!

{features}

Готовы обсудить ваш проект? 🤝

{hashtags}""",
        ],
        
        'tip': [
            """💡 Совет дня: {title}

{content}

Сохраняйте себе! 📌

{hashtags}""",
            
            """🔧 Полезная информация для владельцев бассейнов

{title}

{content}

Делитесь с друзьями! 👆

{hashtags}""",
        ],
        
        'promo': [
            """🎁 АКЦИЯ! {title}

{content}

⏰ Предложение ограничено!
📞 Звоните прямо сейчас!

{hashtags}""",
            
            """🔥 СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ

{title}

{content}

Не упустите шанс! 💪

{hashtags}""",
        ],
        
        'case': [
            """📸 История успеха: {title}

{content}

Спасибо за доверие! 🙏

{hashtags}""",
        ],
        
        'edu': [
            """📚 Полезно знать: {title}

{content}

Подписывайтесь, чтобы не пропустить! 🔔

{hashtags}""",
        ],
        
        'news': [
            """📰 Новости компании!

{title}

{content}

{hashtags}""",
        ],
    }
    
    # Наборы хештегов по категориям
    HASHTAGS = {
        'project': [
            '#бассейн', '#строительствобассейнов', '#бассейнподключ',
            '#бассейнмечты', '#бетонныйбассейн', '#композитныйбассейн',
            '#бассейннадаче', '#ландшафтныйдизайн', '#загородныйдом',
        ],
        'tip': [
            '#уходзабассейном', '#бассейн', '#советы', '#лайфхак',
            '#полезныесоветы', '#бассейнуход', '#чистаявода',
        ],
        'promo': [
            '#акция', '#скидка', '#бассейн', '#специальноепредложение',
            '#выгодно', '#бассейнподключ',
        ],
        'case': [
            '#кейс', '#бассейн', '#отзыв', '#довольныйклиент',
            '#строительствобассейнов',
        ],
        'edu': [
            '#образование', '#бассейн', '#полезнознать', '#интересныефакты',
        ],
        'news': [
            '#новости', '#бассейн', '#компания',
        ],
    }
    
    def generate(
        self, 
        category: str, 
        data: Dict[str, Any],
        hashtag_count: int = 5
    ) -> str:
        """
        Генерация поста из шаблона.
        
        Args:
            category: Категория поста (project, tip, promo и т.д.)
            data: Данные для подстановки в шаблон
            hashtag_count: Количество хештегов
            
        Returns:
            Готовый текст поста
        """
        templates = self.TEMPLATES.get(category, self.TEMPLATES['project'])
        template = random.choice(templates)
        
        # Подготавливаем хештеги
        category_hashtags = self.HASHTAGS.get(category, self.HASHTAGS['project'])
        selected_hashtags = random.sample(
            category_hashtags, 
            min(hashtag_count, len(category_hashtags))
        )
        data['hashtags'] = ' '.join(selected_hashtags)
        
        # Заполняем пустые поля дефолтными значениями
        defaults = {
            'title': 'Новый пост',
            'description': '',
            'content': '',
            'pool_type': 'бассейн',
            'size': '',
            'features': '',
            'location': 'Москва и МО',
        }
        
        for key, default_value in defaults.items():
            if key not in data or not data[key]:
                data[key] = default_value
        
        try:
            result = template.format(**data)
            # Убираем лишние пустые строки
            lines = result.split('\n')
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                is_empty = not line.strip()
                if not (is_empty and prev_empty):
                    cleaned_lines.append(line)
                prev_empty = is_empty
            return '\n'.join(cleaned_lines)
        except KeyError as e:
            logger.error(f"Template key error: {e}")
            return template


class ContentGenerator:
    """
    Генератор контента с использованием ИИ и шаблонов.
    """
    
    def __init__(self):
        self.template_engine = TemplateEngine()
        self._ai_client = None
    
    @property
    def ai_client(self):
        """Lazy load AI client"""
        if self._ai_client is None:
            try:
                from apps.ai_generator.mistral_client import get_mistral_client
                self._ai_client = get_mistral_client()
            except Exception as e:
                logger.warning(f"Could not initialize AI client: {e}")
                self._ai_client = None
        return self._ai_client
    
    def generate_post_content(
        self,
        category: str,
        data: Dict[str, Any],
        use_ai: bool = True
    ) -> str:
        """
        Генерация контента поста.
        
        Args:
            category: Категория поста
            data: Данные для генерации
            use_ai: Использовать ли ИИ (если доступен)
            
        Returns:
            Текст поста
        """
        # Попробуем использовать ИИ
        if use_ai and self.ai_client:
            try:
                ai_result = self.ai_client.generate_pool_post(
                    pool_type=data.get('pool_type', 'бассейн'),
                    size=data.get('size', ''),
                    features=data.get('features', ''),
                    category=category
                )
                if ai_result:
                    logger.info("Generated content using DeepSeek AI")
                    return ai_result
            except Exception as e:
                logger.warning(f"AI generation failed, using templates: {e}")
        
        # Fallback на шаблоны
        logger.info("Generating content using templates")
        return self.template_engine.generate(category, data)
    
    def create_post_from_project(self, project) -> 'Post':
        """
        Создание поста из данных проекта.
        
        Args:
            project: Экземпляр ProjectData
            
        Returns:
            Созданный Post
        """
        from apps.posts.models import Post, PostCategory
        
        # Подготавливаем данные
        data = {
            'title': project.title,
            'description': project.description or project.title,
            'pool_type': project.get_pool_type_display(),
            'size': project.size,
            'features': project.features,
            'location': project.location,
        }
        
        # Генерируем контент
        content = self.generate_post_content('project', data)
        
        # Получаем или создаём категорию
        category, _ = PostCategory.objects.get_or_create(
            slug='project',
            defaults={'name': '🏊 Новый проект'}
        )
        
        # Создаём пост
        post = Post.objects.create(
            title=f"Проект: {project.title}",
            content=content,
            category=category,
            status='pending',
            ai_generated=bool(self.ai_client),
            image=project.main_image if project.main_image else None,
        )
        
        logger.info(f"Created post {post.id} from project {project.id}")
        return post
    
    def generate_tips_batch(self, count: int = 5) -> list:
        """
        Генерация пакета советов.
        
        Args:
            count: Количество советов
            
        Returns:
            Список текстов советов
        """
        tips_topics = [
            ("Чистка фильтра", "Регулярно проверяйте и чистите фильтр бассейна. Рекомендуется делать это каждые 1-2 недели."),
            ("Проверка pH", "Оптимальный уровень pH воды — 7.2-7.6. Проверяйте минимум 2 раза в неделю."),
            ("Зимняя консервация", "Перед зимой слейте воду ниже форсунок и добавьте зимнее средство."),
            ("Обратная промывка", "Делайте обратную промывку фильтра когда давление повышается на 8-10 PSI."),
            ("Уровень хлора", "Поддерживайте уровень хлора 1-3 ppm для безопасного купания."),
            ("Чистка скиммера", "Очищайте корзину скиммера каждые 3-4 дня."),
            ("Проверка насоса", "Регулярно осматривайте насос на предмет утечек и шумов."),
        ]
        
        results = []
        for title, content in random.sample(tips_topics, min(count, len(tips_topics))):
            data = {'title': title, 'content': content}
            post_text = self.generate_post_content('tip', data)
            results.append(post_text)
        
        return results
