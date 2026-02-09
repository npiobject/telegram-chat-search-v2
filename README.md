---
title: Telegram Chat Search
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
---

# Telegram Chat Search - Chat IA

Sistema de búsqueda semántica sobre mensajes de Telegram con interfaz de Chat IA.

## Características

- **Búsqueda híbrida**: Combina búsqueda semántica (embeddings) con búsqueda por keywords (FTS5)
- **Enlaces directos**: Cada resultado incluye un enlace directo al mensaje en Telegram
- **Usuarios importantes**: Los mensajes de administradores y usuarios destacados se resaltan
- **Resúmenes con IA**: Genera resúmenes inteligentes usando OpenRouter (múltiples LLMs)

## Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración
cp .env.example .env
# Editar .env con tu API key de OpenRouter
```

## Uso Rápido

### 1. Importar mensajes desde HTML

```bash
python -m telegram_chat_search import-html
```

### 2. Generar embeddings

```bash
python -m telegram_chat_search generate-embeddings
```

### 3. Lanzar el Chat IA

```bash
python -m telegram_chat_search chat
```

Abre http://localhost:7860 en tu navegador.

## Comandos Disponibles

```bash
# Importar mensajes HTML
python -m telegram_chat_search import-html --input ./chats --output ./data/telegram.db

# Generar embeddings
python -m telegram_chat_search generate-embeddings

# Añadir usuario importante
python -m telegram_chat_search add-important-user --name "Nombre Usuario" --role admin

# Ver estadísticas
python -m telegram_chat_search stats

# Búsqueda rápida desde CLI
python -m telegram_chat_search search "texto a buscar"

# Lanzar interfaz web
python -m telegram_chat_search chat --port 7860
```

## Configuración

### Variables de entorno (.env)

```bash
# OpenRouter API (para resúmenes con IA)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
OPENROUTER_MODEL=anthropic/claude-3-haiku

# Telegram API (opcional, para sincronización futura)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
TELEGRAM_PHONE=+34612345678
```

### Obtener API Key de OpenRouter

1. Visita https://openrouter.ai/keys
2. Crea una cuenta o inicia sesión
3. Genera una nueva API key
4. Copia la key en tu archivo `.env`

### Modelos recomendados en OpenRouter

- `anthropic/claude-3-haiku` - Rápido y económico
- `anthropic/claude-3.5-sonnet` - Mejor calidad
- `google/gemini-flash-1.5` - Muy rápido
- `meta-llama/llama-3-70b-instruct` - Open source

## Estructura del Proyecto

```
telegram_chat_search/
├── __main__.py           # CLI principal
├── config.py             # Configuración
├── html_parser/          # Parser de exports HTML
├── database/             # Schema SQLite + repositorios
├── search/               # Motor de búsqueda híbrida
├── chat_interface/       # Interfaz Gradio
└── llm/                  # Integración OpenRouter
```

## Datos

- **Base de datos**: `data/telegram_messages.db` (SQLite)
- **Embeddings**: Almacenados en la misma base de datos
- **Modelo**: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones)

## Estadísticas actuales

- Mensajes importados: 4,234
- Embeddings generados: 4,154
- Usuarios importantes: 1
