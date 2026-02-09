"""
Motor de embeddings usando sentence-transformers
"""

import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Lazy loading para evitar cargar el modelo hasta que se necesite
_model = None
_model_name = None


def get_model(model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
    """
    Obtiene el modelo de embeddings (lazy loading).

    Args:
        model_name: Nombre del modelo de sentence-transformers
    """
    global _model, _model_name

    if _model is None or _model_name != model_name:
        logger.info(f"Cargando modelo de embeddings: {model_name}")
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(model_name)
            _model_name = model_name
            logger.info("Modelo cargado correctamente")
        except ImportError:
            raise ImportError(
                "sentence-transformers no está instalado. "
                "Ejecuta: pip install sentence-transformers"
            )

    return _model


class EmbeddingEngine:
    """Motor para generar y buscar embeddings semánticos"""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Inicializa el motor de embeddings.

        Args:
            model_name: Modelo de sentence-transformers a usar.
                        'paraphrase-multilingual-MiniLM-L12-v2' es bueno para español.
        """
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy loading del modelo"""
        if self._model is None:
            self._model = get_model(self.model_name)
        return self._model

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Genera embeddings para una lista de textos.

        Args:
            texts: Lista de textos a codificar
            batch_size: Tamaño del batch para procesamiento
            show_progress: Mostrar barra de progreso

        Returns:
            Matriz numpy de embeddings (n_texts, embedding_dim)
        """
        if not texts:
            return np.array([])

        logger.info(f"Generando embeddings para {len(texts)} textos...")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        logger.info(f"Embeddings generados: shape {embeddings.shape}")
        return embeddings

    def encode_query(self, query: str) -> np.ndarray:
        """
        Genera embedding para una query de búsqueda.

        Args:
            query: Texto de la query

        Returns:
            Vector de embedding (embedding_dim,)
        """
        return self.model.encode([query], convert_to_numpy=True)[0]

    def cosine_similarity(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calcula similitud coseno entre query y corpus.

        Args:
            query_embedding: Embedding de la query (embedding_dim,)
            corpus_embeddings: Matriz de embeddings del corpus (n, embedding_dim)

        Returns:
            Array de scores de similitud (n,)
        """
        # Normalizar
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        corpus_norm = corpus_embeddings / np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)

        # Similitud coseno
        similarities = np.dot(corpus_norm, query_norm)

        return similarities

    def search(
        self,
        query: str,
        corpus_embeddings: np.ndarray,
        corpus_ids: list[int],
        top_k: int = 10
    ) -> list[tuple[int, float]]:
        """
        Busca los documentos más similares a la query.

        Args:
            query: Texto de búsqueda
            corpus_embeddings: Matriz de embeddings del corpus
            corpus_ids: IDs correspondientes a cada embedding
            top_k: Número de resultados a devolver

        Returns:
            Lista de tuplas (id, score) ordenados por similitud descendente
        """
        if len(corpus_embeddings) == 0:
            return []

        # Generar embedding de la query
        query_embedding = self.encode_query(query)

        # Calcular similitudes
        similarities = self.cosine_similarity(query_embedding, corpus_embeddings)

        # Obtener top_k índices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Devolver (id, score)
        results = [
            (corpus_ids[idx], float(similarities[idx]))
            for idx in top_indices
        ]

        return results


if __name__ == "__main__":
    # Test básico
    logging.basicConfig(level=logging.INFO)

    engine = EmbeddingEngine()

    # Test de encoding
    texts = [
        "Hola, ¿cómo estás?",
        "Me gusta programar en Python",
        "El tiempo está muy bueno hoy",
        "Python es un lenguaje de programación"
    ]

    embeddings = engine.encode(texts)
    print(f"Shape de embeddings: {embeddings.shape}")

    # Test de búsqueda
    query = "programación"
    results = engine.search(query, embeddings, list(range(len(texts))), top_k=2)

    print(f"\nBúsqueda: '{query}'")
    for idx, score in results:
        print(f"  [{score:.3f}] {texts[idx]}")
