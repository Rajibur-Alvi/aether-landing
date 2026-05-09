import math
import time
from groq import AsyncGroq
from config import get_settings
from typing import AsyncGenerator

_async_client: AsyncGroq | None = None


def _get_async_client() -> AsyncGroq:
    global _async_client
    if _async_client is None:
        settings = get_settings()
        _async_client = AsyncGroq(api_key=settings.groq_api_key)
    return _async_client


def calculate_entropy(text: str) -> float:
    """
    Compute Shannon entropy of the response text, normalised to [0, 1].
    Higher score = more diverse vocabulary = higher information density.
    This is a real measure, not a proxy for GPU speed.
    """
    words = text.lower().split()
    if not words:
        return 0.0
    total = len(words)
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    raw_entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in freq.values()
    )
    # Typical English text has a word-level entropy of ~6-9 bits.
    # We normalise against 8.0 so a rich document scores close to 1.0.
    return round(min(1.0, raw_entropy / 8.0), 3)


def _build_context_block(chunks: list[dict]) -> str:
    block = ""
    for i, chunk in enumerate(chunks):
        block += (
            f"\n--- Source [{i + 1}] "
            f"(doc: {chunk['document_id']}, relevance: {chunk['score']:.3f}) ---\n"
            f"{chunk['text']}\n"
        )
    return block


async def generate_rag_response(
    query: str,
    context_chunks: list[dict],
    model: str = "llama-3.1-8b-instant",
    temperature: float = 0.1,
    max_tokens: int = 1024,
    system_prompt: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Build a RAG prompt from context chunks and query Groq.
    Returns dict with content, latency_ms, tokens_per_second, entropy_score, usage.

    Temperature defaults to 0.1 — precise, factual answers that stay
    close to the source material (correct for RAG use case).
    """
    context_block = _build_context_block(context_chunks)

    if system_prompt is None:
        system_prompt = (
            "You are Entropy AI — a precise, analytical assistant. "
            "Answer questions using ONLY the provided context. "
            "If the context does not contain the answer, say so clearly — do NOT speculate. "
            "Cite which source [number] supports each claim. "
            "Be concise and direct.\n\n"
            f"CONTEXT:\n{context_block}"
        )

    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

    messages.append({"role": "user", "content": query})

    client = _get_async_client()
    start = time.perf_counter()

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=0.9,
    )

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    choice = response.choices[0]
    content = choice.message.content or ""

    total_tokens = response.usage.total_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0
    tps = round(completion_tokens / (elapsed_ms / 1000), 1) if elapsed_ms > 0 else 0

    # Real Shannon entropy of the generated answer
    entropy_score = calculate_entropy(content)

    return {
        "content": content,
        "latency_ms": elapsed_ms,
        "tokens_per_second": tps,
        "total_tokens": total_tokens,
        "completion_tokens": completion_tokens,
        "entropy_score": entropy_score,
        "model": model,
        "finish_reason": choice.finish_reason,
    }


async def stream_rag_response(
    query: str,
    context_chunks: list[dict],
    model: str = "llama-3.1-8b-instant",
    temperature: float = 0.1,
    max_tokens: int = 1024,
    system_prompt: str | None = None,
    conversation_history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Streaming RAG response — yields token strings."""
    context_block = _build_context_block(context_chunks)

    if system_prompt is None:
        system_prompt = (
            "You are Entropy AI — a precise, analytical assistant. "
            "Answer questions using ONLY the provided context. "
            "If the context does not contain the answer, say so clearly — do NOT speculate. "
            "Cite which source [number] supports each claim. "
            "Be concise and direct.\n\n"
            f"CONTEXT:\n{context_block}"
        )

    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })
    messages.append({"role": "user", "content": query})

    client = _get_async_client()
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=0.9,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
