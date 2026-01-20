"""Database connection with support for cloud/remote databases."""

import os
import sqlite3
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

from app.config import CACHE_DB


def get_db_connection(db_path: Optional[Path] = None):
    """
    Get database connection with support for:
    - Local SQLite (default)
    - Remote PostgreSQL (if configured)
    - Cloud SQLite (via environment variable)
    """
    # Check for remote database configuration
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        # PostgreSQL connection
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # Supabase requires SSL connection
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "superfinder"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                sslmode=os.getenv("DB_SSLMODE", "require")  # Supabase requires SSL
            )
            return conn
        except ImportError:
            raise ImportError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")
    
    elif db_type == "cloud_sqlite":
        # SQLite file stored in cloud directory (e.g., synced via Dropbox, iCloud, etc.)
        cloud_path = os.getenv("CLOUD_DB_PATH")
        if cloud_path:
            db_path = Path(cloud_path)
        else:
            # Default to iCloud Drive or Dropbox if available
            home = Path.home()
            for cloud_dir in ["iCloud Drive", "Dropbox"]:
                cloud_path = home / cloud_dir / "SuperFinder" / "cache.sqlite"
                if cloud_path.parent.exists():
                    db_path = cloud_path
                    break
        
        if db_path is None:
            db_path = CACHE_DB
    
    else:
        # Default: Local SQLite
        if db_path is None:
            db_path = CACHE_DB
    
    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    return sqlite3.connect(str(db_path), check_same_thread=False)


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize the database (works with both SQLite and PostgreSQL)."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Check database type
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        # PostgreSQL schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_cache (
                url TEXT PRIMARY KEY,
                html TEXT,
                text_content TEXT,
                fetched_at TIMESTAMP,
                status_code INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_profiles (
                url TEXT PRIMARY KEY,
                profile_json TEXT,
                extracted_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supervisors (
                id SERIAL PRIMARY KEY,
                canonical_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                title TEXT,
                institution TEXT NOT NULL,
                domain TEXT,
                country TEXT,
                region TEXT,
                email TEXT,
                email_confidence TEXT,
                homepage TEXT,
                profile_url TEXT,
                source_url TEXT NOT NULL,
                evidence_email TEXT,
                evidence_snippets_json TEXT,
                keywords_json TEXT NOT NULL,
                keywords_text TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_verified_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_institution ON supervisors(institution)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_region ON supervisors(region)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_country ON supervisors(country)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_email ON supervisors(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_last_seen_at ON supervisors(last_seen_at)")
        
        # Subscription system tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                subscription_type TEXT NOT NULL,  -- 'free', 'individual', 'enterprise'
                status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'expired', 'cancelled'
                searches_per_month INTEGER NOT NULL,
                remaining_searches INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                subscription_id INTEGER REFERENCES subscriptions(id),
                search_type TEXT NOT NULL,  -- 'free', 'individual', 'enterprise'
                keywords TEXT,
                universities_count INTEGER,
                regions TEXT,
                countries TEXT,
                result_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for subscription tables
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_expires_at ON subscriptions(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON search_logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs(created_at)")
    
    else:
        # SQLite schema (original)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_cache (
                url TEXT PRIMARY KEY,
                html TEXT,
                text_content TEXT,
                fetched_at TIMESTAMP,
                status_code INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_profiles (
                url TEXT PRIMARY KEY,
                profile_json TEXT,
                extracted_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supervisors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                title TEXT,
                institution TEXT NOT NULL,
                domain TEXT,
                country TEXT,
                region TEXT,
                email TEXT,
                email_confidence TEXT,
                homepage TEXT,
                profile_url TEXT,
                source_url TEXT NOT NULL,
                evidence_email TEXT,
                evidence_snippets_json TEXT,
                keywords_json TEXT NOT NULL,
                keywords_text TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_verified_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_institution ON supervisors(institution)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_region ON supervisors(region)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_country ON supervisors(country)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_email ON supervisors(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supervisors_last_seen_at ON supervisors(last_seen_at)")
        
        # Subscription system tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                subscription_type TEXT NOT NULL,  -- 'free', 'individual', 'enterprise'
                status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'expired', 'cancelled'
                searches_per_month INTEGER NOT NULL,
                remaining_searches INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                subscription_id INTEGER REFERENCES subscriptions(id),
                search_type TEXT NOT NULL,  -- 'free', 'individual', 'enterprise'
                keywords TEXT,
                universities_count INTEGER,
                regions TEXT,
                countries TEXT,
                result_count INTEGER,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create indexes for subscription tables
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_expires_at ON subscriptions(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON search_logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs(created_at)")
    
    conn.commit()
    conn.close()

