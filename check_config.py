#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации Railway
"""

import os
import sys

def check_config():
    """Проверяет конфигурацию Railway"""
    print("🔍 Проверка конфигурации Railway...")
    print("=" * 50)
    
    # Проверяем переменные окружения
    bot_token = os.getenv("BOT_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    admin_ids = os.getenv("ADMIN_IDS", "")
    
    print(f"📋 Переменные окружения:")
    print(f"   BOT_TOKEN: {'✅ Установлен' if bot_token else '❌ НЕ УСТАНОВЛЕН'}")
    print(f"   OPENAI_API_KEY: {'✅ Установлен' if openai_api_key else '⚠️  НЕ УСТАНОВЛЕН (демо-режим)'}")
    print(f"   ADMIN_IDS: {admin_ids if admin_ids else 'Не установлены'}")
    
    if not bot_token:
        print("\n❌ КРИТИЧЕСКАЯ ОШИБКА:")
        print("   Переменная BOT_TOKEN не установлена!")
        print("\n📝 Как исправить:")
        print("   1. Перейдите в настройки проекта в Railway")
        print("   2. Добавьте переменную окружения:")
        print("      Имя: BOT_TOKEN")
        print("      Значение: ваш_токен_бота")
        print("   3. Получите токен у @BotFather в Telegram")
        return False
    
    print("\n✅ Конфигурация корректна!")
    print("🚀 Бот готов к запуску")
    return True

if __name__ == "__main__":
    success = check_config()
    sys.exit(0 if success else 1)
