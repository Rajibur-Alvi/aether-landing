import asyncio
from pinecone.pinecone import Pinecone
from config import get_settings
from services.embedding_service import get_embeddings, get_single_embedding

_pc: Pinecone | None = None
_index = None

# Minimum cosine similarity score for a chunk to be used as context.
# Chunks below this threshold are discarded — they are not relevant enough
# to the query and would only add noise to the LLM prompt.
SCORE_THRESHOLD = 0.65


def _get_pinecone():
    """Initialize and return Pinecone client (singleton)."""
    global _pc
    if _pc is None:
        settings = get_settings()
        _pc = Pinecone(api_key=settings.pinecone_api_key)
    return _pc


def _get_index():
    """Get the Pinecone index (singleton)."""
    global _index
    if _index is None:
        settings = get_settings()
        pc = _get_pinecone()
        _index = pc.Index(settings.pinecone_index_name)
    return _index


async def upsert_document_chunks(
    user_id: str,
    document_id: str,
    chunks: list[str],
) -> int:
    """
    Embed chunks and upsert them into Pinecone.
    Returns the number of chunks upserted.
    """
    if not chunks:
        return 0

    embeddings = await get_embeddings(chunks)

    vectors = []
    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        vector_id = f"{document_id}_chunk_{i}"
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "user_id": user_id,
                "document_id": document_id,
                "chunk_index": i,
                "chunk_text": chunk_text,
            },
        })

    index = _get_index()
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i: i + batch_size]
        await asyncio.to_thread(index.upsert, vectors=batch)

    return len(vectors)


async def search_similar_chunks(
    query: str,
    user_id: str,
    top_k: int = 5,
    document_id: str | None = None,
    score_threshold: float = SCORE_THRESHOLD,
) -> list[dict]:
    """
    Embed the query and search Pinecone for similar chunks.
    Only returns chunks whose cosine similarity meets score_threshold.
    Returns list of dicts: {text, score, document_id, chunk_index}.
    """
    query_embedding = await get_single_embedding(query)

    filter_dict: dict = {"user_id": user_id}
    if document_id:
        filter_dict["document_id"] = document_id

    index = _get_index()
    # Request more than top_k so we have candidates to filter by threshold
    raw_top_k = min(top_k * 2, 20)
    results = await asyncio.to_thread(
        index.query,
        vector=query_embedding,
        top_k=raw_top_k,
        filter=filter_dict,
        include_metadata=True,
    )

    matches = []
    raw_matches = []
    for match in results.get("matches", []):
        score = match.get("score", 0.0)
        meta = match.get("metadata", {})
        candidate = {
            "text": meta.get("chunk_text", ""),
            "document_id": meta.get("document_id", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "score": score,
        }
        raw_matches.append(candidate)
        # Skip chunks that are not similar enough to the query
        if score < score_threshold:
            continue
        matches.append(candidate)
        if len(matches) >= top_k:
            break

    if not matches and document_id:
        return raw_matches[:top_k]

    return matches


async def delete_document_chunks(document_id: str) -> int:
    """Delete all chunks for a given document from Pinecone."""
    index = _get_index()
    await asyncio.to_thread(
        index.delete,
        filter={"document_id": document_id},
    )
    return 1


async def get_index_stats() -> dict:
    """Get Pinecone index stats for the health endpoint."""
    try:
        index = _get_index()
        stats = await asyncio.to_thread(index.describe_index_stats)
        return {
            "total_vector_count": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension", 0),
        }
    except Exception:
        return {"total_vector_count": 0, "dimension": 0, "error": "unreachable"}
