"""
VK Publisher - публикация в VK и Max (Mail.ru).
Max использует VK API, поэтому один публикатор работает для обоих.
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .base import BasePublisher

logger = logging.getLogger(__name__)


class VKPublisher(BasePublisher):
    """
    Публикатор для VK и Max.
    
    Использование:
        publisher = VKPublisher(token="VK_TOKEN", channel_id="123456")
        result = publisher.publish("Текст поста", image_path="/path/to/image.jpg")
    
    Получение токена:
        1. Создайте Standalone-приложение: https://vk.com/apps?act=manage
        2. Получите access_token с правами: wall, photos, groups
        3. Implicit Flow: https://oauth.vk.com/authorize?client_id=APP_ID&scope=wall,photos,groups&response_type=token
    """
    
    platform_name = "vk"
    
    def __init__(self, token: str, channel_id: str):
        super().__init__(token, channel_id)
        self._vk_session = None
        self._vk_api = None
    
    def _get_vk(self):
        """Lazy initialization of VK API"""
        if self._vk_session is None:
            try:
                import vk_api
                self._vk_session = vk_api.VkApi(token=self.token)
                self._vk_api = self._vk_session.get_api()
            except ImportError:
                raise ImportError("vk-api not installed. Run: pip install vk-api")
        return self._vk_session, self._vk_api
    
    def _upload_photo(self, image_path: str) -> Optional[str]:
        """
        Загрузка фото на стену группы.
        
        Returns:
            Attachment string (photo123_456) или None
        """
        try:
            import vk_api
            
            vk_session, _ = self._get_vk()
            upload = vk_api.VkUpload(vk_session)
            
            # Загружаем фото на стену группы
            photos = upload.photo_wall(
                photos=image_path,
                group_id=int(self.channel_id)
            )
            
            if photos:
                photo = photos[0]
                attachment = f"photo{photo['owner_id']}_{photo['id']}"
                logger.info(f"VK: Uploaded photo {attachment}")
                return attachment
            
        except Exception as e:
            logger.error(f"VK photo upload error: {e}")
        
        return None
    
    def publish(
        self, 
        text: str, 
        image_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Публикация поста в VK группу.
        """
        try:
            _, api = self._get_vk()
            formatted_text = self.format_text(text)
            
            # Подготавливаем attachments
            attachments = []
            if image_path and Path(image_path).exists():
                photo_attachment = self._upload_photo(image_path)
                if photo_attachment:
                    attachments.append(photo_attachment)
            
            # Публикуем пост
            # owner_id для группы должен быть отрицательным
            owner_id = f"-{self.channel_id}" if not self.channel_id.startswith('-') else self.channel_id
            
            post_result = api.wall.post(
                owner_id=owner_id,
                message=formatted_text,
                attachments=','.join(attachments) if attachments else None,
                from_group=1  # Публикация от имени группы
            )
            
            post_id = post_result.get('post_id')
            external_url = f"https://vk.com/wall{owner_id}_{post_id}"
            
            logger.info(f"VK: Published post {post_id}")
            
            return {
                'success': True,
                'external_id': str(post_id),
                'external_url': external_url,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"VK publish error: {e}")
            return {
                'success': False,
                'external_id': '',
                'external_url': '',
                'error': str(e)
            }
    
    def test_connection(self) -> bool:
        """Проверка подключения к VK API"""
        try:
            _, api = self._get_vk()
            
            # Проверяем токен
            user = api.users.get()
            if user:
                logger.info(f"VK connected as user ID: {user[0]['id']}")
            
            # Проверяем доступ к группе
            owner_id = f"-{self.channel_id}" if not self.channel_id.startswith('-') else self.channel_id
            groups = api.groups.getById(group_id=self.channel_id.lstrip('-'))
            if groups:
                logger.info(f"VK group access confirmed: {groups[0]['name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"VK connection test failed: {e}")
            return False
    
    def format_text(self, text: str) -> str:
        """
        Форматирование текста для VK.
        VK поддерживает до 15895 символов в посте.
        """
        max_length = 15000  # Безопасный лимит
        
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."
        
        return text


def get_vk_publisher() -> Optional[VKPublisher]:
    """
    Получить настроенный VKPublisher из settings.
    
    Returns:
        VKPublisher или None если не настроен
    """
    from django.conf import settings
    
    token = getattr(settings, 'VK_ACCESS_TOKEN', '')
    group_id = getattr(settings, 'VK_GROUP_ID', '')
    
    if token and group_id:
        return VKPublisher(token, group_id)
    return None
