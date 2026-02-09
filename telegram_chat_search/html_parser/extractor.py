"""
Parser de exports HTML de Telegram Desktop
"""

import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Iterator
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedMessage:
    """Mensaje parseado del HTML"""
    id: int
    chat_id: str
    topic_id: str
    sender_name: str
    text: str
    text_clean: str
    timestamp: datetime
    timestamp_utc: datetime
    message_type: str  # 'text', 'photo', 'file', 'sticker', 'service'
    reply_to_message_id: Optional[int] = None
    source_file: str = ""
    has_media: bool = False
    media_type: Optional[str] = None


class HTMLMessageExtractor:
    """Extrae mensajes de archivos HTML exportados por Telegram Desktop"""

    def __init__(self, chat_id: str, topic_id: str):
        self.chat_id = chat_id
        self.topic_id = topic_id

    def parse_file(self, file_path: Path) -> list[ParsedMessage]:
        """Parsea un archivo HTML y extrae todos los mensajes"""
        logger.info(f"Parseando archivo: {file_path.name}")

        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml')

        messages = []
        current_sender = None
        source_file = file_path.name

        # Buscar todos los divs con clase 'message'
        for div in soup.find_all('div', class_='message'):
            try:
                msg = self._parse_message_div(div, current_sender, source_file)
                if msg:
                    # Actualizar el sender actual para mensajes "joined"
                    if not self._is_joined_message(div):
                        current_sender = msg.sender_name
                    messages.append(msg)
            except Exception as e:
                msg_id = div.get('id', 'unknown')
                logger.warning(f"Error parseando mensaje {msg_id}: {e}")
                continue

        logger.info(f"Extraídos {len(messages)} mensajes de {file_path.name}")
        return messages

    def _parse_message_div(self, div, current_sender: Optional[str], source_file: str) -> Optional[ParsedMessage]:
        """Parsea un div de mensaje individual"""

        # Obtener ID del mensaje
        msg_id_str = div.get('id', '')
        if not msg_id_str.startswith('message'):
            return None

        # Extraer ID numérico (puede ser negativo para service messages)
        msg_id_match = re.search(r'message(-?\d+)', msg_id_str)
        if not msg_id_match:
            return None
        msg_id = int(msg_id_match.group(1))

        # Determinar tipo de mensaje
        classes = div.get('class', [])
        is_service = 'service' in classes
        is_joined = 'joined' in classes

        if is_service:
            return self._parse_service_message(div, msg_id, source_file)

        # Mensaje regular
        return self._parse_regular_message(div, msg_id, current_sender, is_joined, source_file)

    def _parse_service_message(self, div, msg_id: int, source_file: str) -> Optional[ParsedMessage]:
        """Parsea un mensaje de servicio (fechas, acciones de sistema)"""
        body = div.find('div', class_='body')
        if not body:
            return None

        text = body.get_text(strip=True)
        if not text:
            return None

        # Intentar extraer timestamp
        timestamp = self._extract_timestamp(div)
        if not timestamp:
            # Los mensajes de fecha no tienen timestamp, usar fecha actual como placeholder
            timestamp = datetime.now()

        return ParsedMessage(
            id=msg_id,
            chat_id=self.chat_id,
            topic_id=self.topic_id,
            sender_name="[Sistema]",
            text=text,
            text_clean=self._clean_text(text),
            timestamp=timestamp,
            timestamp_utc=timestamp,
            message_type='service',
            source_file=source_file,
        )

    def _parse_regular_message(
        self,
        div,
        msg_id: int,
        current_sender: Optional[str],
        is_joined: bool,
        source_file: str
    ) -> Optional[ParsedMessage]:
        """Parsea un mensaje regular de usuario"""

        # Extraer sender
        if is_joined and current_sender:
            sender_name = current_sender
        else:
            from_name_div = div.find('div', class_='from_name')
            if from_name_div:
                sender_name = from_name_div.get_text(strip=True)
            else:
                sender_name = "[Desconocido]"

        # Extraer timestamp
        timestamp = self._extract_timestamp(div)
        if not timestamp:
            logger.warning(f"Mensaje {msg_id} sin timestamp")
            timestamp = datetime.now()

        # Extraer texto
        text_div = div.find('div', class_='text')
        text = ""
        if text_div:
            # Preservar saltos de línea
            for br in text_div.find_all('br'):
                br.replace_with('\n')
            text = text_div.get_text()

        # Detectar tipo de mensaje y media
        message_type = 'text'
        has_media = False
        media_type = None

        # Buscar media
        if div.find('a', class_='photo_wrap'):
            message_type = 'photo'
            has_media = True
            media_type = 'photo'
        elif div.find('a', class_='media_file'):
            message_type = 'file'
            has_media = True
            media_type = 'file'
        elif div.find('div', class_='media_video'):
            message_type = 'video'
            has_media = True
            media_type = 'video'
        elif 'Sticker' in str(div):
            message_type = 'sticker'
            has_media = True
            media_type = 'sticker'

        # Extraer reply_to si existe
        reply_to_id = self._extract_reply_to(div)

        # Si no hay texto pero hay media, usar descripción
        if not text.strip() and has_media:
            text = f"[{media_type.upper()}]"

        return ParsedMessage(
            id=msg_id,
            chat_id=self.chat_id,
            topic_id=self.topic_id,
            sender_name=sender_name,
            text=text,
            text_clean=self._clean_text(text),
            timestamp=timestamp,
            timestamp_utc=timestamp,
            message_type=message_type,
            reply_to_message_id=reply_to_id,
            source_file=source_file,
            has_media=has_media,
            media_type=media_type,
        )

    def _extract_timestamp(self, div) -> Optional[datetime]:
        """Extrae el timestamp del atributo title del div de fecha"""
        date_div = div.find('div', class_='date')
        if not date_div:
            date_div = div.find('div', class_='pull_right')

        if date_div and date_div.get('title'):
            title = date_div['title']
            # Formato: "24.11.2025 22:59:16 UTC+01:00"
            try:
                # Remover timezone para simplificar
                dt_str = re.sub(r'\s*UTC[+-]\d{2}:\d{2}$', '', title)
                return datetime.strptime(dt_str, "%d.%m.%Y %H:%M:%S")
            except ValueError:
                pass

        return None

    def _extract_reply_to(self, div) -> Optional[int]:
        """Extrae el ID del mensaje al que se responde"""
        reply_div = div.find('div', class_='reply_to')
        if not reply_div:
            return None

        # Buscar enlace con formato #go_to_messageXXXX o messages.html#go_to_messageXXXX
        link = reply_div.find('a')
        if link and link.get('href'):
            href = link['href']
            match = re.search(r'go_to_message(\d+)', href)
            if match:
                return int(match.group(1))

        return None

    def _is_joined_message(self, div) -> bool:
        """Determina si es un mensaje continuación (sin userpic)"""
        classes = div.get('class', [])
        return 'joined' in classes

    def _clean_text(self, text: str) -> str:
        """Limpia el texto para búsqueda"""
        if not text:
            return ""

        # Normalizar espacios y saltos de línea
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text


