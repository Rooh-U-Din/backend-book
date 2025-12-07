"""
Pydantic models for RAG query API requests and responses
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import uuid


class Citation(BaseModel):
    """Citation reference to book content"""
    chapter_id: str = Field(..., description="Chapter identifier (e.g., 'ros2-fundamentals')")
    chapter_title: str = Field(..., description="Human-readable chapter title")
    section_title: str = Field(..., description="Section title within the chapter")
    url: str = Field(..., description="Relative URL path to the section")
    relevance_score: Optional[float] = Field(None, description="Similarity score from vector search (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "chapter_id": "ros2-fundamentals",
                "chapter_title": "ROS 2 Fundamentals",
                "section_title": "Topics and Publishers",
                "url": "/docs/modules/ros2/fundamentals#topics",
                "relevance_score": 0.89
            }
        }


class QueryRequest(BaseModel):
    """Request model for full-book RAG query"""
    query: str = Field(..., min_length=1, max_length=500, description="User's question")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session identifier for rate limiting")

    @validator('query')
    def validate_query(cls, v):
        """Validate and sanitize query text"""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty after trimming whitespace")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is ROS 2 and how does it differ from ROS 1?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class SelectionQueryRequest(BaseModel):
    """Request model for selection-based RAG query"""
    selected_text: str = Field(..., min_length=1, max_length=5000, description="Text selected by user")
    query: str = Field(..., min_length=1, max_length=500, description="User's question about the selection")
    chapter_context: str = Field(..., description="Current chapter ID for context")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session identifier")

    @validator('selected_text')
    def validate_selection(cls, v):
        """Validate and truncate selected text"""
        v = v.strip()
        if not v:
            raise ValueError("Selected text cannot be empty")
        # Truncate to 1000 words if too long
        words = v.split()
        if len(words) > 1000:
            v = ' '.join(words[:1000]) + '...'
        return v

    @validator('query')
    def validate_query(cls, v):
        """Validate query text"""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "selected_text": "ROS 2 uses DDS (Data Distribution Service) for communication...",
                "query": "What are the benefits of using DDS?",
                "chapter_context": "ros2-fundamentals",
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class QueryResponse(BaseModel):
    """Response model for RAG query"""
    answer: str = Field(..., description="Generated answer to the query")
    citations: List[Citation] = Field(default_factory=list, description="Citations to book sections")
    mode: str = Field(..., description="Query mode: 'full-book' or 'selection'")
    latency_ms: int = Field(..., description="Query processing time in milliseconds")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "ROS 2 is the next generation of the Robot Operating System...",
                "citations": [
                    {
                        "chapter_id": "ros2-fundamentals",
                        "chapter_title": "ROS 2 Fundamentals",
                        "section_title": "Introduction",
                        "url": "/docs/modules/ros2/fundamentals",
                        "relevance_score": 0.92
                    }
                ],
                "mode": "full-book",
                "latency_ms": 2340,
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-12-06T12:00:00Z"
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: dict = Field(default_factory=dict, description="Status of dependent services")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-06T12:00:00Z",
                "services": {
                    "qdrant": "connected",
                    "neon_postgres": "connected",
                    "gemini_api": "available"
                }
            }
        }
