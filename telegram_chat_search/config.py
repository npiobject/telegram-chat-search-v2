"""
Configuración centralizada del proyecto
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Configuración principal de la aplicación"""

    # Rutas
    base_path: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    html_export_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "chats")
    database_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "telegram_messages.db")

    # Chat info (del export actual)
    chat_id: str = "Freedomia_io"
    topic_id: str = "1478"

    # OpenRouter
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku"))

    # Embeddings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # Búsqueda
    search_top_k: int = 15

    # Usuarios importantes (admins, moderadores)
    important_users: list = field(default_factory=lambda: [
        "Fer - Freedomia.io",
    ])

    def __post_init__(self):
        # Asegurar que existen los directorios
        self.database_path.parent.mkdir(parents=True, exist_ok=True)


# Instancia global de configuración
config = Config()