def parse_all_html_files(
    html_dir: Path,
    chat_id: str,
    topic_id: str
) -> list[ParsedMessage]:
    """
    Parsea todos los archivos messages*.html en orden.

    Returns:
        Lista de todos los mensajes parseados
    """
    extractor = HTMLMessageExtractor(chat_id, topic_id)

    # Encontrar todos los archivos messages*.html
    html_files = sorted(html_dir.glob("messages*.html"))

    if not html_files:
        raise FileNotFoundError(f"No se encontraron archivos messages*.html en {html_dir}")

    logger.info(f"Encontrados {len(html_files)} archivos HTML")

    all_messages = []
    for file_path in html_files:
        messages = extractor.parse_file(file_path)
        all_messages.extend(messages)

    # Ordenar por ID de mensaje
    all_messages.sort(key=lambda m: m.id)

    # Eliminar duplicados (pueden existir en límites de archivos)
    seen_ids = set()
    unique_messages = []
    for msg in all_messages:
        if msg.id not in seen_ids:
            seen_ids.add(msg.id)
            unique_messages.append(msg)

    logger.info(f"Total de mensajes únicos: {len(unique_messages)}")
    return unique_messages


if __name__ == "__main__":
    # Test básico
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        html_dir = Path(sys.argv[1])
    else:
        html_dir = Path(__file__).parent.parent.parent / "chats"

    messages = parse_all_html_files(html_dir, "562952938253116", "1478")
    print(f"\nTotal mensajes: {len(messages)}")

    # Mostrar primeros 5 mensajes
    for msg in messages[:5]:
        print(f"\n[{msg.id}] {msg.sender_name} ({msg.timestamp}):")
        print(f"  {msg.text[:100]}...")
