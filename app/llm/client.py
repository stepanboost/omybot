import httpx
import asyncio
from typing import Dict, Any, Optional
from loguru import logger
from ..config import config


class LLMClient:
    """Клиент для работы с OpenAI API"""
    
    def __init__(self):
        self.api_key = config.openai_api_key
        self.base_url = config.llm_base_url
        self.model_text = config.llm_model_text
        self.model_vision = config.llm_model_vision
        
    async def solve_text(self, text: str, subject_hint: str = None) -> Dict[str, Any]:
        """Решает текстовую задачу"""
        if self.api_key == "demo_key":
            return {
                "subject": subject_hint or "математика",
                "response": "Это демо-режим. Для полного функционала настройте OpenAI API ключ."
            }
        
        try:
            system_prompt = self._get_system_prompt(subject_hint)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_text,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1500
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    return self._get_error_response()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                return self._parse_response(content, subject_hint)
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI API: {e}")
            return self._get_error_response()
    
    async def solve_image(self, image_bytes: bytes, subject_hint: str = None) -> Dict[str, Any]:
        """Решает задачу по изображению"""
        if self.api_key == "demo_key":
            return {
                "subject": subject_hint or "математика", 
                "response": "Это демо-режим. Для полного функционала настройте OpenAI API ключ."
            }
        
        try:
            import base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            system_prompt = self._get_system_prompt(subject_hint)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_vision,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Реши задачу на этом изображении:"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_base64}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1500
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    return self._get_error_response()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                return self._parse_response(content, subject_hint)
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI Vision API: {e}")
            return self._get_error_response()
    
    def _get_system_prompt(self, subject_hint: str = None) -> str:
        """Возвращает простой системный промпт"""
        return """Ты - помощник по решению школьных задач. Решай задачи правильно и пошагово.

Используй простые символы для формул:
- Степени: x², x³
- Индексы: x₁, x₂, v₀  
- Дроби: a/b
- Корни: √x
- Греческие буквы: α, β, θ
- Функции: sin(α), cos(β), tan(θ)

Отвечай на русском языке."""
    
    def _parse_response(self, content: str, subject_hint: str = None) -> Dict[str, Any]:
        """Простой парсинг - возвращаем ответ как есть"""
        return {
            "subject": subject_hint or "математика",
            "response": content
        }
    
    def _get_error_response(self) -> Dict[str, Any]:
        """Возвращает ответ при ошибке"""
        return {
            "subject": "неизвестно",
            "response": "Произошла ошибка при обработке запроса. Попробуйте еще раз."
        }


# Глобальный экземпляр клиента
llm_client = LLMClient()
