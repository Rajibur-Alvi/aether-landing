import json
import time
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from models.schemas import TextIngestRequest, IngestResponse, ChatRequest, ChatMessageResponse, ChatMeta, ChatSource
from services.pinecone_service import upsert_document_chunks, search_similar_chunks
from services.groq_service import generate_rag_response, stream_rag_response
from utils.text_splitter import (
    extract_text_from_docx_bytes,
    extract_text_from_pdf_bytes,
    extract_text_from_txt_bytes,
    split_text,
)
from config import get_settings

router = APIRouter(prefix="/public", tags=["Public Testing"])

TEST_USER_ID = "test-user-entropy"
PUBLIC_TEXT_LIMIT_BYTES = 200 * 1024
PUBLIC_FILE_LIMIT_BYTES = 5 * 1024 * 1024
PUBLIC_EXTRACTED_TEXT_LIMIT_BYTES = 200 * 1024
SUPPORTED_FILE_TYPES = ".txt, .pdf, .docx"

MODEL_MAP = {
    "fast": "llama-3.1-8b-instant",
    "balanced": "llama-3.1-8b-instant",   # free trial always uses fast model
    "thorough": "llama-3.3-70b-versatile",
}


def _utf8_size(text: str) -> int:
    return len(text.encode("utf-8"))


def _reject_if_public_text_too_large(
    text: str,
    label: str = "Content",
    limit_bytes: int = PUBLIC_EXTRACTED_TEXT_LIMIT_BYTES,
) -> None:
    if _utf8_size(text) > limit_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"{label} too large for free trial. Maximum 200KB allowed.",
        )


@router.post("/ingest/text", response_model=IngestResponse)
async def public_ingest_text(request: TextIngestRequest):
    """Public ingest text for free trials. Limited to 200KB content."""
    _reject_if_public_text_too_large(request.content, limit_bytes=PUBLIC_TEXT_LIMIT_BYTES)

    settings = get_settings()
    document_id = request.document_id or str(uuid.uuid4())

    chunks = split_text(
        request.content,
        chunk_size=settings.default_chunk_size,
        chunk_overlap=settings.default_chunk_overlap,
    )

    if not chunks:
        raise HTTPException(status_code=400, detail="No content to ingest after splitting")

    try:
        chunk_count = await upsert_document_chunks(
            user_id=TEST_USER_ID,
            document_id=document_id,
            chunks=chunks,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector storage failed: {str(e)}")

    return IngestResponse(
        document_id=document_id,
        chunk_count=chunk_count,
        status="indexed",
        message=f"Successfully ingested '{request.title}' into {chunk_count} chunks",
    )


@router.post("/ingest/file", response_model=IngestResponse)
async def public_ingest_file(
    file: UploadFile = File(...),
    title: str = Form(...),
):
    """Public ingest file for free trials. Limited to 5MB files and 200KB extracted text."""
    settings = get_settings()
    document_id = str(uuid.uuid4())

    file_bytes = await file.read()

    if len(file_bytes) > PUBLIC_FILE_LIMIT_BYTES:
        raise HTTPException(status_code=400, detail="File too large for free trial. Maximum 5MB allowed.")

    filename = file.filename or "untitled"

    content_type = file.content_type or ""
    if filename.lower().endswith(".pdf") or "pdf" in content_type:
        try:
            text = extract_text_from_pdf_bytes(file_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif filename.lower().endswith(".docx") or "wordprocessingml.document" in content_type:
        try:
            text = extract_text_from_docx_bytes(file_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif filename.lower().endswith(".txt") or "text" in content_type:
        try:
            text = extract_text_from_txt_bytes(file_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {filename}. Supported: {SUPPORTED_FILE_TYPES}",
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text content extracted from file")
    _reject_if_public_text_too_large(text, "Extracted text")

    chunks = split_text(
        text,
        chunk_size=settings.default_chunk_size,
        chunk_overlap=settings.default_chunk_overlap,
    )

    if not chunks:
        raise HTTPException(status_code=400, detail="No content to ingest after splitting")

    try:
        chunk_count = await upsert_document_chunks(
            user_id=TEST_USER_ID,
            document_id=document_id,
            chunks=chunks,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector storage failed: {str(e)}")

    return IngestResponse(
        document_id=document_id,
        chunk_count=chunk_count,
        status="indexed",
        message=f"Successfully ingested '{filename}' into {chunk_count} chunks",
    )


@router.post("/chat/ask", response_model=ChatMessageResponse)
async def public_ask_question(request: ChatRequest):
    """Public RAG endpoint for free trials. Limited functionality."""
    settings = get_settings()
    start = time.perf_counter()

    model_name = MODEL_MAP.get(request.model.value if request.model else "balanced", "llama-3.1-8b-instant")
    # Low temperature = accurate factual answers (correct for RAG)
    temperature = min(request.temperature or 0.1, 0.3)
    max_tokens = min(request.max_tokens or 512, 512)
    top_k = 3  # Reduced for free trial

    # Search Pinecone
    try:
        chunks = await search_similar_chunks(
            query=request.message,
            user_id=TEST_USER_ID,
            top_k=top_k,
            document_id=request.document_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector search failed: {str(e)}")

    data_density = len(chunks)

    # Generate via Groq
    try:
        result = await generate_rag_response(
            query=request.message,
            context_chunks=chunks,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=None,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Groq inference failed: {str(e)}")

    total_latency = int((time.perf_counter() - start) * 1000)

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
        id=str(uuid.uuid4()),
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


@router.post("/chat/ask/stream")
async def public_ask_question_stream(request: ChatRequest):
    """Public streaming RAG endpoint for free trials. Limited functionality."""
    settings = get_settings()

    model_name = MODEL_MAP.get(request.model.value if request.model else "balanced", "llama-3.1-8b-instant")
    temperature = min(request.temperature or 0.1, 0.3)
    max_tokens = min(request.max_tokens or 512, 512)
    top_k = 3  # Reduced for free trial

    try:
        chunks = await search_similar_chunks(
            query=request.message,
            user_id=TEST_USER_ID,
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
            system_prompt=None,
        ):
            full_content += token
            yield {"event": "token", "data": json.dumps({"content": token})}

        from services.groq_service import calculate_entropy
        yield {
            "event": "done",
            "data": json.dumps({
                "content_length": len(full_content),
                "entropy_score": calculate_entropy(full_content),
            }),
        }

    return EventSourceResponse(event_generator())
