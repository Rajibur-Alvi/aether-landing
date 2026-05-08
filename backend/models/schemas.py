from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ── Chat ──

class ModelOption(str, Enum):
    fast = "llama-3.1-8b-instant"
    balanced = "llama-3.3-70b-versatile"
    thorough = "llama-3.3-70b-versatile"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None
    model: ModelOption = ModelOption.balanced
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)


class ChatSource(BaseModel):
    text: str
    document_id: str
    chunk_index: int
    score: float


class ChatMeta(BaseModel):
    entropy_score: float = 0.0
    latency_ms: int = 0
    tokens_per_second: float = 0.0
    data_density: int = 0
    sources: list[ChatSource] = []


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    meta: ChatMeta
    created_at: datetime


# ── Ingest ──

class TextIngestRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    document_id: Optional[str] = None


class IngestResponse(BaseModel):
    document_id: str
    chunk_count: int
    status: str
    message: str


# ── Documents ──

class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: Optional[str]
    file_type: Optional[str]
    file_size: Optional[int]
    chunk_count: int
    status: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ── User ──

class UserProfileResponse(BaseModel):
    id: str
    username: Optional[str]
    full_name: Optional[str]
    avatar_url: Optional[str]
    entropy_level: int = 50
    ghost_mode: bool = False
    theme: str = "entropy"
    created_at: datetime
    updated_at: datetime


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    entropy_level: Optional[int] = Field(None, ge=0, le=100)
    ghost_mode: Optional[bool] = None
    theme: Optional[str] = None


class CommandCenterResponse(BaseModel):
    inference_speed: str = "balanced"
    model_preference: str = "llama-3.3-70b-versatile"
    retrieval_depth: int = 5
    temperature: float = 0.7
    max_tokens: int = 1024
    system_prompt: Optional[str] = None
    updated_at: datetime


class UpdateCommandCenterRequest(BaseModel):
    inference_speed: Optional[str] = None
    model_preference: Optional[str] = None
    retrieval_depth: Optional[int] = Field(None, ge=1, le=20)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8192)
    system_prompt: Optional[str] = None


class DarkDataEvent(BaseModel):
    event_type: str
    event_data: dict = {}


class DarkDataResponse(BaseModel):
    events: list[dict]
    total: int


class ConversationResponse(BaseModel):
    id: str
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# ── Health ──

class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict
    uptime_seconds: float
