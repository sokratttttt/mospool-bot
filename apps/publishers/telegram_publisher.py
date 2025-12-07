"""
Telegram Publisher - публикация в Telegram каналы.
Использует python-telegram-bot библиотеку.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .base import BasePublisher

logger = logging.getLogger(__name__)


class TelegramPublisher(BasePublisher):
    """
    Публикатор для Telegram.
    
    Использование:
        publisher = TelegramPublisher(token="BOT_TOKEN", channel_id="@channel_name")
        result = publisher.publish("Текст поста", image_path="/path/to/image.jpg")
    """
    
    platform_name = "telegram"
    
    def __init__(self, token: str, channel_id: str):
        super().__init__(token, channel_id)
        self._bot = None
    
    def _get_bot(self):
        """Lazy initialization of Telegram Bot"""
        if self._bot is None:
            try:
                from telegram import Bot
                self._bot = Bot(token=self.token)
            except ImportError:
                raise ImportError("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return self._bot
    
    async def _publish_async(
        self, 
        text: str, 
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Асинхронная публикация"""
        from telegram.constants import ParseMode
        
        bot = self._get_bot()
        formatted_text = self.format_text(text)
        
        try:
            if image_path and Path(image_path).exists():
                with open(image_path, 'rb') as photo:
                    message = await bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo,
                        caption=formatted_text,
                        parse_mode=ParseMode.HTML
                    )
            else:
                message = await bot.send_message(
                    chat_id=self.channel_id,
                    text=formatted_text,
                    parse_mode=ParseMode.HTML
                )
            
            # Формируем URL поста
            channel_username = self.channel_id.replace('@', '')
            external_url = f"https://t.me/{channel_username}/{message.message_id}"
            
            logger.info(f"Telegram: Published message {message.message_id}")
            
            return {
                'success': True,
                'external_id': str(message.message_id),
                'external_url': external_url,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Telegram publish error: {e}")
            return {
                'success': False,
                'external_id': '',
                'external_url': '',
                'error': str(e)
            }
    
    def publish(
        self, 
        text: str, 
        image_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Синхронная обёртка для публикации.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self._publish_async(text, image_path)
            )
        finally:
            loop.close()
    
    async def _test_connection_async(self) -> bool:
        """Асинхронная проверка подключения"""
        try:
            bot = self._get_bot()
            me = await bot.get_me()
            logger.info(f"Telegram bot connected: @{me.username}")
            return True
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Проверка подключения к Telegram Bot API"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._test_connection_async())
        finally:
            loop.close()
    
    def format_text(self, text: str) -> str:
        """
        Форматирование текста для Telegram.
        Telegram поддерживает HTML разметку.
        """
        # Telegram имеет лимит 4096 символов для сообщений и 1024 для captions
        max_length = 1024  # Безопасный лимит для caption
        
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."
        
        return text


def get_telegram_publisher() -> Optional[TelegramPublisher]:
    """
    Получить настроенный TelegramPublisher из settings.
    
    Returns:
        TelegramPublisher или None если не настроен
    """
    from django.conf import settings
    
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    channel_id = getattr(settings, 'TELEGRAM_CHANNEL_ID', '')
    
    if token and channel_id:
        return TelegramPublisher(token, channel_id)
    return None
