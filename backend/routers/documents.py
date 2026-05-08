from fastapi import APIRouter, Depends, HTTPException
from models.schemas import DocumentResponse, DocumentListResponse
from middleware.auth import get_current_user
from services.pinecone_service import delete_document_chunks
from services.supabase_service import get_supabase

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user_id: str = Depends(get_current_user),
):
    """List all documents for the current user."""
    try:
        sb = get_supabase()
        result = sb.table("documents") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(100) \
            .execute()

        docs = [
            DocumentResponse(
                id=d["id"],
                title=d["title"],
                filename=d.get("filename"),
                file_type=d.get("file_type"),
                file_size=d.get("file_size"),
                chunk_count=d.get("chunk_count", 0),
                status=d.get("status", "unknown"),
                created_at=d["created_at"],
            )
            for d in result.data
        ]
        return DocumentListResponse(documents=docs, total=len(docs))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get a single document's metadata."""
    try:
        sb = get_supabase()
        result = sb.table("documents") \
            .select("*") \
            .eq("id", document_id) \
            .eq("user_id", user_id) \
            .execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        d = result.data[0]
        return DocumentResponse(
            id=d["id"],
            title=d["title"],
            filename=d.get("filename"),
            file_type=d.get("file_type"),
            file_size=d.get("file_size"),
            chunk_count=d.get("chunk_count", 0),
            status=d.get("status", "unknown"),
            created_at=d["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete a document and all its vector chunks."""
    try:
        sb = get_supabase()
        result = sb.table("documents") \
            .select("user_id") \
            .eq("id", document_id) \
            .execute()
        if not result.data or result.data[0]["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="Document not found")

        try:
            await delete_document_chunks(document_id)
        except Exception:
            pass

        sb.table("documents").delete().eq("id", document_id).execute()

        try:
            sb.table("dark_data_events").insert({
                "user_id": user_id,
                "event_type": "document_deleted",
                "event_data": {"document_id": document_id},
            }).execute()
        except Exception:
            pass

        return {"status": "deleted", "document_id": document_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
