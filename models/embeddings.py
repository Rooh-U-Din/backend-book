"""
Pydantic models for Qdrant vector embeddings
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChunkMetadata(BaseModel):
    """Metadata for a book content chunk"""
    chapter_id: str = Field(..., description="Unique chapter identifier")
    chapter_title: str = Field(..., description="Human-readable chapter title")
    section_title: str = Field(..., description="Section or subsection title")
    url_path: str = Field(..., description="Relative URL path to the section")
    chunk_index: int = Field(..., description="Sequential chunk index within chapter")
    token_count: int = Field(..., description="Number of tokens in chunk")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "chapter_id": "ros2-fundamentals",
                "chapter_title": "ROS 2 Fundamentals",
                "section_title": "Topics and Publishers",
                "url_path": "/docs/modules/ros2/fundamentals#topics",
                "chunk_index": 0,
                "token_count": 742,
                "created_at": "2025-12-06T12:00:00Z"
            }
        }


class BookChunk(BaseModel):
    """Complete book chunk with vector embedding and metadata"""
    id: Optional[str] = Field(None, description="Qdrant point ID (UUID)")
    vector: list[float] = Field(..., description="1536-dimensional embedding vector")
    chunk_text: str = Field(..., description="The actual text content")
    metadata: ChunkMetadata = Field(..., description="Chunk metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "vector": [0.023, -0.012, 0.456, "..."],
                "chunk_text": "ROS 2 uses DDS (Data Distribution Service) for communication between nodes...",
                "metadata": {
                    "chapter_id": "ros2-fundamentals",
                    "chapter_title": "ROS 2 Fundamentals",
                    "section_title": "Communication Middleware",
                    "url_path": "/docs/modules/ros2/fundamentals#dds",
                    "chunk_index": 2,
                    "token_count": 512,
                    "created_at": "2025-12-06T12:00:00Z"
                }
            }
        }


class SearchResult(BaseModel):
    """Qdrant search result with score"""
    chunk: BookChunk = Field(..., description="Retrieved chunk")
    score: float = Field(..., description="Similarity score (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "chunk_text": "ROS 2 uses DDS...",
                    "metadata": {}
                },
                "score": 0.92
            }
        }
