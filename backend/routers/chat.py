import json
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from models.schemas import ChatRequest, ChatMessageResponse, ChatMeta, ChatSource
from middleware.auth import get_current_user
from services.pinecone_service import search_similar_chunks
from services.groq_service import generate_rag_response, stream_rag_response
from services.supabase_service import get_supabase
from config import get_settings

router = APIRouter(prefix="/chat", tags=["Chat"])

MODEL_MAP = {
    "fast": "llama-3.1-8b-instant",
    "balanced": "llama-3.3-70b-versatile",
    "thorough": "llama-3.3-70b-versatile",
}


async def _get_user_settings(user_id: str) -> dict:
    """Fetch user's command center settings from Supabase."""
    try:
        sb = get_supabase()
        result = sb.table("command_center_settings") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()
        if result.data:
            return result.data[0]
    except Exception:
        pass
    return {}


@router.post("/ask", response_model=ChatMessageResponse)
async def ask_question(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    """RAG endpoint: query → search Pinecone → build context → Groq → answer."""
    settings = get_settings()
    start = time.perf_counter()

    user_settings = await _get_user_settings(user_id)

    model_name = MODEL_MAP.get(
        user_settings.get("inference_speed", "balanced"),
        "llama-3.3-70b-versatile",
    )
    if request.model:
        model_name = MODEL_MAP.get(request.model.value, model_name)

    temperature = user_settings.get("temperature", request.temperature)
    max_tokens = user_settings.get("max_tokens", request.max_tokens)
    system_prompt = user_settings.get("system_prompt")
    top_k = user_settings.get("retrieval_depth", settings.default_top_k)

    # Step 1: Search Pinecone
    try:
        chunks = await search_similar_chunks(
            query=request.message,
            user_id=user_id,
            top_k=top_k,
            document_id=request.document_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector search failed: {str(e)}")

    data_density = len(chunks)

    # Step 2: Generate via Groq
    try:
        result = await generate_rag_response(
            query=request.message,
            context_chunks=chunks,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Groq inference failed: {str(e)}")

    total_latency = int((time.perf_counter() - start) * 1000)

    # Step 3: Save to conversation history
    conversation_id = request.conversation_id or str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    try:
        sb = get_supabase()
        sb.table("conversations").upsert({
            "id": conversation_id,
            "user_id": user_id,
            "title": request.message[:80],
        }, on_conflict="id").execute()

        sb.table("messages").insert({
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": "user",
            "content": request.message,
        }).execute()

        sb.table("messages").insert({
            "id": message_id,
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": result["content"],
            "meta": {
                "entropy_score": result["entropy_score"],
                "latency_ms": total_latency,
                "tokens_per_second": result["tokens_per_second"],
                "data_density": data_density,
                "model": model_name,
                "sources": [
                    {
                        "document_id": c["document_id"],
                        "chunk_index": c["chunk_index"],
                        "score": c["score"],
                    }
                    for c in chunks
                ],
            },
        }).execute()
    except Exception:
        pass

    # Step 4: Log dark data event
    try:
        sb = get_supabase()
        sb.table("dark_data_events").insert({
            "user_id": user_id,
            "event_type": "inference_complete",
            "event_data": {
                "model": model_name,
                "latency_ms": total_latency,
                "tps": result["tokens_per_second"],
                "entropy_score": result["entropy_score"],
                "data_density": data_density,
            },
        }).execute()
    except Exception:
        pass

    sources = [
        ChatSource(
            text=c["text"][:200],
            document_id=c["document_id"],
            chunk_index=c["chunk_index"],
            score=c["score"],
        )
        for c in chunks
    ]

    return ChatMessageResponse(
        id=message_id,
        role="assistant",
        content=result["content"],
        meta=ChatMeta(
            entropy_score=result["entropy_score"],
            latency_ms=total_latency,
            tokens_per_second=result["tokens_per_second"],
            data_density=data_density,
            sources=sources,
        ),
        created_at=__import__("datetime").datetime.utcnow(),
    )


@router.post("/ask/stream")
async def ask_question_stream(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    """Streaming RAG endpoint — returns SSE events with partial content."""
    settings = get_settings()
    user_settings = await _get_user_settings(user_id)

    model_name = MODEL_MAP.get(
        user_settings.get("inference_speed", "balanced"),
        "llama-3.3-70b-versatile",
    )
    if request.model:
        model_name = MODEL_MAP.get(request.model.value, model_name)

    temperature = user_settings.get("temperature", request.temperature)
    max_tokens = user_settings.get("max_tokens", request.max_tokens)
    system_prompt = user_settings.get("system_prompt")
    top_k = user_settings.get("retrieval_depth", settings.default_top_k)

    try:
        chunks = await search_similar_chunks(
            query=request.message,
            user_id=user_id,
            top_k=top_k,
            document_id=request.document_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector search failed: {str(e)}")

    async def event_generator():
        meta = {
            "data_density": len(chunks),
            "model": model_name,
            "sources": [
                {"document_id": c["document_id"], "score": c["score"]}
                for c in chunks
            ],
        }
        yield {"event": "meta", "data": json.dumps(meta)}

        full_content = ""
        async for token in stream_rag_response(
            query=request.message,
            context_chunks=chunks,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        ):
            full_content += token
            yield {"event": "token", "data": json.dumps({"content": token})}

        yield {
            "event": "done",
            "data": json.dumps({
                "content_length": len(full_content),
                "entropy_score": round(min(1.0, len(chunks) * 0.15 + 0.3), 3),
            }),
        }

        conversation_id = request.conversation_id or str(uuid.uuid4())
        try:
            sb = get_supabase()
            sb.table("conversations").upsert({
                "id": conversation_id,
                "user_id": user_id,
                "title": request.message[:80],
            }, on_conflict="id").execute()
            sb.table("messages").insert([
                {
                    "id": str(uuid.uuid4()),
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": request.message,
                },
                {
                    "id": str(uuid.uuid4()),
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": full_content,
                },
            ]).execute()
        except Exception:
            pass

    return EventSourceResponse(event_generator())


@router.get("/conversations", response_model=list)
async def list_conversations(
    user_id: str = Depends(get_current_user),
):
    """List all conversations for the current user."""
    try:
        sb = get_supabase()
        result = sb.table("conversations") \
            .select("id, title, is_archived, created_at, updated_at") \
            .eq("user_id", user_id) \
            .order("updated_at", desc=True) \
            .limit(50) \
            .execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    try:
        sb = get_supabase()
        conv = sb.table("conversations") \
            .select("user_id") \
            .eq("id", conversation_id) \
            .execute()
        if not conv.data or conv.data[0]["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        result = sb.table("messages") \
            .select("id, role, content, meta, created_at") \
            .eq("conversation_id", conversation_id) \
            .order("created_at", desc=True) \
            .limit(100) \
            .execute()
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    try:
        sb = get_supabase()
        conv = sb.table("conversations") \
            .select("user_id") \
            .eq("id", conversation_id) \
            .execute()
        if not conv.data or conv.data[0]["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        sb.table("messages").delete().eq("conversation_id", conversation_id).execute()
        sb.table("conversations").delete().eq("id", conversation_id).execute()
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
