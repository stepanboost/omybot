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
    
    # === ОЧИСТКА ДАННЫХ ===
    
    async def cleanup_old_data(self, days: int = 7):
        """Удаляет старые данные для экономии места"""
        conn = await self.get_connection()
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Удаляем старый контекст диалогов
            cursor = await conn.execute("""
                DELETE FROM conversation_context
                WHERE timestamp < ?
            """, (cutoff_date,))
            context_deleted = cursor.rowcount
            
            # Удаляем старые запросы (оставляем только последние 30 дней)
            old_requests_cutoff = datetime.now() - timedelta(days=30)
            cursor = await conn.execute("""
                DELETE FROM requests
                WHERE timestamp < ?
            """, (old_requests_cutoff,))
            requests_deleted = cursor.rowcount
            
            # Удаляем неактивных пользователей (не заходили больше 90 дней)
            inactive_users_cutoff = datetime.now() - timedelta(days=90)
            cursor = await conn.execute("""
                DELETE FROM users
                WHERE user_id NOT IN (
                    SELECT DISTINCT user_id FROM requests 
                    WHERE timestamp > ?
                ) AND updated_at < ?
            """, (inactive_users_cutoff, inactive_users_cutoff))
            users_deleted = cursor.rowcount
            
            # Удаляем старые подписки (истекшие больше 30 дней назад)
            expired_subs_cutoff = datetime.now() - timedelta(days=30)
            cursor = await conn.execute("""
                DELETE FROM subscriptions
                WHERE expires_at < ? AND is_active = FALSE
            """, (expired_subs_cutoff,))
            subs_deleted = cursor.rowcount
            
            await conn.commit()
            
            return {
                "context_messages_deleted": context_deleted,
                "old_requests_deleted": requests_deleted,
                "inactive_users_deleted": users_deleted,
                "expired_subscriptions_deleted": subs_deleted
            }
            
        except Exception as e:
            await conn.rollback()
            raise e
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Получает статистику базы данных"""
        conn = await self.get_connection()
        
        # Количество записей в каждой таблице
        tables = ['users', 'requests', 'conversation_context', 'subscriptions']
        stats = {}
        
        for table in tables:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = (await cursor.fetchone())[0]
            stats[f"{table}_count"] = count
        
        # Размер базы данных (приблизительно)
        cursor = await conn.execute("""
            SELECT page_count * page_size as size_bytes
            FROM pragma_page_count(), pragma_page_size()
        """)
        size_result = await cursor.fetchone()
        stats["database_size_bytes"] = size_result[0] if size_result else 0
        stats["database_size_mb"] = round(stats["database_size_bytes"] / (1024 * 1024), 2)
        
        # Старые данные
        cutoff_date = datetime.now() - timedelta(days=7)
        cursor = await conn.execute("""
            SELECT COUNT(*) FROM conversation_context WHERE timestamp < ?
        """, (cutoff_date,))
        stats["old_context_messages"] = (await cursor.fetchone())[0]
        
        old_requests_cutoff = datetime.now() - timedelta(days=30)
        cursor = await conn.execute("""
            SELECT COUNT(*) FROM requests WHERE timestamp < ?
        """, (old_requests_cutoff,))
        stats["old_requests"] = (await cursor.fetchone())[0]
        
        return stats
    
    async def vacuum_database(self):
        """Оптимизирует базу данных (VACUUM)"""
        conn = await self.get_connection()
        await conn.execute("VACUUM")
        await conn.commit()
    
    async def delete_user_data(self, user_id: int):
        """Полностью удаляет все данные пользователя (GDPR compliance)"""
        conn = await self.get_connection()
        
        try:
            # Удаляем в правильном порядке (с учетом внешних ключей)
            await conn.execute("DELETE FROM conversation_context WHERE user_id = ?", (user_id,))
            await conn.execute("DELETE FROM requests WHERE user_id = ?", (user_id,))
            await conn.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            await conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            
            await conn.commit()
            return True
            
        except Exception as e:
            await conn.rollback()
            raise e


# Глобальный экземпляр репозитория
db_repo = DatabaseRepo()
