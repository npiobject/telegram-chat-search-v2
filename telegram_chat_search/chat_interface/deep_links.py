"""
Generador de deep links a mensajes de Telegram

Formatos soportados:
- tg://privatepost?channel=X&post=Y  -> Abre directamente la app de Telegram
- https://t.me/c/X/Y                 -> Abre en Telegram Web (requiere sesión)
"""

from dataclasses import dataclass


@dataclass
class TelegramLinks:
    """Contiene ambos formatos de enlace a Telegram"""
    app: str    # tg://privatepost?channel=X&post=Y
    web: str    # https://t.me/c/X/Y


def _clean_chat_id(chat_id: str) -> str:
    """Limpia el chat_id eliminando prefijos"""
    chat_id_str = str(chat_id)

    if chat_id_str.startswith('-100'):
        return chat_id_str[4:]
    elif chat_id_str.startswith('-'):
        return chat_id_str[1:]
    else:
        return chat_id_str


def generate_telegram_links(chat_id: str, message_id: int, topic_id: str = None) -> TelegramLinks:
    """
    Genera ambos formatos de enlace a un mensaje de Telegram.

    Args:
        chat_id: ID del chat o username (ej: "Freedomia_io")
        message_id: ID del mensaje
        topic_id: ID del topic (opcional)

    Returns:
        TelegramLinks con ambos formatos (app y web)
    """
    # Si es un username (no empieza con - ni es solo números)
    if not chat_id.startswith('-') and not chat_id.isdigit():
        # Grupo público con username
        if topic_id:
            return TelegramLinks(
                app=f"tg://resolve?domain={chat_id}&post={message_id}&thread={topic_id}",
                web=f"https://t.me/{chat_id}/{topic_id}/{message_id}"
            )
        else:
            return TelegramLinks(
                app=f"tg://resolve?domain={chat_id}&post={message_id}",
                web=f"https://t.me/{chat_id}/{message_id}"
            )

    # Chat privado con ID numérico
    channel_id = _clean_chat_id(chat_id)

    if topic_id:
        return TelegramLinks(
            app=f"tg://privatepost?channel={channel_id}&post={message_id}&thread={topic_id}",
            web=f"https://t.me/c/{channel_id}/{topic_id}/{message_id}"
        )

    return TelegramLinks(
        app=f"tg://privatepost?channel={channel_id}&post={message_id}",
        web=f"https://t.me/c/{channel_id}/{message_id}"
    )


def generate_telegram_link(chat_id: str, message_id: int) -> str:
    """
    Genera un enlace directo a un mensaje en Telegram (formato web).

    DEPRECATED: Usar generate_telegram_links() para obtener ambos formatos.

    Args:
        chat_id: ID del chat (puede incluir prefijo -100)
        message_id: ID del mensaje

    Returns:
        URL de enlace directo a Telegram (formato web)
    """
    channel_id = _clean_chat_id(chat_id)
    return f"https://t.me/c/{channel_id}/{message_id}"


def generate_telegram_link_with_topic(chat_id: str, topic_id: str, message_id: int) -> TelegramLinks:
    """
    Genera ambos formatos de enlace a un mensaje en un topic de Telegram.

    Args:
        chat_id: ID del chat
        topic_id: ID del topic
        message_id: ID del mensaje

    Returns:
        TelegramLinks con ambos formatos
    """
    channel_id = _clean_chat_id(chat_id)

    return TelegramLinks(
        app=f"tg://privatepost?channel={channel_id}&post={message_id}&thread={topic_id}",
        web=f"https://t.me/c/{channel_id}/{topic_id}/{message_id}"
    )


def format_links_markdown(links: TelegramLinks) -> str:
    """
    Formatea los enlaces en HTML para mostrar en la interfaz.

    Args:
        links: TelegramLinks con ambos formatos

    Returns:
        String HTML con ambos enlaces
    """
    #return f'📱 <a href="{links.app}" target="_blank">Abrir en App</a> | 🌐 <a href="{links.web}" target="_blank">Ver en Web</a>'
    return f''

if __name__ == "__main__":
    # Test
    chat_id = "562952938253116"
    topic_id = "1478"
    message_id = 1479

"""     links = generate_telegram_links(chat_id, message_id)
    
    print(f"App link: {links.app}")
    print(f"Web link: {links.web}")
    print(f"Markdown: {format_links_markdown(links)}")

    print("\n--- Con topic ---")
    links_topic = generate_telegram_link_with_topic(chat_id, topic_id, message_id)
    print(f"App link: {links_topic.app}")
    print(f"Web link: {links_topic.web}")

    # Test con prefijo -100
    print("\n--- Con prefijo -100 ---")
    chat_id_prefix = "-100562952938253116"
    links_prefix = generate_telegram_links(chat_id_prefix, message_id)
    print(f"App link: {links_prefix.app}")
    print(f"Web link: {links_prefix.web}") """
