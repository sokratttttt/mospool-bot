"""
Mistral AI Client - Бесплатный ИИ для генерации контента.

Mistral AI использует OpenAI-совместимый API.
Бесплатный tier: https://console.mistral.ai/

Модели:
- mistral-small-latest (быстрая, экономичная)
- mistral-medium-latest (баланс)
- mistral-large-latest (лучшее качество)
"""
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class MistralClient:
    """
    Клиент для работы с Mistral AI API.
    Бесплатный ИИ с OpenAI-совместимым API.
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.MISTRAL_API_KEY
        self.base_url = base_url or settings.MISTRAL_API_BASE
        self._client = None
        
    def _get_client(self):
        """Lazy initialization of OpenAI-compatible client"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                raise
        return self._client
    
    def generate_text(
        self, 
        prompt: str, 
        system_prompt: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        model: str = "mistral-small-latest"
    ) -> Optional[str]:
        """
        Генерация текста с помощью Mistral AI.
        
        Args:
            prompt: Основной промпт для генерации
            system_prompt: Системный промпт (контекст)
            max_tokens: Максимальное количество токенов
            temperature: Креативность (0-1)
            model: Модель Mistral (mistral-small-latest, mistral-medium-latest, mistral-large-latest)
            
        Returns:
            Сгенерированный текст или None при ошибке
        """
        if not self.api_key:
            logger.warning("Mistral API key not configured, using template fallback")
            return None
            
        try:
            client = self._get_client()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            result = response.choices[0].message.content
            logger.info(f"Mistral generated {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Mistral API error: {e}")
            return None
    
    def generate_pool_post(
        self,
        pool_type: str,
        size: str,
        features: str,
        category: str = "project",
        tone: str = "профессиональный, но дружелюбный"
    ) -> Optional[str]:
        """
        Генерация поста о бассейне.
        
        Args:
            pool_type: Тип бассейна (бетонный, композитный и т.д.)
            size: Размеры бассейна
            features: Особенности (противоток, подсветка и т.д.)
            category: Категория поста (project, tip, promo и т.д.)
            tone: Тон текста
            
        Returns:
            Готовый текст поста
        """
        system_prompt = """Ты - SMM-специалист компании по строительству бассейнов. 
Твоя задача - создавать привлекательные посты для социальных сетей.
Используй эмодзи для визуального оформления.
Пиши на русском языке.
Добавляй 3-5 релевантных хештегов в конце поста.
Текст должен быть между 100-300 символами (без хештегов)."""

        prompts = {
            "project": f"""Создай пост для соцсетей о завершённом проекте бассейна.
Данные:
- Тип бассейна: {pool_type}
- Размер: {size}
- Особенности: {features}

Тон: {tone}
Формат: короткий, привлекательный пост с эмодзи и хештегами.""",

            "tip": f"""Создай пост с полезным советом по уходу за бассейном типа "{pool_type}".
Тон: {tone}
Формат: короткий совет с эмодзи и хештегами.""",

            "promo": f"""Создай рекламный пост о скидке/акции на строительство бассейнов.
Тип бассейна: {pool_type}
Тон: {tone}
Формат: продающий текст с призывом к действию, эмодзи и хештегами.""",
        }
        
        prompt = prompts.get(category, prompts["project"])
        return self.generate_text(prompt, system_prompt)
    
    def improve_text(self, original_text: str) -> Optional[str]:
        """
        Улучшение существующего текста поста.
        
        Args:
            original_text: Исходный текст
            
        Returns:
            Улучшенный текст
        """
        system_prompt = """Ты - редактор SMM-контента. 
Улучши текст: сделай его более привлекательным, добавь эмодзи если нужно,
проверь грамматику. Сохрани исходный смысл. Ответь только улучшенным текстом."""

        prompt = f"Улучши этот пост для соцсетей:\n\n{original_text}"
        return self.generate_text(prompt, system_prompt, max_tokens=400)
    
    def generate_hashtags(self, text: str, count: int = 5) -> list:
        """
        Генерация хештегов для текста.
        
        Args:
            text: Текст поста
            count: Количество хештегов
            
        Returns:
            Список хештегов
        """
        prompt = f"""Создай {count} релевантных хештегов для этого поста о бассейнах.
Ответь только хештегами через пробел, без объяснений.

Текст: {text}"""

        result = self.generate_text(prompt, max_tokens=100, temperature=0.5)
        if result:
            # Парсим хештеги
            hashtags = [tag.strip() for tag in result.split() if tag.startswith('#')]
            return hashtags[:count]
        return []


# Singleton instance
_mistral_client = None

def get_mistral_client() -> MistralClient:
    """Получить singleton экземпляр Mistral клиента"""
    global _mistral_client
    if _mistral_client is None:
        _mistral_client = MistralClient()
    return _mistral_client


# Алиас для обратной совместимости
def get_ai_client() -> MistralClient:
    """Получить AI клиент (Mistral)"""
    return get_mistral_client()
