"""
Репозиторий для работы с базой данных
"""
import aiosqlite
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from ..config import config


class DatabaseRepo:
    """Репозиторий для работы с базой данных"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database_url
        self._connection = None
        
        # Создаем директорию для базы данных, если она не существует
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_connection(self) -> aiosqlite.Connection:
        """Получает соединение с базой данных"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            # Включаем поддержку внешних ключей
            await self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection
    
    async def close(self):
        """Закрывает соединение с базой данных"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def init_db(self):
        """Инициализирует базу данных"""
        try:
            conn = await self.get_connection()
            
            # Читаем схему из файла
            schema_path = Path(__file__).parent / "schema.sql"
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Выполняем SQL команды
            await conn.executescript(schema_sql)
            await conn.commit()
            
        except Exception as e:
            print(f"Ошибка инициализации БД: {e}")
            raise
    
    # === ПОЛЬЗОВАТЕЛИ ===
    
    async def create_user(self, user_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None):
        """Создает или обновляет пользователя"""
        conn = await self.get_connection()
        
        await conn.execute("""
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, username, first_name, last_name))
        
        await conn.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID"""
        conn = await self.get_connection()
        
        cursor = await conn.execute("""
            SELECT * FROM users WHERE user_id = ?
        """, (user_id,))
        
        row = await cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    # === ЗАПРОСЫ ===
    
    async def save_request(self, user_id: int, request_text: str = None, 
                          request_type: str = "text", subject: str = None, 
                          response_text: str = None):
        """Сохраняет запрос пользователя"""
        conn = await self.get_connection()
        
        await conn.execute("""
            INSERT INTO requests (user_id, request_text, request_type, subject, response_text)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, request_text, request_type, subject, response_text))
        
        await conn.commit()
    
    # === КОНТЕКСТ ДИАЛОГОВ ===
    
    async def save_message(self, user_id: int, conversation_id: str, 
                          role: str, content: str):
        """Сохраняет сообщение в контекст диалога"""
        conn = await self.get_connection()
        
        await conn.execute("""
            INSERT INTO conversation_context (user_id, conversation_id, message_role, message_content)
            VALUES (?, ?, ?, ?)
        """, (user_id, conversation_id, role, content))
        
        await conn.commit()
    
    async def get_conversation_context(self, user_id: int, conversation_id: str, 
                                     limit: int = 10) -> List[Dict[str, Any]]:
        """Получает контекст диалога"""
        conn = await self.get_connection()
        
        cursor = await conn.execute("""
            SELECT message_role, message_content, timestamp
            FROM conversation_context
            WHERE user_id = ? AND conversation_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, conversation_id, limit))
        
        rows = await cursor.fetchall()
        return [
            {
                "role": row[0],
                "content": row[1],
                "timestamp": row[2]
            }
            for row in reversed(rows)  # Возвращаем в хронологическом порядке
        ]
    
    async def create_conversation_id(self) -> str:
        """Создает уникальный ID для диалога"""
        return str(uuid.uuid4())
    
    async def cleanup_old_context(self, days: int = 7):
        """Удаляет старый контекст диалогов"""
        conn = await self.get_connection()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        await conn.execute("""
            DELETE FROM conversation_context
            WHERE timestamp < ?
        """, (cutoff_date,))
        
        await conn.commit()
    
    # === ПОДПИСКИ ===
    
    async def set_subscription(self, user_id: int, is_active: bool = True, 
                              expires_at: datetime = None):
        """Устанавливает подписку пользователя"""
        conn = await self.get_connection()
        
        await conn.execute("""
            INSERT OR REPLACE INTO subscriptions (user_id, is_active, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, is_active, expires_at))
        
        await conn.commit()
    
    async def get_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о подписке"""
        conn = await self.get_connection()
        
        cursor = await conn.execute("""
            SELECT * FROM subscriptions WHERE user_id = ?
        """, (user_id,))
        
        row = await cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    # === СТАТИСТИКА ===
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получает статистику пользователя"""
        conn = await self.get_connection()
        
        # Общее количество запросов
        cursor = await conn.execute("""
            SELECT COUNT(*) FROM requests WHERE user_id = ?
        """, (user_id,))
        total_requests = (await cursor.fetchone())[0]
        
        # Запросы за последние 7 дней
        cursor = await conn.execute("""
            SELECT COUNT(*) FROM requests 
            WHERE user_id = ? AND timestamp > datetime('now', '-7 days')
        """, (user_id,))
        recent_requests = (await cursor.fetchone())[0]
        
        # Любимые предметы
        cursor = await conn.execute("""
            SELECT subject, COUNT(*) as count
            FROM requests 
            WHERE user_id = ? AND subject IS NOT NULL
            GROUP BY subject
            ORDER BY count DESC
            LIMIT 3
        """, (user_id,))
        
        favorite_subjects = [
            {"subject": row[0], "count": row[1]}
            for row in await cursor.fetchall()
        ]
        
        return {
            "total_requests": total_requests,
            "recent_requests": recent_requests,
            "favorite_subjects": favorite_subjects
        }


# Глобальный экземпляр репозитория
db_repo = DatabaseRepo()
