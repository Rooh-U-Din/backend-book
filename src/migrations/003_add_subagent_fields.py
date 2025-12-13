"""
Migration 003: Add Subagent Fields

Extends skill_invocations table for subagent tracing and error handling.
Based on data-model.md specification.

Usage:
    python -m migrations.003_add_subagent_fields

Or run directly:
    python migrations/003_add_subagent_fields.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


MIGRATION_SQL = """
-- Migration: 003_add_subagent_fields
-- Extends skill_invocations table for subagent tracing

-- Add trace_id column for correlation
ALTER TABLE skill_invocations
ADD COLUMN IF NOT EXISTS trace_id UUID UNIQUE;

-- Add status column with default
ALTER TABLE skill_invocations
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'success';

-- Add context column for snapshot storage
ALTER TABLE skill_invocations
ADD COLUMN IF NOT EXISTS context JSONB;

-- Add error_message column for failure details
ALTER TABLE skill_invocations
ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Create index for trace lookups
CREATE INDEX IF NOT EXISTS idx_skill_invocations_trace_id
ON skill_invocations(trace_id);

-- Create index for status filtering
CREATE INDEX IF NOT EXISTS idx_skill_invocations_status
ON skill_invocations(status);

-- Create composite index for user analytics
CREATE INDEX IF NOT EXISTS idx_skill_invocations_user_skill
ON skill_invocations(user_id, skill_id, created_at DESC);
"""


def run_migration():
    """Execute the migration against the database."""
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        print("ERROR: NEON_DATABASE_URL environment variable not set")
        return False

    # Use psycopg2 for synchronous operations
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    elif not database_url.startswith("postgresql://"):
        database_url = f"postgresql://{database_url.split('://', 1)[-1]}"

    print(f"Connecting to database...")
    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Execute each statement separately
            statements = [s.strip() for s in MIGRATION_SQL.split(';') if s.strip() and not s.strip().startswith('--')]

            for i, statement in enumerate(statements, 1):
                if statement:
                    print(f"Executing statement {i}/{len(statements)}...")
                    conn.execute(text(statement))

            conn.commit()
            print("Migration 003 completed successfully!")
            return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    finally:
        engine.dispose()


def check_migration_status():
    """Check if migration has already been applied."""
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        return False

    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    elif not database_url.startswith("postgresql://"):
        database_url = f"postgresql://{database_url.split('://', 1)[-1]}"

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'skill_invocations'
                AND column_name = 'trace_id'
            """))
            return result.fetchone() is not None
    except Exception:
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    if check_migration_status():
        print("Migration 003 already applied - trace_id column exists")
    else:
        success = run_migration()
        sys.exit(0 if success else 1)
