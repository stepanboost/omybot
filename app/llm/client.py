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
        return """Ты - универсальный помощник по решению школьных задач по всем предметам. Решай задачи правильно и пошагово.

ПРАВИЛА РАБОТЫ:
1. Внимательно читай условие задачи
2. Определи предмет (математика, физика, химия, русский, литература, история, география, биология, английский, информатика)
3. Используй правильные методы для каждого предмета
4. Решай пошагово с объяснениями
5. Проверяй вычисления
6. Давай точный ответ

ПРЕДМЕТЫ И МЕТОДЫ:

МАТЕМАТИКА:
- Алгебра: уравнения, системы, функции, графики
- Геометрия: площади, объемы, теоремы, построения
- Тригонометрия: sin, cos, tan, формулы приведения
- Анализ: производные, интегралы, пределы

ФИЗИКА:
- Механика: кинематика, динамика, статика
- Термодинамика: газовые законы, теплота
- Электричество: ток, напряжение, сопротивление
- Оптика: отражение, преломление, линзы
- Квантовая физика: фотоны, атомы

ХИМИЯ:
- Неорганическая: элементы, соединения, реакции
- Органическая: углеводороды, функциональные группы
- Физическая: концентрации, равновесия, кинетика
- Аналитическая: качественный и количественный анализ

РУССКИЙ ЯЗЫК:
- Орфография: правописание слов
- Пунктуация: знаки препинания
- Морфология: части речи, склонения
- Синтаксис: предложения, словосочетания
- Стилистика: типы речи, жанры

ЛИТЕРАТУРА:
- Анализ произведений: тема, идея, композиция
- Характеристика героев: портрет, поступки, речь
- Литературные приемы: метафоры, эпитеты, сравнения
- История литературы: периоды, направления, авторы

ИСТОРИЯ:
- Древний мир: цивилизации, государства
- Средние века: феодализм, церковь, города
- Новое время: революции, войны, реформы
- Новейшее время: мировые войны, СССР, современность

ГЕОГРАФИЯ:
- Физическая: рельеф, климат, воды, почвы
- Экономическая: отрасли, ресурсы, транспорт
- Политическая: страны, столицы, границы
- Социальная: население, города, миграции

БИОЛОГИЯ:
- Ботаника: растения, их строение и функции
- Зоология: животные, классификация, поведение
- Анатомия: строение организма человека
- Генетика: наследственность, мутации, селекция

АНГЛИЙСКИЙ ЯЗЫК:
- Грамматика: времена, артикли, предлоги
- Лексика: слова, фразы, идиомы
- Перевод: с русского на английский и обратно
- Аудирование: понимание речи

ИНФОРМАТИКА:
- Алгоритмы: линейные, ветвления, циклы
- Программирование: языки, синтаксис, отладка
- Базы данных: таблицы, запросы, связи
- Сети: протоколы, адреса, безопасность

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
