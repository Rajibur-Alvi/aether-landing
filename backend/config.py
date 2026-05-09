import os
from pydantic_settings import BaseSettings
from functools import lru_cache


def _parse_cors(raw: str) -> list[str]:
    """Parse comma-separated CORS origins from env var."""
    return [o.strip() for o in raw.split(",") if o.strip()]


class Settings(BaseSettings):
    # ── Groq ──────────────────────────────────────────────────────────────────
    groq_api_key: str = ""

    # ── Pinecone ──────────────────────────────────────────────────────────────
    pinecone_api_key: str = ""
    pinecone_index_name: str = "entropy-vectors"
    # IMPORTANT: Must match the embedding model dimension below.
    # BAAI/bge-base-en-v1.5 → 768 dims
    # sentence-transformers/all-MiniLM-L6-v2 → 384 dims (old, worse)
    pinecone_dimension: int = 768

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""

    # ── Lemon Squeezy (payments) ───────────────────────────────────────────────
    lemonsqueezy_api_key: str = ""
    lemonsqueezy_store_id: str = ""
    # Variant IDs from your Lemon Squeezy dashboard → Products → Variants
    lemonsqueezy_signal_variant_id: str = ""       # Signal $29/mo
    lemonsqueezy_signal_pro_variant_id: str = ""   # Signal Pro $99/mo
    # Where to send users after payment (your Vercel URL)
    app_url: str = "http://localhost:3000"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Set CORS_ORIGINS env var to a comma-separated list of allowed origins.
    # Example: CORS_ORIGINS=https://yourapp.vercel.app,http://localhost:3000
    cors_origins_raw: str = "http://localhost:3000,http://localhost:8080"

    @property
    def cors_origins(self) -> list[str]:
        return _parse_cors(self.cors_origins_raw)

    environment: str = "development"

    # ── RAG defaults ──────────────────────────────────────────────────────────
    default_top_k: int = 5
    # Larger chunks = more context per chunk = better accuracy
    default_chunk_size: int = 1200
    default_chunk_overlap: int = 200
    # Low temperature = precise factual answers (RAG use case)
    default_temperature: float = 0.1
    default_max_tokens: int = 1024
    # Fast model by default; users can switch to 70b in Command Center
    default_model: str = "llama-3.1-8b-instant"
    # Upgraded embedding model — significantly better accuracy than MiniLM
    embedding_model_name: str = "BAAI/bge-base-en-v1.5"
    # Minimum cosine similarity score to include a chunk as context
    default_score_threshold: float = 0.65

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
