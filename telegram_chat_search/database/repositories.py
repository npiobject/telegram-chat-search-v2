"""
Repositorios para acceso a datos
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Iterator
import numpy as np
import logging

from .schema import Message, get_connection

logger = logging.getLogger(__name__)


class MessageRepository:
    """Repositorio para operaciones CRUD de mensajes"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    def insert_message(self, msg: Message) -> None:
        """Inserta un mensaje en la base de datos"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO messages (
                    id, chat_id, topic_id, sender_name, is_important_user,
                    message_type, text, text_clean, timestamp, timestamp_utc,
                    reply_to_message_id, source, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                msg.id, msg.chat_id, msg.topic_id, msg.sender_name, msg.is_important_user,
                msg.message_type, msg.text, msg.text_clean, msg.timestamp, msg.timestamp_utc,
                msg.reply_to_message_id, msg.source, msg.source_file
            ))
            conn.commit()

    def bulk_insert(self, messages: list[Message], batch_size: int = 100) -> int:
        """
        Inserta múltiples mensajes de forma eficiente.

        Returns:
            Número de mensajes insertados
        """
        count = 0
        with self._get_conn() as conn:
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                conn.executemany("""
                    INSERT OR REPLACE INTO messages (
                        id, chat_id, topic_id, sender_name, is_important_user,
                        message_type, text, text_clean, timestamp, timestamp_utc,
                        reply_to_message_id, source, source_file
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (
                        msg.id, msg.chat_id, msg.topic_id, msg.sender_name, msg.is_important_user,
                        msg.message_type, msg.text, msg.text_clean, msg.timestamp, msg.timestamp_utc,
                        msg.reply_to_message_id, msg.source, msg.source_file
                    )
                    for msg in batch
                ])
                count += len(batch)

            conn.commit()

        logger.info(f"Insertados {count} mensajes")
        return count

    def get_message(self, message_id: int) -> Optional[Message]:
        """Obtiene un mensaje por ID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM messages WHERE id = ?",
                (message_id,)
            ).fetchone()

            if row:
                return self._row_to_message(row)
            return None

    def get_all_messages(self) -> list[Message]:
        """Obtiene todos los mensajes"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages ORDER BY timestamp"
            ).fetchall()
            return [self._row_to_message(row) for row in rows]

    def get_messages_with_text(self) -> list[Message]:
        """Obtiene solo mensajes con texto (para generar embeddings)"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM messages
                WHERE text_clean IS NOT NULL
                AND text_clean != ''
                AND message_type != 'service'
                ORDER BY id
            """).fetchall()
            return [self._row_to_message(row) for row in rows]

    def get_latest_message_id(self, chat_id: str, topic_id: str) -> Optional[int]:
        """Obtiene el ID del último mensaje para sincronización incremental"""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT MAX(id) as max_id FROM messages
                WHERE chat_id = ? AND topic_id = ?
            """, (chat_id, topic_id)).fetchone()

            if row and row['max_id']:
                return row['max_id']
            return None

    def count_messages(self) -> int:
        """Cuenta el total de mensajes"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM messages").fetchone()
            return row['count']

    def _sanitize_fts_query(self, query: str) -> str:
        """
        Sanitiza la query para FTS5, escapando caracteres especiales.
        """
        import re
        # Eliminar caracteres especiales de FTS5
        sanitized = re.sub(r'[",\*\(\)\:\+\-\^\[\]\{\}\?\!]', ' ', query)
        # Limpiar espacios múltiples
        sanitized = ' '.join(sanitized.split()).strip()
        return sanitized if sanitized else None

    def fts_search(self, query: str, limit: int = 20) -> list[tuple[Message, float]]:
        """
        Búsqueda Full-Text Search con FTS5.

        Returns:
            Lista de tuplas (mensaje, score)
        """
        # Sanitizar query para evitar errores de sintaxis FTS5
        safe_query = self._sanitize_fts_query(query)
        if not safe_query:
            return []

        try:
            with self._get_conn() as conn:
                # FTS5 con ranking BM25
                rows = conn.execute("""
                    SELECT m.*, bm25(messages_fts) as score
                    FROM messages_fts fts
                    JOIN messages m ON fts.rowid = m.id
                    WHERE messages_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                """, (safe_query, limit)).fetchall()

                return [(self._row_to_message(row), row['score']) for row in rows]
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"FTS search failed: {e}")
            return []

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Convierte una fila de SQLite a objeto Message"""
        return Message(
            id=row['id'],
            chat_id=row['chat_id'],
            topic_id=row['topic_id'],
            sender_name=row['sender_name'],
            is_important_user=bool(row['is_important_user']),
            message_type=row['message_type'],
            text=row['text'],
            text_clean=row['text_clean'],
            timestamp=row['timestamp'],
            timestamp_utc=row['timestamp_utc'],
            reply_to_message_id=row['reply_to_message_id'],
            source=row['source'],
            source_file=row['source_file'],
        )


class EmbeddingRepository:
    """Repositorio para embeddings vectoriales"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    def save_embedding(self, message_id: int, embedding: np.ndarray, model_name: str) -> None:
        """Guarda un embedding"""
        embedding_bytes = embedding.astype(np.float32).tobytes()

        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO message_embeddings (message_id, embedding, model_name)
                VALUES (?, ?, ?)
            """, (message_id, embedding_bytes, model_name))
            conn.commit()

    def bulk_save_embeddings(
        self,
        message_ids: list[int],
        embeddings: np.ndarray,
        model_name: str,
        batch_size: int = 100
    ) -> None:
        """Guarda múltiples embeddings de forma eficiente"""
        with self._get_conn() as conn:
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]

                conn.executemany("""
                    INSERT OR REPLACE INTO message_embeddings (message_id, embedding, model_name)
                    VALUES (?, ?, ?)
                """, [
                    (msg_id, emb.astype(np.float32).tobytes(), model_name)
                    for msg_id, emb in zip(batch_ids, batch_embeddings)
                ])

            conn.commit()

        logger.info(f"Guardados {len(message_ids)} embeddings")

    def get_all_embeddings(self) -> tuple[list[int], np.ndarray]:
        """
        Obtiene todos los embeddings.

        Returns:
            Tupla de (lista de message_ids, matriz de embeddings)
        """
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT message_id, embedding FROM message_embeddings
                ORDER BY message_id
            """).fetchall()

            if not rows:
                return [], np.array([])

            message_ids = [row['message_id'] for row in rows]
            embeddings = np.array([
                np.frombuffer(row['embedding'], dtype=np.float32)
                for row in rows
            ])

            return message_ids, embeddings

    def count_embeddings(self) -> int:
        """Cuenta el total de embeddings"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM message_embeddings").fetchone()
            return row['count']


class ImportantUserRepository:
    """Repositorio para usuarios importantes"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    def add_user(self, user_name: str, role: str = "important", color: str = "#FFD700") -> None:
        """Añade un usuario importante"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO important_users (user_name, role, highlight_color)
                VALUES (?, ?, ?)
            """, (user_name, role, color))
            conn.commit()

    def get_all_users(self) -> list[str]:
        """Obtiene todos los nombres de usuarios importantes"""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT user_name FROM important_users").fetchall()
            return [row['user_name'] for row in rows]

    def is_important(self, user_name: str) -> bool:
        """Verifica si un usuario es importante"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM important_users WHERE user_name = ?",
                (user_name,)
            ).fetchone()
            return row is not None

    def mark_important_messages(self) -> int:
        """
        Actualiza el flag is_important_user en todos los mensajes
        de usuarios importantes.

        Returns:
            Número de mensajes actualizados
        """
        with self._get_conn() as conn:
            cursor = conn.execute("""
                UPDATE messages
                SET is_important_user = TRUE
                WHERE sender_name IN (SELECT user_name FROM important_users)
            """)
            conn.commit()
            return cursor.rowcount
