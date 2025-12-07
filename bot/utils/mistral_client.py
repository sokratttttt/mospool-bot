"""
MOS-POOL Bot - Mistral AI клиент
"""
import logging
from typing import Optional
from openai import OpenAI
from config import MISTRAL_API_KEY, MISTRAL_API_BASE, MISTRAL_MODEL

logger = logging.getLogger(__name__)


class MistralClient:
    """Клиент для Mistral AI"""
    
    def __init__(self):
        self.client = None
        if MISTRAL_API_KEY:
            self.client = OpenAI(
                api_key=MISTRAL_API_KEY,
                base_url=MISTRAL_API_BASE
            )
    
    def is_configured(self) -> bool:
        """Проверка, настроен ли API"""
        return self.client is not None
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Optional[str]:
        """Генерация текста"""
        if not self.is_configured():
            logger.warning("Mistral API not configured")
            return None
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Mistral API error: {e}")
            return None
    
    def generate_post(
        self,
        post_type: str,
        pool_type: str = None,
        size: str = None,
        features: str = None,
        **kwargs
    ) -> Optional[str]:
        """Генерация поста о бассейне"""
        
        system_prompt = """Ты - SMM-специалист компании MOS-POOL по строительству бассейнов.
Твоя задача - создавать привлекательные посты для социальных сетей.
Правила:
- Используй эмодзи для визуального оформления
- Пиши на русском языке
- Текст должен быть 100-300 символов (без хештегов)
- В конце добавь 3-5 релевантных хештегов
- Тон: профессиональный, но дружелюбный"""

        prompts = {
            "project": f"""Создай пост о завершённом проекте бассейна.
Тип: {pool_type or 'бетонный'}
Размер: {size or '6x3 м'}
Особенности: {features or 'современный дизайн'}""",

            "tip": f"""Создай полезный совет по уходу за бассейном.
Тема: {kwargs.get('topic', 'Чистка фильтра')}""",

            "promo": f"""Создай рекламный пост о скидке/акции.
Тип бассейна: {pool_type or 'любой'}
Акция: {kwargs.get('promo_text', 'Скидка 10% на строительство')}""",

            "case": f"""Создай пост-кейс о работе с клиентом.
Проект: {pool_type or 'бассейн под ключ'}
Результат: {kwargs.get('result', 'Довольный клиент')}""",
        }
        
        prompt = prompts.get(post_type, prompts["project"])
        return self.generate(prompt, system_prompt)
    
    def improve_text(self, text: str) -> Optional[str]:
        """Улучшение текста"""
        system_prompt = """Ты - редактор SMM-контента.
Улучши текст: сделай его более привлекательным, добавь эмодзи если нужно.
Сохрани исходный смысл. Ответь только улучшенным текстом."""

        prompt = f"Улучши этот пост:\n\n{text}"
        return self.generate(prompt, system_prompt, max_tokens=400)
    
    def generate_hashtags(self, text: str, count: int = 5) -> Optional[str]:
        """Генерация хештегов"""
        prompt = f"""Создай {count} хештегов для этого поста о бассейнах.
Ответь только хештегами через пробел.

Текст: {text}"""
        
        result = self.generate(prompt, max_tokens=100, temperature=0.5)
        return result


# Singleton
_client = None

def get_mistral_client() -> MistralClient:
    """Получить экземпляр Mistral клиента"""
    global _client
    if _client is None:
        _client = MistralClient()
    return _client
