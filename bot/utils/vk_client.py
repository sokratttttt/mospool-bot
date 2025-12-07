"""
MOS-POOL Bot - VK клиент
"""
import logging
from typing import Optional, List
import vk_api
from config import VK_ACCESS_TOKEN, VK_GROUP_ID

logger = logging.getLogger(__name__)


class VKClient:
    """Клиент для VK API"""
    
    def __init__(self):
        self.session = None
        self.api = None
        self.upload = None
        
        if VK_ACCESS_TOKEN and VK_GROUP_ID:
            try:
                self.session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
                self.api = self.session.get_api()
                self.upload = vk_api.VkUpload(self.session)
                self.group_id = int(VK_GROUP_ID)
            except Exception as e:
                logger.error(f"VK API init error: {e}")
    
    def is_configured(self) -> bool:
        """Проверка, настроен ли API"""
        return self.api is not None
    
    def test_connection(self) -> bool:
        """Тест подключения"""
        if not self.is_configured():
            return False
        
        try:
            info = self.api.groups.getById(group_id=self.group_id)
            return len(info) > 0
        except Exception as e:
            logger.error(f"VK connection test failed: {e}")
            return False
    
    def publish_post(
        self,
        text: str,
        photo_paths: List[str] = None,
        from_group: bool = True
    ) -> Optional[dict]:
        """
        Публикация поста в группу
        
        Returns:
            dict с post_id и url если успешно, None если ошибка
        """
        if not self.is_configured():
            logger.error("VK API not configured")
            return None
        
        try:
            attachments = []
            
            # Загрузка фото
            if photo_paths:
                for photo_path in photo_paths[:10]:  # Максимум 10 фото
                    try:
                        photos = self.upload.photo_wall(
                            photo_path,
                            group_id=self.group_id
                        )
                        if photos:
                            photo = photos[0]
                            attachments.append(f"photo{photo['owner_id']}_{photo['id']}")
                    except Exception as e:
                        logger.error(f"VK photo upload error: {e}")
            
            # Публикация
            response = self.api.wall.post(
                owner_id=-self.group_id,
                message=text,
                attachments=",".join(attachments) if attachments else None,
                from_group=1 if from_group else 0
            )
            
            post_id = response.get("post_id")
            if post_id:
                return {
                    "post_id": post_id,
                    "url": f"https://vk.com/wall-{self.group_id}_{post_id}"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"VK publish error: {e}")
            return None
    
    def delete_post(self, post_id: int) -> bool:
        """Удаление поста"""
        if not self.is_configured():
            return False
        
        try:
            self.api.wall.delete(
                owner_id=-self.group_id,
                post_id=post_id
            )
            return True
        except Exception as e:
            logger.error(f"VK delete error: {e}")
            return False
    
    def get_post_stats(self, post_id: int) -> Optional[dict]:
        """Получение статистики поста"""
        if not self.is_configured():
            return None
        
        try:
            posts = self.api.wall.getById(
                posts=f"-{self.group_id}_{post_id}"
            )
            if posts:
                post = posts[0]
                return {
                    "views": post.get("views", {}).get("count", 0),
                    "likes": post.get("likes", {}).get("count", 0),
                    "reposts": post.get("reposts", {}).get("count", 0),
                    "comments": post.get("comments", {}).get("count", 0),
                }
            return None
        except Exception as e:
            logger.error(f"VK stats error: {e}")
            return None


# Singleton
_client = None

def get_vk_client() -> VKClient:
    """Получить экземпляр VK клиента"""
    global _client
    if _client is None:
        _client = VKClient()
    return _client
