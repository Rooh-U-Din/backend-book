"""
SQLAlchemy models for Neon Postgres database
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class QueryLog(Base):
    """Query logs table - stores all user queries and responses"""
    __tablename__ = 'query_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text)
    mode = Column(String(50), default='full-book', nullable=False, index=True)
    latency_ms = Column(Integer)
    user_session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    selected_text = Column(Text)
    citations_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<QueryLog(id={self.id}, mode={self.mode}, session={self.user_session_id})>"


class ChatSession(Base):
    """Chat sessions table - tracks user sessions"""
    __tablename__ = 'chat_sessions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    message_count = Column(Integer, default=0)
    user_agent = Column(Text)

    def __repr__(self):
        return f"<ChatSession(session_id={self.session_id}, messages={self.message_count})>"


class EmbeddingsMetadata(Base):
    """Embeddings metadata table - tracks embedding generation"""
    __tablename__ = 'embeddings_metadata'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chapter_id = Column(String(100), unique=True, nullable=False, index=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    last_generated = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    embedding_model = Column(String(100), default='text-embedding-3-small', nullable=False)
    total_tokens = Column(Integer)

    def __repr__(self):
        return f"<EmbeddingsMetadata(chapter={self.chapter_id}, chunks={self.chunk_count})>"
