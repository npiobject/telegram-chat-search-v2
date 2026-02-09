"""
Interfaz de Chat IA usando Gradio
"""

from pathlib import Path
from typing import Optional
import logging

from ..config import config
from ..search.hybrid_search import HybridSearch, SearchResult
from ..database.repositories import ImportantUserRepository
from ..llm.summarizer import OpenRouterSummarizer, MockSummarizer
from ..search.filters import es_mensaje_bajo_valor
# from .deep_links import generate_telegram_links, format_links_markdown

logger = logging.getLogger(__name__)


class TelegramChatBot:
    """Bot de búsqueda en chats de Telegram"""

    def __init__(
        self,
        db_path: Path,
        openrouter_api_key: str = "",
        openrouter_model: str = "anthropic/claude-3-haiku",
        important_users: Optional[list[str]] = None
    ):
        self.db_path = db_path
        self.search_engine = HybridSearch(db_path)
        self.important_users = set(important_users or [])

        # Cargar usuarios importantes de la base de datos
        try:
            user_repo = ImportantUserRepository(db_path)
            db_important_users = user_repo.get_all_users()
            self.important_users.update(db_important_users)
        except Exception as e:
            logger.warning(f"No se pudieron cargar usuarios importantes: {e}")

        # Inicializar summarizer
        if openrouter_api_key:
            self.summarizer = OpenRouterSummarizer(openrouter_api_key, openrouter_model)
        else:
            logger.warning("No hay API key de OpenRouter, usando mock summarizer")
            self.summarizer = MockSummarizer()

        # Precargar embeddings
        logger.info("Precargando embeddings...")
        self.search_engine.load_embeddings()

    def format_result(self, result: SearchResult, index: int) -> str:
        """Formatea un resultado de búsqueda para mostrar"""
        msg = result.message

        # Determinar si es usuario importante
        is_important = msg.sender_name in self.important_users or msg.is_important_user

        # Formatear timestamp a DD-MM-AAAA HH:MM
        if msg.timestamp:
            try:
                from datetime import datetime
                ts = msg.timestamp if isinstance(msg.timestamp, datetime) else datetime.fromisoformat(str(msg.timestamp)[:19])
                timestamp_str = ts.strftime("%d-%m-%Y %H:%M")
            except:
                timestamp_str = str(msg.timestamp)[:19]
        else:
            timestamp_str = "N/A"

        # Truncar texto largo
        text = msg.text or ""
        if len(text) > 300:
            text = text[:300] + "..."

        # Indicador de tipo de match
        match_icon = {
            'vector': '🧠',
            'fts': '🔤',
            'hybrid': '✨'
        }.get(result.match_type, '')

        if is_important:
            return f"""
### ⭐ {index}. {msg.sender_name} (Usuario Importante)
**Fecha:** {timestamp_str} | {match_icon} Score: {result.score:.3f}

> {text}

---
"""
        else:
            return f"""
### {index}. {msg.sender_name}
**Fecha:** {timestamp_str} | {match_icon} Score: {result.score:.3f}

> {text}

---
"""

    def search_and_respond(self, query: str) -> str:
        """
        Busca mensajes y genera respuesta con resumen.

        Args:
            query: Pregunta del usuario

        Returns:
            Respuesta formateada en Markdown
        """
        if not query.strip():
            return "Por favor, escribe una pregunta para buscar en el chat."

        logger.info(f"Procesando consulta: {query}")

        # Buscar mensajes relevantes
        # results = self.search_engine.search(query, top_k=15)
        results = self.search_engine.search(query, top_k=50)

        # Filtrar mensajes de bajo valor (monosilabos, risas, etc.)
        results = [r for r in results if not es_mensaje_bajo_valor(r.message.text_clean)]

        if not results:
            return f"""
## 🔍 No se encontraron resultados

No se encontraron mensajes relevantes para: **"{query}"**

Intenta con otros términos de búsqueda.
"""

        # Formatear mensajes encontrados
        formatted_results = []
        messages_for_summary = []

        for i, result in enumerate(results, 1):
            formatted_results.append(self.format_result(result, i))
            messages_for_summary.append({
                'sender_name': result.message.sender_name,
                'text': result.message.text or "",
                'timestamp': str(result.message.timestamp)[:19]
            })

        # Generar resumen con LLM
        summary = self.summarizer.summarize(query, messages_for_summary)

        # Componer respuesta final
        response = f"""
## 📝 Resumen

{summary}

---

## 🔍 Mensajes encontrados ( Máximo: {len(results)} )

{''.join(formatted_results)}
"""

        return response


