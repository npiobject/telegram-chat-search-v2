"""
Punto de entrada para Railway / Hugging Face Spaces
"""
import os
import logging

logging.basicConfig(level=logging.INFO)

# Importar y lanzar la aplicación
from telegram_chat_search.chat_interface.app import create_chat_app

app = create_chat_app()

# Lanzar la aplicación en el puerto especificado por Railway o Hugging Face Spaces
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port)
