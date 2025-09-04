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
        base_prompt = """Ты - помощник по решению школьных задач. Решай задачи правильно и пошагово.

ПРАВИЛА:
1. Внимательно читай условие задачи
2. Используй правильные формулы
3. Проверяй вычисления
4. Давай точный ответ

ФОРМАТИРОВАНИЕ:
- Степени: x², x³
- Индексы: x₁, x₂, v₀
- Дроби: a/b
- Корни: √x
- Греческие буквы: α, β, θ
- Функции: sin(α), cos(β), tan(θ)

СТРУКТУРА:
Короткий ответ: [если есть]
Решение:
1. [шаг 1]
2. [шаг 2]
...
Ответ: [финальный ответ]

ВАЖНО: НЕ используй LaTeX блоки [ ] или \( \). Используй только простые символы.

Язык: русский."""
        
        if subject_hint:
            subject_prompts = {
                "математика": "\n\nМатематика: ВАЖНО - внимательно читай условие! Решай пошагово:\n- Квадратные уравнения: ax² + bx + c = 0, D = b² - 4ac\n- Системы уравнений: подстановка или сложение\n- Геометрия: площади, объемы, теоремы\nПроверяй ответ подстановкой!",
                "физика": "\n\nФизика: ВАЖНО - внимательно читай условие! Используй правильные формулы:\n- Кинематика: v = v₀ + at, s = v₀t + at²/2, v² = v₀² + 2as\n- Динамика: F = ma, F = mg\n- Энергия: E = mv²/2, E = mgh\n- Баллистика: h = v₀²sin²(α)/(2g), s = v₀²sin(2α)/g\n- Вращение: ω = ω₀ + εt, φ = ω₀t + εt²/2, n = N/t, ω = 2πn\nПроверяй единицы измерения!",
                "химия": "\n\nХимия: уравнивай реакции, вычисляй молярные массы, решай задачи на концентрации.",
                "русский": "\n\nРусский язык: объясняй правила орфографии и пунктуации.",
                "литература": "\n\nЛитература: анализируй произведения, объясняй литературные приемы.",
                "английский": "\n\nАнглийский язык: объясняй грамматику, переводи тексты.",
                "информатика": "\n\nИнформатика: объясняй алгоритмы, решай задачи программирования.",
                "история": "\n\nИстория: объясняй исторические события и их причины.",
                "география": "\n\nГеография: объясняй географические процессы и явления.",
                "биология": "\n\nБиология: объясняй биологические процессы и закономерности."
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
