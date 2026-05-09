import asyncio
from config import get_settings
from pinecone.pinecone import Pinecone

_pc: Pinecone | None = None
_HOSTED_INFERENCE_BATCH_SIZE = 96


def _get_pinecone() -> Pinecone:
    """Initialize and return a Pinecone client for hosted inference."""
    global _pc
    if _pc is None:
        settings = get_settings()
        _pc = Pinecone(api_key=settings.pinecone_api_key)
    return _pc


def _values_from_embedding(item) -> list[float]:
    """Extract vector values from Pinecone SDK response shapes."""
    if isinstance(item, dict):
        return item.get("values", [])
    return getattr(item, "values", [])


def _embed_sync(texts: list[str], input_type: str) -> list[list[float]]:
    """Generate embeddings via Pinecone Inference."""
    settings = get_settings()
    pc = _get_pinecone()
    response = pc.inference.embed(
        model=settings.embedding_model_name,
        inputs=texts,
        parameters={
            "input_type": input_type,
            "truncate": "END",
            "dimension": settings.pinecone_dimension,
        },
    )
    if isinstance(response, dict):
        data = response.get("data", response)
    else:
        data = getattr(response, "data", response)
    return [_values_from_embedding(item) for item in data]


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    Runs Pinecone hosted inference in a thread pool to avoid blocking the
    async event loop.
    """
    if not texts:
        return []

    embeddings: list[list[float]] = []
    for i in range(0, len(texts), _HOSTED_INFERENCE_BATCH_SIZE):
        batch = texts[i:i + _HOSTED_INFERENCE_BATCH_SIZE]
        embeddings.extend(await asyncio.to_thread(_embed_sync, batch, "passage"))
    return embeddings


async def get_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    embeddings = await asyncio.to_thread(_embed_sync, [text], "query")
    return embeddings[0] if embeddings else []


def get_dimension() -> int:
    """Return the embedding dimension for the configured model."""
    settings = get_settings()
    return settings.pinecone_dimension
