"""Clean up old cache data to reduce database size."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from app.config import CACHE_DB


def cleanup_old_cache(
    page_cache_days: int = 30,
    extracted_profiles_days: int = 90,
    keep_supervisors: bool = True
) -> None:
    """
    Clean up old cache data to reduce database size.
    
    Args:
        page_cache_days: Delete page cache older than this many days (default: 30)
        extracted_profiles_days: Delete extracted profiles older than this many days (default: 90)
        keep_supervisors: If True, never delete supervisors (default: True)
    """
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    print("Cleaning up old cache data...")
    print(f"  Page cache retention: {page_cache_days} days")
    print(f"  Extracted profiles retention: {extracted_profiles_days} days")
    print(f"  Keep supervisors: {keep_supervisors}")
    print()
    
    # Get initial sizes
    cursor.execute("SELECT COUNT(*) FROM page_cache")
    initial_page_cache = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM extracted_profiles")
    initial_extracted = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM supervisors")
    supervisors_count = cursor.fetchone()[0]
    
    print(f"Initial counts:")
    print(f"  Page cache: {initial_page_cache}")
    print(f"  Extracted profiles: {initial_extracted}")
    print(f"  Supervisors: {supervisors_count}")
    print()
    
    # Clean page cache
    cutoff_date = (datetime.now() - timedelta(days=page_cache_days)).isoformat()
    cursor.execute("DELETE FROM page_cache WHERE fetched_at < ?", (cutoff_date,))
    deleted_page_cache = cursor.rowcount
    print(f"Deleted {deleted_page_cache} old page cache entries")
    
    # Clean extracted profiles
    cutoff_date = (datetime.now() - timedelta(days=extracted_profiles_days)).isoformat()
    cursor.execute("DELETE FROM extracted_profiles WHERE extracted_at < ?", (cutoff_date,))
    deleted_extracted = cursor.rowcount
    print(f"Deleted {deleted_extracted} old extracted profiles")
    
    # Vacuum to reclaim space
    print("\nVacuuming database to reclaim space...")
    cursor.execute("VACUUM")
    
    conn.commit()
    conn.close()
    
    # Get final size
    db_size = CACHE_DB.stat().st_size / (1024 * 1024)  # Size in MB
    print(f"\n✓ Cleanup complete!")
    print(f"  Database size: {db_size:.2f} MB")
    print(f"  Supervisors preserved: {supervisors_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up old cache data")
    parser.add_argument("--page-cache-days", type=int, default=30,
                       help="Delete page cache older than N days (default: 30)")
    parser.add_argument("--extracted-days", type=int, default=90,
                       help="Delete extracted profiles older than N days (default: 90)")
    parser.add_argument("--delete-supervisors", action="store_true",
                       help="Also delete old supervisors (default: keep all)")
    
    args = parser.parse_args()
    
    cleanup_old_cache(
        page_cache_days=args.page_cache_days,
        extracted_profiles_days=args.extracted_days,
        keep_supervisors=not args.delete_supervisors
    )

