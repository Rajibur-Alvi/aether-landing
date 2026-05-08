import asyncio
import numpy as np
from fastembed import TextEmbedding
from config import get_settings

_model: TextEmbedding | None = None


def _load_model() -> TextEmbedding:
    """Load the embedding model (singleton)."""
    global _model
    if _model is None:
        settings = get_settings()
        _model = TextEmbedding(settings.embedding_model_name)
    return _model


def _embed_sync(texts: list[str]) -> list[np.ndarray]:
    """Synchronous embedding generation."""
    model = _load_model()
    return list(model.embed(texts))


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    Returns list of float lists (dimension 384 for all-MiniLM-L6-v2).
    Runs in a thread to avoid blocking the event loop.
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
