import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from routers import health, chat, ingest, documents, user
from services.pinecone_service import _get_pinecone
from services.embedding_service import _load_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: preload models and connections. Shutdown: cleanup."""
    print("⚡ Loading embedding model...")
    _load_model()
    print("✅ Embedding model loaded (all-MiniLM-L6-v2, dim=384)")

    print("⚡ Connecting to Pinecone...")
    settings = get_settings()
    try:
        pc = _get_pinecone()
        idx = pc.Index(settings.pinecone_index_name)
        stats = idx.describe_index_stats()
        print(f"✅ Pinecone connected — {stats.get('total_vector_count', 0)} vectors")
    except Exception as e:
        print(f"⚠️  Pinecone connection warning: {e}")

    print("🚀 Entropy Backend is live.")
    yield

    print("🔌 Shutting down...")


app = FastAPI(
    title="The Entropy Aesthetic — Backend",
    description="High-performance RAG backend with Groq + Pinecone + Supabase",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──
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


# ── Register Routers ──
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(user.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "The Entropy Aesthetic — Backend",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }
