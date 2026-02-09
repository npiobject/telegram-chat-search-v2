"""
Generador de resúmenes usando OpenRouter API
"""

import httpx
import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class OpenRouterSummarizer:
    """Cliente para generar resúmenes usando OpenRouter"""

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3-haiku",
        base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    ):
        """
        Inicializa el cliente de OpenRouter.

        Args:
            api_key: API key de OpenRouter
            model: Modelo a usar (ver https://openrouter.ai/models)
            base_url: URL base de la API
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def summarize_async(
        self,
        query: str,
        messages: list[dict],
        max_messages: int = 15
    ) -> str:
        """
        Genera un resumen de los mensajes encontrados (async).

        Args:
            query: Pregunta del usuario
            messages: Lista de dicts con 'sender_name', 'text', 'timestamp'
            max_messages: Máximo de mensajes a incluir en el contexto

        Returns:
            Resumen generado
        """
        if not self.api_key:
            return "⚠️ No hay API key de OpenRouter configurada. Configura OPENROUTER_API_KEY en el archivo .env"

        # Limitar mensajes
        messages = messages[:max_messages]

        # Formatear contexto
        context_parts = []
        for msg in messages:
            context_parts.append(
                f"**{msg['sender_name']}** ({msg['timestamp']}):\n{msg['text']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""Analiza los siguientes mensajes de un chat de Telegram y responde a la pregunta del usuario de forma concisa y útil.

## Pregunta del usuario
{query}

## Mensajes encontrados
{context}

## Instrucciones
- Responde directamente a la pregunta basándote en los mensajes
- Si hay información contradictoria, menciónalo
- Cita a los usuarios relevantes cuando sea apropiado
- Sé conciso pero completo
- Si no hay información suficiente para responder, indícalo"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://telegram-chat-search.local",
                        "X-Title": "Telegram Chat Search"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.3
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Error de OpenRouter: {response.status_code} - {response.text}")
                    return f"⚠️ Error al generar resumen: {response.status_code}"

                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            logger.error("Timeout al conectar con OpenRouter")
            return "⚠️ Timeout al generar resumen. Intenta de nuevo."
        except Exception as e:
            logger.error(f"Error en OpenRouter: {e}")
            return f"⚠️ Error al generar resumen: {str(e)}"

    def summarize(
        self,
        query: str,
        messages: list[dict],
        max_messages: int = 15
    ) -> str:
        """
        Genera un resumen de los mensajes encontrados (sync).

        Wrapper síncrono de summarize_async.
        """
        return asyncio.run(self.summarize_async(query, messages, max_messages))


class MockSummarizer:
    """Summarizer de prueba que no requiere API"""

    def summarize(self, query: str, messages: list[dict], max_messages: int = 15) -> str:
        """Genera un resumen básico sin usar LLM"""
        if not messages:
            return "No se encontraron mensajes relevantes."

        n_messages = len(messages)
        senders = set(m['sender_name'] for m in messages)

        return f"""📊 **Resumen básico** (sin LLM)

Se encontraron **{n_messages} mensajes** de **{len(senders)} usuarios**.

Para obtener resúmenes inteligentes, configura tu API key de OpenRouter en el archivo `.env`:
```
OPENROUTER_API_KEY=tu-api-key
```

Puedes obtener una API key en: https://openrouter.ai/keys"""


if __name__ == "__main__":
    # Test básico
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if api_key:
        summarizer = OpenRouterSummarizer(api_key)
    else:
        print("No hay API key, usando mock summarizer")
        summarizer = MockSummarizer()

    messages = [
        {"sender_name": "Juan", "text": "Me gusta Python porque es fácil", "timestamp": "2025-01-01 10:00"},
        {"sender_name": "María", "text": "Yo prefiero JavaScript para web", "timestamp": "2025-01-01 10:01"},
        {"sender_name": "Pedro", "text": "Python es mejor para data science", "timestamp": "2025-01-01 10:02"},
    ]

    result = summarizer.summarize("¿Qué lenguaje de programación prefieren?", messages)
    print(result)
