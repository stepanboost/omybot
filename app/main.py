import asyncio
import signal
import sys
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from .config import config
from .handlers.start import router as start_router
from .db.repo import db_repo


class SchoolBot:
    """Простой Telegram-бот для помощи школьникам"""
    
    def __init__(self):
        self.bot = Bot(token=config.bot_token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        
        # Регистрируем обработчики
        self.dp.include_router(start_router)
        
    async def set_commands(self):
        """Устанавливает команды бота"""
        commands = [
            BotCommand(command="start", description="Начать работу с ботом"),
            BotCommand(command="help", description="Справка и примеры"),
        ]
        await self.bot.set_my_commands(commands)
        logger.info("Команды бота установлены")
    
    async def start(self):
        """Запускает бота"""
        try:
            # Инициализируем базу данных
            logger.info("Инициализация базы данных...")
            await db_repo.init_db()
            logger.info("База данных инициализирована")
            
            # Устанавливаем команды
            await self.set_commands()
            
            # Запускаем бота
            logger.info("Бот запускается...")
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
        finally:
            await self.bot.session.close()
            await db_repo.close()
    
    async def stop(self):
        """Останавливает бота"""
        logger.info("Бот останавливается...")
        await self.bot.session.close()
        await db_repo.close()


async def main():
    """Главная функция запуска бота"""
    
    try:
        logger.info("🚀 Запуск Telegram-бота 'Умный помощник по учёбе'")
        
        # Создаем экземпляр бота только при запуске
        school_bot = SchoolBot()
        
        # Настраиваем обработчики сигналов для graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}, завершаем работу...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Запускаем бота
        await school_bot.start()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем работу...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)
    finally:
        # Останавливаем бота
        if 'school_bot' in locals():
            await school_bot.stop()
        await db_repo.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    # Запускаем главную функцию
    asyncio.run(main())
