"""
SQLAlchemy models for Neon Postgres database
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, BigInteger, Index, Boolean, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


# ============ AUTH & PROFILE MODELS ============

class User(Base):
    """Users table - stores authenticated user information"""
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    verification_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class UserProfile(Base):
    """User profiles table - stores user background and expertise information"""
    __tablename__ = 'user_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    expertise_level = Column(String(20), default='intermediate')
    programming_languages = Column(ARRAY(Text), default=[])
    learning_goals = Column(Text)
    questionnaire_responses = Column(JSONB)
    profile_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, expertise={self.expertise_level})>"


class PersonalizedContent(Base):
    """Personalized content cache table"""
    __tablename__ = 'personalized_content'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(String(100), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    profile_hash = Column(String(16), nullable=False)
    personalized_content = Column(Text, nullable=False)
    is_cached = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('idx_personalized_chapter_hash', 'chapter_id', 'profile_hash'),
    )

    def __repr__(self):
        return f"<PersonalizedContent(chapter={self.chapter_id}, hash={self.profile_hash})>"


class SkillInvocation(Base):
    """Skill invocations log table - tracks agent skill usage"""
    __tablename__ = 'skill_invocations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    skill_id = Column(String(50), nullable=False, index=True)
    trace_id = Column(UUID(as_uuid=True), unique=True, index=True)
    input_text = Column(Text)
    output_text = Column(Text)
    status = Column(String(20), default='success')
    latency_ms = Column(Integer)
    context = Column(JSONB)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_skill_invocations_user_skill', 'user_id', 'skill_id', created_at.desc()),
    )

    def __repr__(self):
        return f"<SkillInvocation(skill={self.skill_id}, trace={self.trace_id}, status={self.status})>"


# ============ EXISTING MODELS ============

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
