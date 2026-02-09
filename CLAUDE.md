# CLAUDE.md - Telegram Chat Search V2.0

## Proyecto

Sistema de **busqueda semantica sobre mensajes de Telegram** con interfaz web (Gradio) y resumenes con IA (OpenRouter). El chat indexado es **Freedomia_io** (topic 1478), en espanol.

## Stack

- **Lenguaje**: Python 3.10+
- **BD**: SQLite con FTS5 (full-text search)
- **Embeddings**: sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, 384 dims)
- **Busqueda**: Hibrida (vectorial + FTS5) con Reciprocal Rank Fusion (RRF)
- **LLM**: OpenRouter API (por defecto `anthropic/claude-3-haiku`)
- **UI**: Gradio 4.x con tema oscuro personalizado (colores Freedomia: naranja #e85d04)
- **CLI**: Click + Rich
- **HTTP**: httpx (async)
- **Config**: python-dotenv + dataclass

## Estructura

```
telegram_chat_search/
  __main__.py            # CLI (click): import-html, generate-embeddings, chat, stats, search, add-important-user
  config.py              # Dataclass Config con rutas, API keys, embedding model
  html_parser/
    extractor.py         # Parsea exports HTML de Telegram Desktop
  database/
    schema.py            # Modelos (Message, MessageEmbedding, ImportantUser, SyncState) + DDL SQLite
    repositories.py      # MessageRepository, EmbeddingRepository, ImportantUserRepository
  search/
    embeddings.py        # EmbeddingEngine (encode, search por cosine similarity)
    hybrid_search.py     # HybridSearch: vector_search + fts_search + rrf_fusion
  chat_interface/
    app.py               # TelegramChatBot + create_chat_app (Gradio Blocks)
    deep_links.py        # Genera enlaces directos a mensajes en Telegram
  llm/
    summarizer.py        # OpenRouterSummarizer (httpx async) + MockSummarizer
app.py                   # Entry point para Hugging Face Spaces
run_chat.py              # Script rapido para lanzar el chat localmente
```

## Comandos frecuentes

```bash
# Importar mensajes HTML a SQLite
python -m telegram_chat_search import-html --input ./chats --output ./data/telegram.db

# Generar embeddings
python -m telegram_chat_search generate-embeddings

# Lanzar interfaz web
python -m telegram_chat_search chat --port 7860

# Busqueda CLI
python -m telegram_chat_search search "texto"

# Estadisticas
python -m telegram_chat_search stats

# Instalar dependencias
pip install -r requirements.txt
```

## Datos

- **BD**: `data/telegram_messages.db`
- **Exports HTML**: `chats/` (incluye fotos, stickers, archivos)
- **Sesiones Telethon**: `sessions/` (para sincronizacion futura)
- **Modelo HF cacheado**: `temp_hf/`

## Configuracion (.env)

```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3-haiku
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_PHONE=...
```

## Convenciones

- Idioma del codigo: espanol (docstrings, variables, mensajes)
- Sin tests automatizados (scripts `if __name__ == "__main__"` para pruebas manuales)
- Logging con `logging.getLogger(__name__)`
- Repositorios usan SQLite directamente (sin ORM)
- Los embeddings se almacenan como BLOBs en SQLite
- Los embeddings se cachean en memoria al iniciar el bot (`load_embeddings()`)

## Notas importantes

- La busqueda hibrida usa top_k=50 en produccion (hardcodeado en `app.py:117`)
- El summarizer envia max 15 mensajes al LLM
- Hay un `MockSummarizer` como fallback cuando no hay API key
- Los triggers SQLite mantienen FTS5 sincronizado automaticamente
- El chat_id numerico es `562952938253116`, el username es `Freedomia_io`
- El import comentado de `deep_links` en `app.py:13` indica que los enlaces directos a Telegram no estan integrados en la UI actualmente
