#!/usr/bin/env python3
"""
Точка входа для Telegram-бота "Умный помощник по учёбе"
"""

import sys
import os
import asyncio

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем и запускаем бота
from app.main import main

if __name__ == "__main__":
    asyncio.run(main())
