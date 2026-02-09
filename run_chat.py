#!/usr/bin/env python3
"""
Script rápido para lanzar el Chat IA

Uso:
    python run_chat.py
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from telegram_chat_search.chat_interface.app import launch_app

if __name__ == "__main__":
    launch_app(share=False)
