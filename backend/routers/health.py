import time
from fastapi import APIRouter
from models.schemas import HealthResponse
from services.pinecone_service import get_index_stats
from services.supabase_service import get_supabase
from services.embedding_service import get_single_embedding

_start_time = time.time()
router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health of all connected services."""

    # Check Pinecone
    try:
        stats = await get_index_stats()
        pinecone_status = "healthy"
        pinecone_detail = stats
    except Exception as e:
        pinecone_status = "error"
        pinecone_detail = {"error": str(e)[:100]}

    # Check Supabase
    try:
        sb = get_supabase()
        sb.table("user_profiles").select("id").limit(1).execute()
        supabase_status = "healthy"
        supabase_detail = "connected"
    except Exception as e:
        supabase_status = "error"
        supabase_detail = {"error": str(e)[:100]}

    # Check embedding model
    try:
        emb = await get_single_embedding("test")
        groq_status = "healthy"
        groq_detail = {"embedding_dim": len(emb)}
    except Exception as e:
        groq_status = "error"
        groq_detail = {"error": str(e)[:100]}

    return HealthResponse(
        status="operational" if all(
            s == "healthy" for s in [pinecone_status, supabase_status, groq_status]
        ) else "degraded",
        version="1.0.0",
        services={
            "pinecone": {"status": pinecone_status, "detail": pinecone_detail},
            "supabase": {"status": supabase_status, "detail": supabase_detail},
            "groq_embeddings": {"status": groq_status, "detail": groq_detail},
        },
        uptime_seconds=round(time.time() - _start_time, 1),
    )
