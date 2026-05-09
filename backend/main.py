import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from routers import health, chat, ingest, documents, user, public, payment
from services.pinecone_service import _get_pinecone
from services.embedding_service import get_dimension


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify remote connections. Shutdown: cleanup."""
    settings = get_settings()

    dim = get_dimension()
    print(f"✅ Pinecone hosted embeddings configured ({settings.embedding_model_name}, dim={dim})")

    print("⚡ Connecting to Pinecone...")
    try:
        pc = _get_pinecone()
        idx = pc.Index(settings.pinecone_index_name)
        stats = idx.describe_index_stats()
        vec_count = stats.get("total_vector_count", 0)
        index_dim = stats.get("dimension", 0)
        if index_dim and index_dim != dim:
            print(
                f"⚠️  Pinecone index dimension mismatch! "
                f"Index={index_dim}, model={dim}. "
                f"Delete and recreate the index at {dim} dims."
            )
        else:
            print(f"✅ Pinecone connected — {vec_count} vectors, dim={index_dim}")
    except Exception as e:
        print(f"⚠️  Pinecone connection warning: {e}")

    print(f"🚀 Entropy Backend is live. CORS origins: {settings.cors_origins}")
    yield

    print("🔌 Shutting down...")


app = FastAPI(
    title="The Entropy Aesthetic — Backend",
    description="High-performance RAG backend with Groq + Pinecone + Supabase",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Origins are loaded from the CORS_ORIGINS env var (comma-separated list).
# Set it on Render to your Vercel URL, e.g.:
#   CORS_ORIGINS=https://yourapp.vercel.app,https://www.yourapp.com
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Entropy-Score", "X-Latency-Ms", "X-Tokens-Per-Second"],
)


@app.middleware("http")
async def add_entropy_headers(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    elapsed = int((time.perf_counter() - start) * 1000)
    response.headers["X-Response-Time-Ms"] = str(elapsed)
    response.headers["X-Powered-By"] = "Entropy Aesthetic"
    return response


# ── Register Routers ──────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(payment.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "The Entropy Aesthetic — Backend",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
    }
