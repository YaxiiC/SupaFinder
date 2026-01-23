"""Lightweight database cleanup functions for automatic cleanup."""

import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from app.config import CACHE_DB, get_secret
from app.db_cloud import get_db_connection


def auto_cleanup_page_cache(
    db_path: Optional[Path] = None,
    keep_days: int = 0,
    max_cache_entries: Optional[int] = None
) -> dict:
    """
    Lightweight automatic cleanup of page_cache.
    
    This function:
    - Deletes old page_cache entries (if keep_days > 0)
    - Or deletes all page_cache if keep_days = 0
    - Optionally limits cache size to max_cache_entries
    
    Note: This is a lightweight cleanup that only deletes cache entries.
    For full cleanup including VACUUM, use scripts/cleanup_database.py
    
    Args:
        db_path: Database path (default: CACHE_DB)
        keep_days: Keep cache entries newer than this many days (0 = delete all)
        max_cache_entries: Maximum number of cache entries to keep (None = no limit)
    
    Returns:
        dict with cleanup statistics: {'deleted': int, 'before_count': int, 'after_count': int}
    """
    if db_path is None:
        db_path = CACHE_DB
    
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    stats = {
        'deleted': 0,
        'before_count': 0,
        'after_count': 0
    }
    
    try:
        # Get current count
        cursor.execute("SELECT COUNT(*) FROM page_cache")
        stats['before_count'] = cursor.fetchone()[0]
        
        if stats['before_count'] == 0:
            # No cache to clean
            conn.close()
            return stats
        
        # Delete based on keep_days
        if keep_days > 0:
            cutoff_date = (datetime.now() - timedelta(days=keep_days)).isoformat()
            cursor.execute(
                "DELETE FROM page_cache WHERE datetime(fetched_at) < datetime(?)",
                (cutoff_date,)
            )
            stats['deleted'] = cursor.rowcount
            conn.commit()
        else:
            # Delete all cache
            cursor.execute("DELETE FROM page_cache")
            stats['deleted'] = cursor.rowcount
            conn.commit()
        
        # Optionally limit cache size (only if keep_days > 0, since keep_days=0 deletes all)
        if keep_days > 0 and max_cache_entries is not None and max_cache_entries > 0:
            cursor.execute("SELECT COUNT(*) FROM page_cache")
            current_count = cursor.fetchone()[0]
            
            if current_count > max_cache_entries:
                # Delete oldest entries
                cursor.execute("""
                    DELETE FROM page_cache 
                    WHERE url IN (
                        SELECT url FROM page_cache 
                        ORDER BY fetched_at ASC 
                        LIMIT ?
                    )
                """, (current_count - max_cache_entries,))
                additional_deleted = cursor.rowcount
                stats['deleted'] += additional_deleted
                conn.commit()
        
        # Get final count
        cursor.execute("SELECT COUNT(*) FROM page_cache")
        stats['after_count'] = cursor.fetchone()[0]
        
    except Exception as e:
        # Don't raise - cleanup is optional
        # Silently fail to avoid disrupting main flow
        pass
    finally:
        conn.close()
    
    return stats


def auto_cleanup_evidence_snippets(
    db_path: Optional[Path] = None,
    clear_all: bool = False
) -> dict:
    """
    Clear evidence_snippets_json to save space.
    
    Args:
        db_path: Database path (default: CACHE_DB)
        clear_all: If True, clear all evidence snippets. If False, only clear non-empty ones.
    
    Returns:
        dict with cleanup statistics
    """
    if db_path is None:
        db_path = CACHE_DB
    
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    stats = {
        'cleared': 0
    }
    
    try:
        if clear_all:
            cursor.execute("UPDATE supervisors SET evidence_snippets_json = '[]' WHERE evidence_snippets_json IS NOT NULL")
        else:
            cursor.execute("UPDATE supervisors SET evidence_snippets_json = '[]' WHERE evidence_snippets_json IS NOT NULL AND evidence_snippets_json != '[]'")
        
        stats['cleared'] = cursor.rowcount
        conn.commit()
    except Exception as e:
        print(f"Warning: Evidence cleanup failed: {e}")
    finally:
        conn.close()
    
    return stats


def should_run_cleanup(
    last_cleanup_time: Optional[datetime] = None,
    min_interval_hours: int = 24,
    cache_threshold: int = 1000
) -> bool:
    """
    Determine if cleanup should run based on time and cache size.
    
    Args:
        last_cleanup_time: Last cleanup timestamp
        min_interval_hours: Minimum hours between cleanups
        cache_threshold: Run cleanup if cache has more than this many entries
    
    Returns:
        bool: True if cleanup should run
    """
    # Check cache size threshold
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM page_cache")
        cache_count = cursor.fetchone()[0]
        conn.close()
        
        if cache_count > cache_threshold:
            return True
    except:
        pass
    
    # Check time interval
    if last_cleanup_time is None:
        return True
    
    time_since_cleanup = datetime.now() - last_cleanup_time
    if time_since_cleanup.total_seconds() / 3600 >= min_interval_hours:
        return True
    
    return False

