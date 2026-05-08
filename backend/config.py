from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Groq
    groq_api_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "entropy-vectors"
    pinecone_dimension: int = 384

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""

    # Server
    # NOTE: Replace https://project-dmwt4.vercel.app with your actual Vercel domain.
    cors_origins: list[str] = [
        "https://project-dmwt4.vercel.app",
        "https://aether-landing.onrender.com",
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    environment: str = "development"

    # RAG defaults
    default_top_k: int = 5
    default_chunk_size: int = 500
    default_chunk_overlap: int = 50
    default_temperature: float = 0.7
    default_max_tokens: int = 1024
    default_model: str = "llama-3.3-70b-versatile"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Stripe
    stripe_secret_key: str = "sk_test_placeholder"
    stripe_publishable_key: str = "pk_test_placeholder"
    stripe_signal_pro_price_id: str = "price_placeholder_signal_pro"
    stripe_aether_core_price_id: str = "price_placeholder_aether_core"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
