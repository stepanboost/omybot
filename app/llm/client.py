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
                "short_answer": "x = 6",
                "explanation": "Это демо-режим. Для полного функционала настройте OpenAI API ключ.",
                "latex_formulas": [],
                "quiz": []
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
                "short_answer": "Ответ по фото",
                "explanation": "Это демо-режим. Для полного функционала настройте OpenAI API ключ.",
                "latex_formulas": [],
                "quiz": []
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
        """Возвращает системный промпт для предмета"""
        base_prompt = """ТЫ — «Умный помощник по учёбе» для школьника 5–11 классов. 

КРИТИЧЕСКИ ВАЖНО - ФОРМАТИРОВАНИЕ:
1) Всегда давай решение и КОРОТКОЕ объяснение шаг за шагом.
2) Формулы и выражения — используй простые математические символы.
3) Если задача допускает «короткий ответ», вынеси его в начале.
4) Не придумывай данных, не меняй чисел из условия.
5) Если задача неоднозначна — предложи 1–2 варианта интерпретации и реши каждый кратко.
6) В конце дай «Проверка себя» — 2–3 мини-вопроса по теме (без ответов).

ПРАВИЛА МАТЕМАТИЧЕСКОГО ФОРМАТИРОВАНИЯ:
- Степени: x², x³, x^n
- Индексы: x₁, x₂, x₀
- Дроби: a/b или (a)/(b)
- Корни: √x, ³√x
- Греческие буквы: α, β, γ, θ, π
- Функции: sin(α), cos(β), tan(θ)
- Стрелки: →, ←
- Символы: ≈, ≠, ≤, ≥, ±
- Химические элементы: H₂O, CO₂, Fe₂O₃
- Химические стрелки: →, ⇌

СТРУКТУРА ОТВЕТА:
Короткий ответ: [если есть]
Решение:
1. [шаг 1]
2. [шаг 2]
...
Ответ: [финальный ответ]

ВАЖНО: НЕ используй LaTeX блоки \( \) или \[ \]. Используй только простые символы.

Тон: чёткий, дружелюбный, без морализаторства. Язык — русский."""
        
        if subject_hint:
            subject_prompts = {
                "математика": "\n\nМатематика: используй простые символы для формул. Примеры: x² + 2x + 1 = 0, √(a² + b²), sin(α), πr²",
                "физика": "\n\nФизика: используй простые символы для формул. Примеры: F = ma, E = mc², v = v₀ + at, h = v₀²/(2g)",
                "химия": "\n\nХимия: используй простые символы для формул. Примеры: H₂O, CO₂, 2H₂ + O₂ → 2H₂O, CaCO₃ + 2HCl → CaCl₂ + H₂O + CO₂↑",
                "русский": "\n\nРусский язык: объясняй правила, приводи примеры.",
                "литература": "\n\nЛитература: анализируй текст, приводи цитаты.",
                "английский": "\n\nАнглийский язык: объясняй грамматику, давай переводы.",
                "информатика": "\n\nИнформатика: объясняй алгоритмы пошагово.",
                "история": "\n\nИстория: указывай даты, объясняй причины и следствия.",
                "география": "\n\nГеография: используй карты, объясняй процессы.",
                "биология": "\n\nБиология: объясняй процессы, приводи схемы."
            }
            base_prompt += subject_prompts.get(subject_hint.lower(), "")
        
        return base_prompt
    
    def _parse_response(self, content: str, subject_hint: str = None) -> Dict[str, Any]:
        """Парсит ответ от LLM"""
        import re
        
        short_answer = ""
        explanation = content
        latex_formulas = []
        quiz = []
        
        # Ищем короткий ответ
        short_answer_match = re.search(r'Короткий ответ:\s*(.*?)(?=\n\n|Решение:|$)', content, re.IGNORECASE | re.DOTALL)
        if short_answer_match:
            short_answer = short_answer_match.group(1).strip()
        
        # Ищем математические формулы с простыми символами
        # Ищем формулы с греческими буквами, степенями, корнями
        math_patterns = [
            r'[αβγθπ][\w\s\+\-\*\/\^\(\)\d\.]+',  # Греческие буквы
            r'[a-zA-Z]²|[a-zA-Z]³',  # Степени
            r'√[a-zA-Z0-9\(\)\+\-\*\/]+',  # Корни
            r'[a-zA-Z]₁|[a-zA-Z]₂|[a-zA-Z]₀',  # Индексы
            r'[a-zA-Z]₂O|[a-zA-Z]₃',  # Химические формулы
        ]
        
        for pattern in math_patterns:
            matches = re.findall(pattern, content)
            latex_formulas.extend([match.strip() for match in matches])
        
        # Убираем дубликаты
        latex_formulas = list(dict.fromkeys(latex_formulas))
        
        # Ищем квиз
        quiz_section = False
        lines = content.split('\n')
        for line in lines:
            if "проверка себя" in line.lower() or "квиз" in line.lower():
                quiz_section = True
                continue
            if quiz_section and line.strip():
                if line.strip().startswith(('1)', '2)', '3)', '•', '-', '1.', '2.', '3.')):
                    quiz.append(line.strip())
        
        return {
            "subject": subject_hint or "математика",
            "short_answer": short_answer,
            "explanation": explanation,
            "latex_formulas": latex_formulas,
            "quiz": quiz
        }
    
    def _get_error_response(self) -> Dict[str, Any]:
        """Возвращает ответ при ошибке"""
        return {
            "subject": "неизвестно",
            "short_answer": "Ошибка обработки",
            "explanation": "Произошла ошибка при обработке запроса. Попробуйте еще раз.",
            "latex_formulas": [],
            "quiz": []
        }


# Глобальный экземпляр клиента
llm_client = LLMClient()
