import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from models.schemas import TextIngestRequest, IngestResponse
from middleware.auth import get_current_user
from services.pinecone_service import upsert_document_chunks
from services.supabase_service import get_supabase
from utils.text_splitter import (
    extract_text_from_docx_bytes,
    extract_text_from_pdf_bytes,
    extract_text_from_txt_bytes,
    split_text,
)
from config import get_settings

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])


@router.post("/text", response_model=IngestResponse)
async def ingest_text(
    request: TextIngestRequest,
    user_id: str = Depends(get_current_user),
):
    """Ingest a text document: split → embed → store in Pinecone → save metadata."""
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
            user_id=user_id,
            document_id=document_id,
            chunks=chunks,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector storage failed: {str(e)}")

    try:
        sb = get_supabase()
        sb.table("documents").upsert({
            "id": document_id,
            "user_id": user_id,
            "title": request.title,
            "file_type": "text",
            "file_size": len(request.content.encode("utf-8")),
            "chunk_count": chunk_count,
            "status": "indexed",
        }, on_conflict="id").execute()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Metadata storage failed: {str(e)}")

    try:
        sb.table("dark_data_events").insert({
            "user_id": user_id,
            "event_type": "document_ingested",
            "event_data": {
                "document_id": document_id,
                "title": request.title,
                "chunk_count": chunk_count,
                "file_type": "text",
            },
        }).execute()
    except Exception:
        pass

    return IngestResponse(
        document_id=document_id,
        chunk_count=chunk_count,
        status="indexed",
        message=f"Successfully ingested '{request.title}' into {chunk_count} chunks",
    )


@router.post("/file", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    user_id: str = Depends(get_current_user),
):
    """Ingest a file (TXT, PDF, or DOCX): extract → split → embed → store."""
    settings = get_settings()
    document_id = str(uuid.uuid4())

    file_bytes = await file.read()
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
            detail=f"Unsupported file type: {filename}. Supported: .txt, .pdf, .docx",
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text content extracted from file")

    chunks = split_text(
        text,
        chunk_size=settings.default_chunk_size,
        chunk_overlap=settings.default_chunk_overlap,
    )

    if not chunks:
        raise HTTPException(status_code=400, detail="No content to ingest after splitting")

    try:
        chunk_count = await upsert_document_chunks(
            user_id=user_id,
            document_id=document_id,
            chunks=chunks,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector storage failed: {str(e)}")

    try:
        sb = get_supabase()
        sb.table("documents").insert({
            "id": document_id,
            "user_id": user_id,
            "title": title,
            "filename": filename,
            "file_type": filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown",
            "file_size": len(file_bytes),
            "chunk_count": chunk_count,
            "status": "indexed",
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Metadata storage failed: {str(e)}")

    try:
        sb.table("dark_data_events").insert({
            "user_id": user_id,
            "event_type": "file_ingested",
            "event_data": {
                "document_id": document_id,
                "title": title,
                "filename": filename,
                "chunk_count": chunk_count,
            },
        }).execute()
    except Exception:
        pass

    return IngestResponse(
        document_id=document_id,
        chunk_count=chunk_count,
        status="indexed",
        message=f"Successfully ingested '{filename}' into {chunk_count} chunks",
    )
