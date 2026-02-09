"""
Esquema de base de datos SQLite con FTS5 para búsqueda de texto
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Modelo de mensaje en la base de datos"""
    id: int
    chat_id: str
    topic_id: str
    sender_name: str
    text: str
    text_clean: str
    timestamp: datetime
    timestamp_utc: datetime
    message_type: str
    reply_to_message_id: Optional[int] = None
    source: str = "html_export"
    source_file: Optional[str] = None
    is_important_user: bool = False


@dataclass
class MessageEmbedding:
    """Embedding vectorial de un mensaje"""
    message_id: int
    embedding: bytes  # numpy array serializado
    model_name: str


@dataclass
class ImportantUser:
    """Usuario marcado como importante (admin, experto, etc.)"""
    id: int
    user_name: str
    role: str
    highlight_color: str = "#FFD700"


@dataclass
class SyncState:
    """Estado de sincronización para actualizaciones incrementales"""
    chat_id: str
    topic_id: str
    last_message_id: int
    last_message_date: datetime
    last_sync_at: datetime


# SQL para crear las tablas
CREATE_TABLES_SQL = """
-- Tabla principal de mensajes
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    chat_id TEXT NOT NULL,
    topic_id TEXT,

    sender_name TEXT NOT NULL,
    is_important_user BOOLEAN DEFAULT FALSE,

    message_type TEXT NOT NULL,
    text TEXT,
    text_clean TEXT,

    timestamp DATETIME NOT NULL,
    timestamp_utc DATETIME NOT NULL,

    reply_to_message_id INTEGER,

    source TEXT NOT NULL DEFAULT 'html_export',
    source_file TEXT,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Índices para búsqueda eficiente
CREATE INDEX IF NOT EXISTS idx_messages_chat_topic ON messages(chat_id, topic_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_name);
CREATE INDEX IF NOT EXISTS idx_messages_important ON messages(is_important_user);

-- Full-Text Search (FTS5) para búsqueda de texto
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    text_clean,
    sender_name,
    content='messages',
    content_rowid='id',
    tokenize='unicode61'
);

-- Triggers para mantener FTS sincronizado
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, text_clean, sender_name)
    VALUES (new.id, new.text_clean, new.sender_name);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, text_clean, sender_name)
    VALUES ('delete', old.id, old.text_clean, old.sender_name);
END;

CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, text_clean, sender_name)
    VALUES ('delete', old.id, old.text_clean, old.sender_name);
    INSERT INTO messages_fts(rowid, text_clean, sender_name)
    VALUES (new.id, new.text_clean, new.sender_name);
END;

-- Tabla de embeddings vectoriales
CREATE TABLE IF NOT EXISTS message_embeddings (
    message_id INTEGER PRIMARY KEY,
    embedding BLOB NOT NULL,
    model_name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

-- Usuarios importantes (administradores, moderadores, expertos)
CREATE TABLE IF NOT EXISTS important_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL UNIQUE,
    role TEXT DEFAULT 'important',
    highlight_color TEXT DEFAULT '#FFD700'
);

-- Estado de sincronización
CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    topic_id TEXT,
    last_message_id INTEGER,
    last_message_date DATETIME,
    last_sync_at DATETIME,
    UNIQUE(chat_id, topic_id)
);
"""


def init_database(db_path: Path) -> sqlite3.Connection:
    """
    Inicializa la base de datos creando las tablas necesarias.

    Args:
        db_path: Ruta al archivo de base de datos SQLite

    Returns:
        Conexión a la base de datos
    """
    logger.info(f"Inicializando base de datos en {db_path}")

    # Asegurar que existe el directorio
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Conectar y crear tablas
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Ejecutar SQL de creación
    conn.executescript(CREATE_TABLES_SQL)
    conn.commit()

    logger.info("Base de datos inicializada correctamente")
    return conn


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Obtiene una conexión a la base de datos existente"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    # Test de creación de base de datos
    import tempfile

    logging.basicConfig(level=logging.INFO)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_path = Path(f.name)

    conn = init_database(test_path)

    # Verificar tablas creadas
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tablas creadas: {tables}")

    conn.close()
    test_path.unlink()
