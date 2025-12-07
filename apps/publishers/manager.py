"""
Publisher Manager - централизованное управление публикациями.
"""
import logging
from typing import Dict, List, Any, Optional

from .telegram_publisher import TelegramPublisher
from .vk_publisher import VKPublisher
from .base import BasePublisher

logger = logging.getLogger(__name__)


class PublisherManager:
    """
    Менеджер для управления всеми публикаторами.
    
    Использование:
        manager = PublisherManager()
        manager.add_platform('telegram', TelegramPublisher(token, channel))
        results = manager.publish_to_all("Текст поста")
    """
    
    def __init__(self):
        self._publishers: Dict[str, BasePublisher] = {}
    
    def add_platform(self, name: str, publisher: BasePublisher):
        """Добавить платформу для публикации"""
        self._publishers[name] = publisher
        logger.info(f"Added publisher: {name}")
    
    def remove_platform(self, name: str):
        """Удалить платформу"""
        if name in self._publishers:
            del self._publishers[name]
            logger.info(f"Removed publisher: {name}")
    
    def get_publisher(self, name: str) -> Optional[BasePublisher]:
        """Получить публикатор по имени"""
        return self._publishers.get(name)
    
    def list_platforms(self) -> List[str]:
        """Список доступных платформ"""
        return list(self._publishers.keys())
    
    def publish_to_platform(
        self, 
        platform: str, 
        text: str, 
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Публикация на конкретную платформу.
        
        Returns:
            Результат публикации
        """
        publisher = self._publishers.get(platform)
        if not publisher:
            return {
                'success': False,
                'platform': platform,
                'error': f"Platform '{platform}' not configured"
            }
        
        result = publisher.publish(text, image_path)
        result['platform'] = platform
        return result
    
    def publish_to_all(
        self, 
        text: str, 
        image_path: Optional[str] = None,
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Публикация на все или выбранные платформы.
        
        Args:
            text: Текст поста
            image_path: Путь к изображению
            platforms: Список платформ (если None - все)
            
        Returns:
            Список результатов для каждой платформы
        """
        results = []
        target_platforms = platforms or self.list_platforms()
        
        for platform in target_platforms:
            result = self.publish_to_platform(platform, text, image_path)
            results.append(result)
        
        return results
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        Проверка подключения ко всем платформам.
        
        Returns:
            Dict с результатами для каждой платформы
        """
        results = {}
        for name, publisher in self._publishers.items():
            try:
                results[name] = publisher.test_connection()
            except Exception as e:
                logger.error(f"Connection test failed for {name}: {e}")
                results[name] = False
        return results
    
    @classmethod
    def from_settings(cls) -> 'PublisherManager':
        """
        Создать менеджер из Django settings.
        
        Returns:
            Настроенный PublisherManager
        """
        from django.conf import settings
        
        manager = cls()
        
        # Telegram
        tg_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        tg_channel = getattr(settings, 'TELEGRAM_CHANNEL_ID', '')
        if tg_token and tg_channel:
            manager.add_platform('telegram', TelegramPublisher(tg_token, tg_channel))
        
        # VK
        vk_token = getattr(settings, 'VK_ACCESS_TOKEN', '')
        vk_group = getattr(settings, 'VK_GROUP_ID', '')
        if vk_token and vk_group:
            manager.add_platform('vk', VKPublisher(vk_token, vk_group))
        
        return manager
    
    @classmethod
    def from_database(cls) -> 'PublisherManager':
        """
        Создать менеджер из базы данных (Platform модели).
        
        Returns:
            Настроенный PublisherManager
        """
        from apps.posts.models import Platform
        
        manager = cls()
        
        for platform in Platform.objects.filter(is_active=True):
            if platform.name == 'telegram':
                publisher = TelegramPublisher(platform.api_token, platform.channel_id)
            elif platform.name == 'vk':
                publisher = VKPublisher(platform.api_token, platform.channel_id)
            else:
                continue
            
            manager.add_platform(platform.name, publisher)
        
        return manager


def publish_post(post) -> List[Dict[str, Any]]:
    """
    Публикация поста на все его платформы.
    
    Args:
        post: Post instance
        
    Returns:
        Список результатов публикации
    """
    from apps.posts.models import Publication
    
    results = []
    
    for platform in post.platforms.filter(is_active=True):
        # Создаём публикатор
        if platform.name == 'telegram':
            publisher = TelegramPublisher(platform.api_token, platform.channel_id)
        elif platform.name == 'vk':
            publisher = VKPublisher(platform.api_token, platform.channel_id)
        else:
            continue
        
        # Получаем текст для платформы
        text = post.get_content_for_platform(platform.name)
        
        # Получаем путь к изображению
        image_path = None
        if post.image:
            image_path = post.image.path
        
        # Публикуем
        result = publisher.publish(text, image_path)
        
        # Сохраняем результат в БД
        Publication.objects.create(
            post=post,
            platform=platform,
            status='success' if result['success'] else 'failed',
            external_id=result.get('external_id', ''),
            external_url=result.get('external_url', ''),
            error_message=result.get('error', '')
        )
        
        result['platform'] = platform.name
        results.append(result)
    
    # Обновляем статус поста
    if all(r['success'] for r in results):
        post.mark_as_published()
    elif any(r['success'] for r in results):
        post.status = 'published'  # Частично опубликован
        post.save()
    else:
        post.status = 'failed'
        post.save()
    
    return results
