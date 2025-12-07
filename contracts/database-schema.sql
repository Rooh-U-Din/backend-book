-- Neon Postgres Schema for Physical AI & Humanoid Robotics RAG Chatbot
-- Version: 1.0.0
-- Database: Neon Serverless Postgres

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Query Logs Table
-- Stores all user queries, responses, and performance metrics
CREATE TABLE IF NOT EXISTS query_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    query_text TEXT NOT NULL,
    response_text TEXT,
    mode VARCHAR(50) DEFAULT 'full-book' CHECK (mode IN ('full-book', 'selection')),
    latency_ms INTEGER,
    user_session_id UUID NOT NULL,
    selected_text TEXT,
    citations_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for common queries
    INDEX idx_query_logs_session (user_session_id),
    INDEX idx_query_logs_timestamp (timestamp DESC),
    INDEX idx_query_logs_mode (mode)
);

-- Chat Sessions Table
-- Tracks user sessions for rate limiting and analytics
CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    message_count INTEGER DEFAULT 0,
    user_agent TEXT,

    -- Indexes
    INDEX idx_chat_sessions_session_id (session_id),
    INDEX idx_chat_sessions_last_activity (last_activity DESC)
);

-- Embeddings Metadata Table
-- Tracks embedding generation history and statistics
CREATE TABLE IF NOT EXISTS embeddings_metadata (
    id BIGSERIAL PRIMARY KEY,
    chapter_id VARCHAR(100) NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    last_generated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    total_tokens INTEGER,

    -- Ensure one record per chapter
    UNIQUE(chapter_id),

    -- Index
    INDEX idx_embeddings_chapter (chapter_id)
);

-- Comments
COMMENT ON TABLE query_logs IS 'Stores all user queries and responses for analytics and debugging';
COMMENT ON TABLE chat_sessions IS 'Tracks user sessions for rate limiting and usage analytics';
COMMENT ON TABLE embeddings_metadata IS 'Metadata about embedding generation runs for each chapter';

COMMENT ON COLUMN query_logs.mode IS 'Query mode: full-book (search entire book) or selection (constrained to selected text)';
COMMENT ON COLUMN query_logs.latency_ms IS 'Total query processing time in milliseconds';
COMMENT ON COLUMN query_logs.citations_json IS 'JSON array of citation objects with chapter_id, section_title, url';

-- Sample queries for testing

-- Get recent queries for a session
-- SELECT * FROM query_logs WHERE user_session_id = 'YOUR_SESSION_UUID' ORDER BY timestamp DESC LIMIT 10;

-- Get average latency by mode
-- SELECT mode, AVG(latency_ms) as avg_latency, COUNT(*) as query_count FROM query_logs GROUP BY mode;

-- Get active sessions in last 24 hours
-- SELECT COUNT(*) FROM chat_sessions WHERE last_activity > NOW() - INTERVAL '24 hours';
