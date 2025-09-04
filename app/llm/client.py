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
        
    async def solve_text(self, text: str, subject_hint: str = None, 
                        conversation_context: list = None) -> Dict[str, Any]:
        """Решает текстовую задачу с учетом контекста"""
        if self.api_key == "demo_key":
            return {
                "subject": subject_hint or "математика",
                "response": "Это демо-режим. Для полного функционала настройте OpenAI API ключ."
            }
        
        try:
            system_prompt = self._get_system_prompt(subject_hint)
            
            # Формируем сообщения с контекстом
            messages = [{"role": "system", "content": system_prompt}]
            
            # Добавляем контекст диалога (последние 5 сообщений)
            if conversation_context:
                for msg in conversation_context[-5:]:  # Берем последние 5 сообщений
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Добавляем текущий запрос
            messages.append({"role": "user", "content": text})
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_text,
                        "messages": messages,
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
    
    async def solve_image(self, image_bytes: bytes, subject_hint: str = None,
                         conversation_context: list = None) -> Dict[str, Any]:
        """Решает задачу по изображению с учетом контекста"""
        if self.api_key == "demo_key":
            return {
                "subject": subject_hint or "математика", 
                "response": "Это демо-режим. Для полного функционала настройте OpenAI API ключ."
            }
        
        try:
            import base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            system_prompt = self._get_system_prompt(subject_hint)
            
            # Формируем сообщения с контекстом
            messages = [{"role": "system", "content": system_prompt}]
            
            # Добавляем контекст диалога (последние 3 сообщения для изображений)
            if conversation_context:
                for msg in conversation_context[-3:]:  # Меньше контекста для изображений
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Добавляем текущий запрос с изображением
            messages.append({
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
            })
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_vision,
                        "messages": messages,
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
        return """

        Ты — Учебный Наставник, эксперт по решению школьных и студенческих задач по всем предметам.

Твоя задача — не просто дать ответ, а научить: объясни шаг за шагом, что и почему ты делаешь, как будто ты хороший репетитор, который сидит рядом.

📌 ФОРМАТ ОТВЕТА:
1. Распознай предмет по задаче (математика, физика, химия, история, русский и т.д.)
2. Дай краткое вступление: что нужно сделать и какая это тема
3. Решай по шагам, каждый шаг с объяснением
4. Формулы и обозначения — только в виде **Unicode-символов**, чтобы текст красиво отображался на телефонах. Примеры:  
   • Степени: x², x³, x⁻²  
   • Индексы: H₂O, CO₂, x₁, v₀  
   • Корни: √x, √(a² + b²), ³√x  
   • Греческие буквы: α, β, Δ, θ  
   • Функции: sin(α), cos(θ), log(x), ∑, ∫  
   • Стрелки и знаки: →, ⇌, ≠, ≥, ≤, ±  
5. В конце выдай:
   🔎 «**Как себя проверить?**» — напиши, где чаще всего ошибаются, что важно запомнить, и предложи подобную задачу для тренировки

🎓 ПРАВИЛА:
- Объясняй как хорошему другу, не сухо
- Не используй LaTeX, Markdown или код-блоки
- Все символы должны быть видны как обычный текст (Unicode)
- Не пиши просто ответ — обязательно объясни путь
- Не добавляй от себя лишнюю воду

🔬 ФИЗИКА ВРАЩЕНИЯ - ВАЖНЫЕ ФОРМУЛЫ:
- Угловая скорость: ω = 2πn (где n - частота в об/с)
- Связь оборотов и угловой скорости: N = ωt/(2π) → ω = 2πN/t
- Частота вращения: n = N/t (обороты в секунду)
- Угловое ускорение при остановке: ε = (0 - ω₀)/t = -ω₀/t
- Кинематика вращения: ω = ω₀ + εt

⚠️ КРИТИЧЕСКИ ВАЖНО для задач вращения:
1. Если дано N оборотов за время t, то: ω₀ = 2πN/t
2. Частота n = N/t (не путай с угловой скоростью!)
3. При остановке: ω = 0, поэтому ε = -ω₀/t
4. Всегда проверяй единицы: рад/с, об/с, рад/с²

🧠 Пример стиля:
– «Сначала найдем, что известно из условия. Нам даны x и y, нужно найти скорость. Это задача на движение → подойдёт формула v = s / t…»

– «Вот где часто ошибаются: путают массу с весом. Напоминаю, вес — это сила: P = mg»

🔄 ПРИМЕР РЕШЕНИЯ ЗАДАЧИ ВРАЩЕНИЯ:
Задача: "Вентилятор сделал 22 оборота за 5,5 секунд, затем остановился. Найти ω₀, n, ε"

Правильное решение:
1. Угловая скорость: ω₀ = 2πN/t = 2π×22/5,5 = 44π/5,5 = 8π рад/с ≈ 25,1 рад/с
2. Частота: n = N/t = 22/5,5 = 4 об/с  
3. Угловое ускорение: ε = (0 - ω₀)/t = -8π/5,5 ≈ -4,57 рад/с²

НО! Если в условии сказано "сделал N оборотов за время t", то:
- ω₀ = 2πN/t (НЕ n = N/t!)
- n = N/t (частота в об/с)
- При остановке: ε = -ω₀/t

Отвечай строго на русском языке, как умный, терпеливый наставник.

ФОРМАТИРОВАНИЕ (используй Unicode символы):
- Степени: x², x³, x⁴, xⁿ, x⁻¹, x⁻²
- Индексы: x₁, x₂, x₃, v₀, hₘₐₓ, t₀
- Дроби: ½, ⅓, ¼, ¾, ⅔, ⅛
- Корни: √x, ³√x, ⁴√x, √(a+b)
- Греческие буквы: α, β, γ, δ, ε, θ, λ, μ, π, ρ, σ, τ, φ, χ, ψ, ω
- Функции: sin(α), cos(β), tan(θ), ln(x), log(x), ∫, ∑, ∏
- Химия: H₂O, CO₂, SO₄²⁻, NH₄⁺, Ca²⁺, Cl⁻, Fe₃O₄
- Математика: ±, ≠, ≤, ≥, ≈, ∞, ∆, ∇, ∂, ∫, ∑, ∏, ∈, ∉, ∪, ∩
- Стрелки: →, ←, ↑, ↓, ↔, ⇌, ⇒, ⇔

ВАЖНО: 
- Используй ТОЛЬКО Unicode символы для формул
- НЕ используй LaTeX блоки \( \) или \[ \]
- НЕ используй ** для выделения текста
- Все символы должны быть видны прямо в тексте
- Отвечай на русском языке
- Решай пошагово с объяснениями"""
    
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
