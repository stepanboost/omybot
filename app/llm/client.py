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
Требования к ответу:
1) Всегда давай решение и КОРОТКОЕ объяснение шаг за шагом.
2) Формулы и выражения — в LaTeX, блоки оборачивай в ```math ... ``` (без подсветки языка).
3) Если задача допускает «короткий ответ», вынеси его в начале.
4) Не придумывай данных, не меняй чисел из условия.
5) Если задача неоднозначна — предложи 1–2 варианта интерпретации и реши каждый кратко.
6) В конце дай «Проверка себя» — 2–3 мини-вопроса по теме (без ответов).
Тон: чёткий, дружелюбный, без морализаторства. Язык — русский."""
        
        if subject_hint:
            subject_prompts = {
                "математика": "\n\nМатематика: аккуратно с единицами, проверяй ответ подстановкой.",
                "физика": "\n\nФизика: указывай единицы измерения, проверяй размерность.",
                "химия": "\n\nХимия: уравнивай реакции, указывай условия.",
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
        # Простой парсинг - в реальной версии можно улучшить
        lines = content.split('\n')
        
        short_answer = ""
        explanation = content
        latex_formulas = []
        quiz = []
        
        # Ищем короткий ответ
        for line in lines:
            if "ответ:" in line.lower() or "результат:" in line.lower():
                short_answer = line.strip()
                break
        
        # Ищем LaTeX формулы
        import re
        latex_matches = re.findall(r'```math\s*(.*?)\s*```', content, re.DOTALL)
        latex_formulas = [match.strip() for match in latex_matches]
        
        # Ищем квиз
        quiz_section = False
        for line in lines:
            if "проверка себя" in line.lower() or "квиз" in line.lower():
                quiz_section = True
                continue
            if quiz_section and line.strip():
                if line.strip().startswith(('1)', '2)', '3)', '•', '-')):
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
