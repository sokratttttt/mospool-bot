"""
Base Publisher - абстрактный базовый класс для публикаторов.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BasePublisher(ABC):
    """
    Базовый класс для всех публикаторов.
    """
    
    platform_name: str = "base"
    
    def __init__(self, token: str, channel_id: str):
        self.token = token
        self.channel_id = channel_id
        self._validate_config()
    
    def _validate_config(self):
        """Проверка конфигурации"""
        if not self.token:
            raise ValueError(f"{self.platform_name}: API token is required")
        if not self.channel_id:
            raise ValueError(f"{self.platform_name}: Channel/Group ID is required")
    
    @abstractmethod
    def publish(
        self, 
        text: str, 
        image_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Публикация поста.
        
        Args:
            text: Текст поста
            image_path: Путь к изображению (опционально)
            
        Returns:
            Dict с результатом публикации:
            - success: bool
            - external_id: str (ID поста в соцсети)
            - external_url: str (URL поста)
            - error: str (сообщение об ошибке, если есть)
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Проверка подключения к API.
        
        Returns:
            True если подключение успешно
        """
        pass
    
    def format_text(self, text: str) -> str:
        """
        Форматирование текста под платформу.
        Переопределяется в наследниках если нужно.
        """
        return text
