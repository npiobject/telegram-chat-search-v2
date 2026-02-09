"""
Motor de búsqueda híbrida que combina búsqueda vectorial (semántica) con FTS5 (keywords)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np
import logging

from ..database.schema import Message
from ..database.repositories import MessageRepository, EmbeddingRepository
from .embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Resultado de búsqueda con metadata"""
    message: Message
    score: float
    match_type: str  # 'vector', 'fts', 'hybrid'


class HybridSearch:
    """
    Motor de búsqueda híbrida que combina:
    - Búsqueda vectorial (semántica) usando embeddings
    - Búsqueda FTS5 (keywords exactos)

    Usa Reciprocal Rank Fusion (RRF) para combinar resultados.
    """

    def __init__(
        self,
        db_path: Path,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        self.db_path = db_path
        self.message_repo = MessageRepository(db_path)
        self.embedding_repo = EmbeddingRepository(db_path)
        self.embedding_engine = EmbeddingEngine(model_name)

        # Cache de embeddings en memoria
        self._corpus_ids: Optional[list[int]] = None
        self._corpus_embeddings: Optional[np.ndarray] = None

    def load_embeddings(self) -> None:
        """Carga todos los embeddings en memoria para búsqueda rápida"""
        logger.info("Cargando embeddings en memoria...")
        self._corpus_ids, self._corpus_embeddings = self.embedding_repo.get_all_embeddings()
        logger.info(f"Cargados {len(self._corpus_ids)} embeddings")

    def _ensure_embeddings_loaded(self) -> None:
        """Asegura que los embeddings están cargados"""
        if self._corpus_ids is None or self._corpus_embeddings is None:
            self.load_embeddings()

    def vector_search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        """
        Búsqueda puramente vectorial (semántica).

        Returns:
            Lista de tuplas (message_id, score)
        """
        self._ensure_embeddings_loaded()

        if len(self._corpus_embeddings) == 0:
            logger.warning("No hay embeddings disponibles")
            return []

        results = self.embedding_engine.search(
            query,
            self._corpus_embeddings,
            self._corpus_ids,
            top_k=top_k
        )

        return results

    def fts_search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        """
        Búsqueda Full-Text Search con FTS5.

        Returns:
            Lista de tuplas (message_id, score)
        """
        results = self.message_repo.fts_search(query, limit=top_k)

        # Convertir a formato (id, score)
        return [(msg.id, abs(score)) for msg, score in results]

    def rrf_fusion(
        self,
        vector_results: list[tuple[int, float]],
        fts_results: list[tuple[int, float]],
        k: int = 60  # Constante RRF
    ) -> dict[int, float]:
        """
        Combina resultados usando Reciprocal Rank Fusion (RRF).

        RRF score = sum(1 / (k + rank))

        Args:
            vector_results: Resultados de búsqueda vectorial
            fts_results: Resultados de FTS
            k: Constante de smoothing (default 60)

        Returns:
            Dict de message_id -> combined_score
        """
        combined_scores = {}

        # Agregar scores de búsqueda vectorial
        for rank, (msg_id, _) in enumerate(vector_results):
            if msg_id not in combined_scores:
                combined_scores[msg_id] = 0
            combined_scores[msg_id] += 1 / (k + rank + 1)

        # Agregar scores de FTS
        for rank, (msg_id, _) in enumerate(fts_results):
            if msg_id not in combined_scores:
                combined_scores[msg_id] = 0
            combined_scores[msg_id] += 1 / (k + rank + 1)

        return combined_scores

    def search(
        self,
        query: str,
        top_k: int = 15,
        vector_weight: float = 0.6,
        fts_weight: float = 0.4
    ) -> list[SearchResult]:
        """
        Búsqueda híbrida combinando vectorial y FTS.

        Args:
            query: Texto de búsqueda
            top_k: Número de resultados a devolver
            vector_weight: Peso para resultados vectoriales (0-1)
            fts_weight: Peso para resultados FTS (0-1)

        Returns:
            Lista de SearchResult ordenados por relevancia
        """
        logger.info(f"Búsqueda híbrida: '{query}'")

        # Búsqueda vectorial
        vector_results = self.vector_search(query, top_k=top_k * 2)
        logger.debug(f"Resultados vectoriales: {len(vector_results)}")

        # Búsqueda FTS
        fts_results = self.fts_search(query, top_k=top_k * 2)
        logger.debug(f"Resultados FTS: {len(fts_results)}")

        # Combinar con RRF
        combined_scores = self.rrf_fusion(vector_results, fts_results)

        # Ordenar por score combinado
        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)

        # Obtener mensajes y crear resultados
        results = []
        vector_ids = {msg_id for msg_id, _ in vector_results}
        fts_ids = {msg_id for msg_id, _ in fts_results}

        for msg_id in sorted_ids[:top_k]:
            message = self.message_repo.get_message(msg_id)
            if message:
                # Determinar tipo de match
                in_vector = msg_id in vector_ids
                in_fts = msg_id in fts_ids

                if in_vector and in_fts:
                    match_type = 'hybrid'
                elif in_vector:
                    match_type = 'vector'
                else:
                    match_type = 'fts'

                results.append(SearchResult(
                    message=message,
                    score=combined_scores[msg_id],
                    match_type=match_type
                ))

        logger.info(f"Devolviendo {len(results)} resultados")
        return results

    def semantic_search_only(self, query: str, top_k: int = 15) -> list[SearchResult]:
        """Búsqueda solo semántica (sin FTS)"""
        vector_results = self.vector_search(query, top_k=top_k)

        results = []
        for msg_id, score in vector_results:
            message = self.message_repo.get_message(msg_id)
            if message:
                results.append(SearchResult(
                    message=message,
                    score=score,
                    match_type='vector'
                ))

        return results

    def keyword_search_only(self, query: str, top_k: int = 15) -> list[SearchResult]:
        """Búsqueda solo por keywords (FTS)"""
        fts_results = self.fts_search(query, top_k=top_k)

        results = []
        for msg_id, score in fts_results:
            message = self.message_repo.get_message(msg_id)
            if message:
                results.append(SearchResult(
                    message=message,
                    score=score,
                    match_type='fts'
                ))

        return results


if __name__ == "__main__":
    # Test básico
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    else:
        db_path = Path(__file__).parent.parent.parent / "data" / "telegram_messages.db"

    if not db_path.exists():
        print(f"Base de datos no encontrada: {db_path}")
        sys.exit(1)

    search = HybridSearch(db_path)

    # Test de búsqueda
    query = "inversión"
    print(f"\nBuscando: '{query}'")

    results = search.search(query, top_k=5)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. [{result.match_type}] Score: {result.score:.3f}")
        print(f"   {result.message.sender_name} ({result.message.timestamp}):")
        print(f"   {result.message.text[:150]}...")
