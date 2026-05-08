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


async def generate_rag_response(
    query: str,
    context_chunks: list[dict],
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    system_prompt: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Build a RAG prompt from context chunks and query Groq.
    Returns dict with content, latency_ms, tokens_per_second, usage stats.
    """
    context_block = ""
    for i, chunk in enumerate(context_chunks):
        context_block += f"\n--- Source [{i+1}] (doc: {chunk['document_id']}, score: {chunk['score']:.3f}) ---\n{chunk['text']}\n"

    if system_prompt is None:
        system_prompt = (
            "You are the Entropy AI — a hyper-intelligent, precise, and slightly poetic assistant. "
            "You answer questions using ONLY the provided context data. "
            "If the context does not contain the answer, say so clearly. "
            "Cite which source [number] you used for each claim. "
            "Be concise but thorough. Embrace complexity.\n\n"
            f"CONTEXT DATA:\n{context_block}"
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
    content = choice.message.content

    total_tokens = response.usage.total_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0
    tps = round(completion_tokens / (elapsed_ms / 1000), 1) if elapsed_ms > 0 else 0

    entropy_score = round(min(1.0, len(context_chunks) * 0.15 + (tps / 200)), 3)

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
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    system_prompt: str | None = None,
    conversation_history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Streaming RAG response — yields SSE chunks.
    """
    context_block = ""
    for i, chunk in enumerate(context_chunks):
        context_block += f"\n--- Source [{i+1}] (doc: {chunk['document_id']}, score: {chunk['score']:.3f}) ---\n{chunk['text']}\n"

    if system_prompt is None:
        system_prompt = (
            "You are the Entropy AI — a hyper-intelligent, precise, and slightly poetic assistant. "
            "You answer questions using ONLY the provided context data. "
            "If the context does not contain the answer, say so clearly. "
            "Cite which source [number] you used for each claim. "
            "Be concise but thorough. Embrace complexity.\n\n"
            f"CONTEXT DATA:\n{context_block}"
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
