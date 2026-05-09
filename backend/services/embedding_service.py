import asyncio
import numpy as np
from fastembed import TextEmbedding
from config import get_settings

_model: TextEmbedding | None = None


def _load_model() -> TextEmbedding:
    """
    Load the embedding model (singleton).
    BAAI/bge-base-en-v1.5 → 768-dimensional embeddings.
    Significantly outperforms all-MiniLM-L6-v2 on retrieval benchmarks.

    IMPORTANT: If you change this model, you MUST delete and recreate your
    Pinecone index with the matching dimension (768 for bge-base-en-v1.5).
    """
    global _model
    if _model is None:
        settings = get_settings()
        _model = TextEmbedding(settings.embedding_model_name)
    return _model


def _embed_sync(texts: list[str]) -> list[np.ndarray]:
    """Synchronous embedding generation (called in a thread pool)."""
    model = _load_model()
    return list(model.embed(texts))


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    Runs in a thread pool to avoid blocking the async event loop.
    Returns list of float lists (768-dim for BAAI/bge-base-en-v1.5).
    """
    if not texts:
        return []
    results = await asyncio.to_thread(_embed_sync, texts)
    return [arr.tolist() for arr in results]


async def get_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    embeddings = await get_embeddings([text])
    return embeddings[0] if embeddings else []


def get_dimension() -> int:
    """Return the embedding dimension for the configured model."""
    settings = get_settings()
    return settings.pinecone_dimension
