"""SQLite cache for crawled pages and extracted data."""

import sqlite3
import json
import os
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

from app.config import CACHE_DB, get_secret
from app.db_cloud import get_db_connection


def _is_postgresql(conn) -> bool:
    """Check if connection is PostgreSQL."""
    # First check DB_TYPE from config (most reliable)
    db_type = get_secret("DB_TYPE", "sqlite").lower()
    if db_type == "postgresql":
        return True
    
    # Check connection module name
    try:
        module_name = conn.__class__.__module__
        if 'psycopg2' in module_name or 'psycopg' in module_name:
            return True
    except Exception:
        pass
    
    return False


def init_db(db_path: Path = CACHE_DB) -> None:
    """Initialize the cache database (works with both SQLite and PostgreSQL)."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Check database type
    is_pg = _is_postgresql(conn)
    
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
    
    # Create supervisors table for local repository
    # Use SERIAL for PostgreSQL, AUTOINCREMENT for SQLite
    if is_pg:
        id_column = "id SERIAL PRIMARY KEY"
    else:
        id_column = "id INTEGER PRIMARY KEY AUTOINCREMENT"
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS supervisors (
            {id_column},
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
    
    # Create FTS5 virtual table for full-text search (SQLite only)
    # PostgreSQL doesn't support FTS5, skip it for PostgreSQL
    if not is_pg:
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS supervisors_fts USING fts5(
                    name,
                    institution,
                    title,
                    keywords_text,
                    content='supervisors',
                    content_rowid='id'
                )
            """)
            
            # Create triggers to keep FTS5 in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS supervisors_fts_insert AFTER INSERT ON supervisors BEGIN
                    INSERT INTO supervisors_fts(rowid, name, institution, title, keywords_text)
                    VALUES (new.id, new.name, new.institution, new.title, new.keywords_text);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS supervisors_fts_delete AFTER DELETE ON supervisors BEGIN
                    DELETE FROM supervisors_fts WHERE rowid = old.id;
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS supervisors_fts_update AFTER UPDATE ON supervisors BEGIN
                    DELETE FROM supervisors_fts WHERE rowid = old.id;
                    INSERT INTO supervisors_fts(rowid, name, institution, title, keywords_text)
                    VALUES (new.id, new.name, new.institution, new.title, new.keywords_text);
                END
            """)
        except sqlite3.OperationalError:
            # FTS5 might not be available, skip it
            pass
    
    conn.commit()
    conn.close()


def get_cached_page(url: str, max_age_days: int = 7, db_path: Path = CACHE_DB) -> Optional[dict]:
    """Get cached page if exists and not expired."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Use appropriate parameter placeholder
    is_pg = _is_postgresql(conn)
    param_placeholder = "%s" if is_pg else "?"
    
    cursor.execute(
        f"SELECT html, text_content, fetched_at, status_code FROM page_cache WHERE url = {param_placeholder}",
        (url,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        fetched_at = datetime.fromisoformat(row[2])
        if datetime.now() - fetched_at < timedelta(days=max_age_days):
            return {
                "html": row[0],
                "text_content": row[1],
                "status_code": row[3]
            }
    return None


def cache_page(url: str, html: str, text_content: str, status_code: int, db_path: Path = CACHE_DB) -> None:
    """Cache a fetched page."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Use appropriate syntax for INSERT OR REPLACE
    is_pg = _is_postgresql(conn)
    if is_pg:
        # PostgreSQL uses ON CONFLICT
        cursor.execute("""
            INSERT INTO page_cache (url, html, text_content, fetched_at, status_code)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE SET
                html = EXCLUDED.html,
                text_content = EXCLUDED.text_content,
                fetched_at = EXCLUDED.fetched_at,
                status_code = EXCLUDED.status_code
        """, (url, html, text_content, datetime.now().isoformat(), status_code))
    else:
        # SQLite uses INSERT OR REPLACE
        cursor.execute("""
        INSERT OR REPLACE INTO page_cache (url, html, text_content, fetched_at, status_code)
        VALUES (?, ?, ?, ?, ?)
    """, (url, html, text_content, datetime.now().isoformat(), status_code))
    
    conn.commit()
    conn.close()


def get_cached_profile(url: str, db_path: Path = CACHE_DB) -> Optional[dict]:
    """Get cached extracted profile."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Use appropriate parameter placeholder
    is_pg = _is_postgresql(conn)
    param_placeholder = "%s" if is_pg else "?"
    
    cursor.execute(f"SELECT profile_json FROM extracted_profiles WHERE url = {param_placeholder}", (url,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return None


def cache_profile(url: str, profile: dict, db_path: Path = CACHE_DB) -> None:
    """Cache extracted profile."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Use appropriate syntax for INSERT OR REPLACE
    is_pg = _is_postgresql(conn)
    if is_pg:
        # PostgreSQL uses ON CONFLICT
        cursor.execute("""
            INSERT INTO extracted_profiles (url, profile_json, extracted_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (url) DO UPDATE SET
                profile_json = EXCLUDED.profile_json,
                extracted_at = EXCLUDED.extracted_at
        """, (url, json.dumps(profile), datetime.now().isoformat()))
    else:
        # SQLite uses INSERT OR REPLACE
        cursor.execute("""
        INSERT OR REPLACE INTO extracted_profiles (url, profile_json, extracted_at)
        VALUES (?, ?, ?)
    """, (url, json.dumps(profile), datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


# Initialize DB on import
init_db()