def create_chat_app(
    db_path: Optional[Path] = None,
    openrouter_api_key: Optional[str] = None,
    openrouter_model: Optional[str] = None,
    important_users: Optional[list[str]] = None
):
    """
    Crea y configura la aplicación Gradio.

    Args:
        db_path: Ruta a la base de datos (default: config)
        openrouter_api_key: API key de OpenRouter (default: config)
        openrouter_model: Modelo de OpenRouter (default: config)
        important_users: Lista de usuarios importantes (default: config)

    Returns:
        Aplicación Gradio
    """
    try:
        import gradio as gr
    except ImportError:
        raise ImportError("Gradio no está instalado. Ejecuta: pip install gradio")

    # Usar valores de config si no se especifican
    db_path = db_path or config.database_path
    openrouter_api_key = openrouter_api_key or config.openrouter_api_key
    openrouter_model = openrouter_model or config.openrouter_model
    important_users = important_users or config.important_users

    if not db_path.exists():
        raise FileNotFoundError(
            f"Base de datos no encontrada: {db_path}\n"
            "Primero ejecuta: python -m telegram_chat_search import-html"
        )

    # Crear bot
    bot = TelegramChatBot(
        db_path=db_path,
        openrouter_api_key=openrouter_api_key,
        openrouter_model=openrouter_model,
        important_users=important_users
    )

    # CSS personalizado estilo Freedomia
    custom_css = """
    /* Fondo general oscuro */
    .gradio-container {
        background: linear-gradient(180deg, #1a2332 0%, #0f1419 100%) !important;
        min-height: 100vh;
    }

    /* Header naranja */
    .header-freedomia {
        background: linear-gradient(135deg, #e85d04 0%, #f48c06 100%);
        padding: 20px 30px;
        border-radius: 0 0 20px 20px;
        margin: -20px -20px 20px -20px;
        color: white;
    }

    .header-freedomia h1 {
        color: white !important;
        margin: 0 !important;
        font-size: 1.8em !important;
    }

    .header-freedomia p {
        color: rgba(255,255,255,0.9) !important;
        margin: 5px 0 0 0 !important;
    }

    /* Tarjetas oscuras con bordes redondeados */
    .card-dark {
        background: #1e2a3a !important;
        border-radius: 16px !important;
        padding: 20px !important;
        border: 1px solid #2d3f52 !important;
        margin-bottom: 15px !important;
    }

    /* Input de texto */
    .gradio-container textarea, .gradio-container input[type="text"] {
        background: #1e2a3a !important;
        border: 1px solid #2d3f52 !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        padding: 15px !important;
    }

    .gradio-container textarea:focus, .gradio-container input[type="text"]:focus {
        border-color: #e85d04 !important;
        box-shadow: 0 0 0 2px rgba(232, 93, 4, 0.2) !important;
    }

    /* Labels */
    .gradio-container label {
        color: #a0aec0 !important;
        font-weight: 500 !important;
    }

    /* Botón primario naranja */
    .gradio-container button.primary {
        background: linear-gradient(135deg, #e85d04 0%, #f48c06 100%) !important;
        border: none !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 12px 30px !important;
        transition: all 0.3s ease !important;
    }

    .gradio-container button.primary:hover {
        background: linear-gradient(135deg, #f48c06 0%, #e85d04 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 15px rgba(232, 93, 4, 0.4) !important;
    }

    /* Botón secundario */
    .gradio-container button.secondary {
        background: #1e2a3a !important;
        border: 1px solid #2d3f52 !important;
        border-radius: 12px !important;
        color: #a0aec0 !important;
        padding: 12px 30px !important;
        transition: all 0.3s ease !important;
    }

    .gradio-container button.secondary:hover {
        background: #2d3f52 !important;
        color: white !important;
    }

    /* Área de resultados - forzar color en todos los elementos */
    .gradio-container .prose,
    .gradio-container .prose * {
        color: #e4e4ef !important;
    }

    .gradio-container .prose h2 {
        color: #f48c06 !important;
        border-bottom: 1px solid #2d3f52;
        padding-bottom: 10px;
    }

    .gradio-container .prose h3 {
        color: #ffffff !important;
    }

    .gradio-container .prose strong {
        color: #f48c06 !important;
    }

    .gradio-container .prose p,
    .gradio-container .prose li,
    .gradio-container .prose span {
        color: #e4e4ef !important;
    }

    .gradio-container .prose blockquote,
    .gradio-container .prose blockquote * {
        background: #1e2a3a !important;
        border-left: 4px solid #e85d04 !important;
        border-radius: 0 12px 12px 0 !important;
        padding: 15px !important;
        color: #cbd5e0 !important;
    }

    .gradio-container .prose hr {
        border-color: #2d3f52 !important;
    }

    .gradio-container .prose a {
        color: #f48c06 !important;
    }

    /* Leyenda al final */
    .legend-box {
        background: #1e2a3a;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #2d3f52;
        color: #a0aec0;
    }

    /* Ocultar footer */
    footer {display: none !important;}
    .gradio-container footer {display: none !important;}
    """

    # Crear interfaz Gradio
    with gr.Blocks(
        title="Freedomia - Búsqueda en Chats",
        theme=gr.themes.Base(),
        css=custom_css
    ) as app:
        gr.HTML("""
        <div class="header-freedomia">
            <h1>🔍 Chats de Freedomia en Telegram</h1>
            <p>Solamente chats en Español hasta: 3 de febrero de 2026 - 14:30</p>
        </div>
        """)

        gr.Markdown("""
**Características:**
- ⭐ Los mensajes de usuarios importantes se muestran resaltados
- 🧠 Búsqueda semántica (entiende el significado, no solo palabras exactas)
- 🔤 Búsqueda por keywords (encuentra palabras exactas)
""")

        with gr.Row():
            query_input = gr.Textbox(
                label="Pregunta lo que necesites y recibirás una respuesta basada en los mensajes del historial",
                placeholder="Ej: Google Wallet, tarjetas virtuales, recargas...",
                lines=2
            )

        with gr.Row():
            search_btn = gr.Button("🔍 Buscar", variant="primary")
            clear_btn = gr.Button("🗑️ Limpiar", variant="secondary")

        output = gr.Markdown(label="Resultados")

        # Función que muestra indicador de carga
        def search_with_loading(query):
            return bot.search_and_respond(query)

        # Event handlers con indicador de carga
        search_btn.click(
            fn=lambda: "## ⏳ Buscando...\n\nAnalizando mensajes relevantes...",
            outputs=[output]
        ).then(
            fn=search_with_loading,
            inputs=[query_input],
            outputs=[output]
        )

        query_input.submit(
            fn=lambda: "## ⏳ Buscando...\n\nAnalizando mensajes relevantes...",
            outputs=[output]
        ).then(
            fn=search_with_loading,
            inputs=[query_input],
            outputs=[output]
        )

        clear_btn.click(
            fn=lambda: ("", ""),
            outputs=[query_input, output]
        )

        gr.HTML("""
        <div class="legend-box">
            <strong style="color: #f48c06;">Leyenda:</strong><br>
            🧠 Match semántico · 🔤 Match por keywords · ✨ Match híbrido · ⭐ Usuario importante
        </div>
        """)

    return app


def launch_app(**kwargs):
    """Lanza la aplicación Gradio"""
    app = create_chat_app()
    app.launch(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    launch_app(share=False)
