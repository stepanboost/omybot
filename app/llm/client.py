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
                        "temperature": 0.1,
                        "max_tokens": 2000
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
                        "temperature": 0.1,
                        "max_tokens": 2000
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
        """Возвращает улучшенный системный промпт"""
        return """Ты - эксперт по решению школьных задач. Решай задачи правильно и пошагово.

ВАЖНЫЕ ПРАВИЛА:
1. Внимательно читай условие задачи
2. Используй правильные формулы для каждого предмета
3. Проверяй вычисления несколько раз
4. Давай точный численный ответ
5. Объясняй каждый шаг решения

ФОРМУЛЫ ДЛЯ ФИЗИКИ:
- Кинематика: v = v₀ + at, s = v₀t + at²/2, v² = v₀² + 2as
- Динамика: F = ma, F = mg
- Энергия: E = mv²/2, E = mgh
- Вращение: ω = ω₀ + εt, n = N/t, ω = 2πn, ε = (ω - ω₀)/t
- ВАЖНО для вращения: если тело остановилось, то ω = 0, ε = (0 - ω₀)/t
- Баллистика: h = v₀²sin²(α)/(2g), s = v₀²sin(2α)/g

ФОРМУЛЫ ДЛЯ МАТЕМАТИКИ:
- Квадратные уравнения: ax² + bx + c = 0, D = b² - 4ac, x = (-b ± √D)/(2a)
- Системы уравнений: подстановка или сложение
- Геометрия: площади, объемы, теоремы

ФОРМАТИРОВАНИЕ:
- Степени: x², x³
- Индексы: x₁, x₂, v₀  
- Дроби: a/b
- Корни: √x
- Греческие буквы: α, β, θ, ω, ε
- Функции: sin(α), cos(β), tan(θ)

ПРИМЕРЫ ПРАВИЛЬНОГО РЕШЕНИЯ:

Задача на вращение вентилятора:
Дано: N = 22 оборота, t = 5.5 с, остановился
Решение:
1. Частота вращения: n = N/t = 22/5.5 = 4 об/с
2. Угловая скорость: ω₀ = 2πn = 2π × 4 = 8π рад/с ≈ 25.1 рад/с
3. Угловое ускорение: ε = (0 - ω₀)/t = -8π/5.5 ≈ -4.57 рад/с²

Отвечай на русском языке. Проверяй ответ подстановкой!"""
    
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
