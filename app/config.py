import os
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


class Config(BaseModel):
    """Конфигурация приложения"""
    
    # Telegram Bot
    bot_token: str = Field(..., description="Токен Telegram бота")
    
    # OpenAI API
    openai_api_key: str = Field(..., description="API ключ OpenAI")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Базовый URL для OpenAI API"
    )
    llm_model_text: str = Field(
        default="gpt-4o-mini",
        description="Модель для текстовых запросов"
    )
    llm_model_vision: str = Field(
        default="gpt-4o-mini",
        description="Модель для запросов с изображениями"
    )
    
    # Администраторы
    admin_ids: List[int] = Field(default_factory=list, description="ID администраторов")
    
    # Лимиты
    rate_limit_per_hour: int = Field(
        default=10,
        description="Максимальное количество запросов в час на пользователя"
    )
    
    # База данных
    database_url: str = Field(
        default="data/schoolbot.db",
        description="Путь к SQLite базе данных"
    )
    
    # Логирование
    log_level: str = Field(
        default="INFO",
        description="Уровень логирования"
    )
    log_file: str = Field(
        default="logs/schoolbot.log",
        description="Файл для логов"
    )


def load_config() -> Config:
    """Загружает конфигурацию из переменных окружения"""
    
    # Парсим admin_ids из строки
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids = []
    if admin_ids_str:
        admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_model_text=os.getenv("LLM_MODEL_TEXT", "gpt-4o-mini"),
        llm_model_vision=os.getenv("LLM_MODEL_VISION", "gpt-4o-mini"),
        admin_ids=admin_ids,
        rate_limit_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "10")),
        database_url=os.getenv("DATABASE_URL", "data/schoolbot.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "logs/schoolbot.log")
    )


# Глобальный экземпляр конфигурации
config = load_config()
