"""
Migration script to create auth and personalization tables
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

import psycopg2

def run_migration():
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        print("ERROR: NEON_DATABASE_URL not set")
        return False

    migration_sql = """
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255),
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

    -- User profiles table
    CREATE TABLE IF NOT EXISTS user_profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        expertise_level VARCHAR(20) DEFAULT 'intermediate',
        programming_languages TEXT[] DEFAULT '{}',
        learning_goals TEXT,
        questionnaire_responses JSONB,
        profile_completed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_profiles_expertise ON user_profiles(expertise_level);

    -- Personalized content cache table
    CREATE TABLE IF NOT EXISTS personalized_content (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        chapter_id VARCHAR(100) NOT NULL,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        profile_hash VARCHAR(16) NOT NULL,
        personalized_content TEXT NOT NULL,
        is_cached BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        expires_at TIMESTAMP WITH TIME ZONE
    );

    CREATE INDEX IF NOT EXISTS idx_personalized_chapter_hash
        ON personalized_content(chapter_id, profile_hash);
    CREATE INDEX IF NOT EXISTS idx_personalized_user ON personalized_content(user_id);

    -- Skill invocations log table
    CREATE TABLE IF NOT EXISTS skill_invocations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        skill_id VARCHAR(50) NOT NULL,
        input_text TEXT,
        output_text TEXT,
        latency_ms INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_skill_invocations_user ON skill_invocations(user_id);
    CREATE INDEX IF NOT EXISTS idx_skill_invocations_skill ON skill_invocations(skill_id);
    CREATE INDEX IF NOT EXISTS idx_skill_invocations_created ON skill_invocations(created_at);
    """

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("Running migration...")
        cursor.execute(migration_sql)
        conn.commit()

        print("Migration completed successfully!")

        # Verify tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('users', 'user_profiles', 'personalized_content', 'skill_invocations')
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"Created tables: {[t[0] for t in tables]}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    run_migration()
