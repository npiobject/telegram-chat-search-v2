"""
CLI principal del Telegram Chat Search
"""

import click
import logging
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import config

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@click.group()
def cli():
    """Telegram Chat Search - Chat IA para búsqueda en mensajes de Telegram"""
    pass


@cli.command('import-html')
@click.option(
    '--input', '-i', 'input_path',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Directorio con archivos HTML exportados de Telegram'
)
@click.option(
    '--output', '-o', 'output_path',
    type=click.Path(path_type=Path),
    default=None,
    help='Ruta para la base de datos SQLite'
)
@click.option(
    '--chat-id',
    default="562952938253116",
    help='ID del chat'
)
@click.option(
    '--topic-id',
    default="1478",
    help='ID del topic (para supergrupos con topics)'
)
def import_html(input_path, output_path, chat_id, topic_id):
    """Importa mensajes desde archivos HTML de Telegram Desktop"""
    from .html_parser import parse_all_html_files
    from .database.schema import init_database, Message
    from .database.repositories import MessageRepository, ImportantUserRepository

    input_path = input_path or config.html_export_path
    output_path = output_path or config.database_path

    console.print(f"[bold blue]Importando mensajes desde:[/] {input_path}")
    console.print(f"[bold blue]Base de datos:[/] {output_path}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Parsear HTML
        task = progress.add_task("Parseando archivos HTML...", total=None)
        messages = parse_all_html_files(input_path, chat_id, topic_id)
        progress.update(task, description=f"Parseados {len(messages)} mensajes")

        # Inicializar base de datos
        progress.update(task, description="Inicializando base de datos...")
        init_database(output_path)

        # Convertir a objetos Message
        db_messages = []
        for msg in messages:
            db_messages.append(Message(
                id=msg.id,
                chat_id=msg.chat_id,
                topic_id=msg.topic_id,
                sender_name=msg.sender_name,
                text=msg.text,
                text_clean=msg.text_clean,
                timestamp=msg.timestamp,
                timestamp_utc=msg.timestamp_utc,
                message_type=msg.message_type,
                reply_to_message_id=msg.reply_to_message_id,
                source='html_export',
                source_file=msg.source_file,
            ))

        # Insertar mensajes
        progress.update(task, description="Insertando mensajes en la base de datos...")
        repo = MessageRepository(output_path)
        count = repo.bulk_insert(db_messages)

        # Añadir usuarios importantes por defecto
        progress.update(task, description="Configurando usuarios importantes...")
        user_repo = ImportantUserRepository(output_path)
        for user in config.important_users:
            user_repo.add_user(user, role="admin")

        # Marcar mensajes de usuarios importantes
        marked = user_repo.mark_important_messages()

        progress.update(task, description="[green]✓ Importación completada")

    console.print(f"\n[green]✓[/] Importados [bold]{count}[/] mensajes")
    console.print(f"[green]✓[/] Marcados [bold]{marked}[/] mensajes de usuarios importantes")
    console.print(f"\n[dim]Base de datos guardada en: {output_path}[/]")


@cli.command('generate-embeddings')
@click.option(
    '--database', '-d',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Ruta a la base de datos SQLite'
)
@click.option(
    '--batch-size',
    default=32,
    help='Tamaño del batch para generar embeddings'
)
def generate_embeddings(database, batch_size):
    """Genera embeddings para búsqueda semántica"""
    from .database.repositories import MessageRepository, EmbeddingRepository
    from .search.embeddings import EmbeddingEngine

    database = database or config.database_path

    console.print(f"[bold blue]Generando embeddings desde:[/] {database}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Cargando mensajes...", total=None)

        # Obtener mensajes con texto
        msg_repo = MessageRepository(database)
        messages = msg_repo.get_messages_with_text()
        progress.update(task, description=f"Cargados {len(messages)} mensajes con texto")

        if not messages:
            console.print("[yellow]No hay mensajes para procesar[/]")
            return

        # Preparar textos
        texts = [m.text_clean for m in messages]
        message_ids = [m.id for m in messages]

        # Generar embeddings
        progress.update(task, description="Generando embeddings (esto puede tardar)...")
        engine = EmbeddingEngine(config.embedding_model)
        embeddings = engine.encode(texts, batch_size=batch_size, show_progress=True)

        # Guardar en base de datos
        progress.update(task, description="Guardando embeddings...")
        emb_repo = EmbeddingRepository(database)
        emb_repo.bulk_save_embeddings(message_ids, embeddings, config.embedding_model)

        progress.update(task, description="[green]✓ Embeddings generados")

    console.print(f"\n[green]✓[/] Generados [bold]{len(embeddings)}[/] embeddings")
    console.print(f"[dim]Modelo: {config.embedding_model}[/]")


@cli.command('add-important-user')
@click.option('--name', '-n', required=True, help='Nombre del usuario (como aparece en el chat)')
@click.option('--role', '-r', default='important', help='Rol del usuario (admin, moderator, expert, etc.)')
@click.option(
    '--database', '-d',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Ruta a la base de datos SQLite'
)
def add_important_user(name, role, database):
    """Añade un usuario a la lista de usuarios importantes"""
    from .database.repositories import ImportantUserRepository

    database = database or config.database_path

    user_repo = ImportantUserRepository(database)
    user_repo.add_user(name, role)

    # Marcar sus mensajes
    marked = user_repo.mark_important_messages()

    console.print(f"[green]✓[/] Usuario '[bold]{name}[/]' añadido como {role}")
    console.print(f"[green]✓[/] {marked} mensajes marcados como importantes")


@cli.command('chat')
@click.option(
    '--database', '-d',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Ruta a la base de datos SQLite'
)
@click.option('--port', default=7860, help='Puerto para la interfaz web')
@click.option('--share/--no-share', default=False, help='Crear enlace público compartible')
def chat(database, port, share):
    """Lanza la interfaz de Chat IA"""
    from .chat_interface.app import create_chat_app

    database = database or config.database_path

    console.print(f"[bold blue]Iniciando Chat IA...[/]")
    console.print(f"[dim]Base de datos: {database}[/]")

    app = create_chat_app(db_path=database)

    console.print(f"\n[green]Abriendo en:[/] http://localhost:{port}")
    if share:
        console.print("[yellow]Creando enlace público...[/]")

    app.launch(server_port=port, share=share)


@cli.command('stats')
@click.option(
    '--database', '-d',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Ruta a la base de datos SQLite'
)
def stats(database):
    """Muestra estadísticas de la base de datos"""
    from .database.repositories import MessageRepository, EmbeddingRepository, ImportantUserRepository

    database = database or config.database_path

    msg_repo = MessageRepository(database)
    emb_repo = EmbeddingRepository(database)
    user_repo = ImportantUserRepository(database)

    n_messages = msg_repo.count_messages()
    n_embeddings = emb_repo.count_embeddings()
    important_users = user_repo.get_all_users()

    console.print("\n[bold]📊 Estadísticas de la base de datos[/]\n")
    console.print(f"  📨 Mensajes: [bold]{n_messages}[/]")
    console.print(f"  🧠 Embeddings: [bold]{n_embeddings}[/]")
    console.print(f"  ⭐ Usuarios importantes: [bold]{len(important_users)}[/]")

    if important_users:
        console.print("\n  [dim]Usuarios importantes:[/]")
        for user in important_users:
            console.print(f"    - {user}")

    if n_embeddings < n_messages:
        console.print(f"\n[yellow]⚠ Faltan {n_messages - n_embeddings} embeddings. Ejecuta:[/]")
        console.print("[dim]  python -m telegram_chat_search generate-embeddings[/]")


@cli.command('search')
@click.argument('query')
@click.option(
    '--database', '-d',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Ruta a la base de datos SQLite'
)
@click.option('--top-k', '-k', default=10, help='Número de resultados')
def search(query, database, top_k):
    """Búsqueda rápida desde línea de comandos"""
    from .search.hybrid_search import HybridSearch
    from .chat_interface.deep_links import generate_telegram_link

    database = database or config.database_path

    search_engine = HybridSearch(database)

    console.print(f"\n[bold]🔍 Buscando:[/] {query}\n")

    results = search_engine.search(query, top_k=top_k)

    for i, result in enumerate(results, 1):
        msg = result.message
        link = generate_telegram_link(msg.chat_id, msg.id)

        # Icono de match
        match_icon = {'vector': '🧠', 'fts': '🔤', 'hybrid': '✨'}.get(result.match_type, '')

        # Texto truncado
        text = (msg.text or "")[:150]
        if len(msg.text or "") > 150:
            text += "..."

        console.print(f"[bold]{i}.[/] {match_icon} [dim]{msg.sender_name}[/] ({str(msg.timestamp)[:10]})")
        console.print(f"   {text}")
        console.print(f"   [blue underline]{link}[/]")
        console.print()


if __name__ == '__main__':
    cli()
