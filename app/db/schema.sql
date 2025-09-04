-- Схема базы данных для школьного бота

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица запросов
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    request_text TEXT,
    request_type TEXT, -- 'text' или 'image'
    subject TEXT,
    response_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- Таблица контекста диалогов
CREATE TABLE IF NOT EXISTS conversation_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    conversation_id TEXT NOT NULL, -- уникальный ID диалога
    message_role TEXT NOT NULL, -- 'user' или 'assistant'
    message_content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_user_id ON requests(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_context_user_id ON conversation_context(user_id);
CREATE INDEX IF NOT EXISTS idx_context_conversation_id ON conversation_context(conversation_id);
CREATE INDEX IF NOT EXISTS idx_context_timestamp ON conversation_context(timestamp);

-- Статистика по дням
CREATE VIEW IF NOT EXISTS daily_stats AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_requests,
    COUNT(DISTINCT user_id) as unique_users
FROM requests
GROUP BY DATE(timestamp);

-- Таблица подписок
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);
