"""
Migration script to add email verification columns to users table (FR-026)
"""

import os
import sys
from pathlib import Path

# Get the backend directory (2 levels up from migrations folder)
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir / "src"))

from dotenv import load_dotenv
# Load from backend/.env
load_dotenv(backend_dir / ".env")

import psycopg2

def run_migration():
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        print("ERROR: NEON_DATABASE_URL not set")
        return False

    migration_sql = """
    -- Add email verification columns to users table (FR-026)
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE NOT NULL,
        ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255),
        ADD COLUMN IF NOT EXISTS verification_expires TIMESTAMP WITH TIME ZONE;

    -- Index for looking up users by verification token
    CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)
        WHERE verification_token IS NOT NULL;
    """

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("Running migration 002: Add email verification columns...")
        cursor.execute(migration_sql)
        conn.commit()

        print("Migration completed successfully!")

        # Verify columns exist
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'users'
            AND column_name IN ('email_verified', 'verification_token', 'verification_expires')
            ORDER BY column_name
        """)
        columns = cursor.fetchall()
        print(f"Added columns: {[c[0] for c in columns]}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    run_migration()
