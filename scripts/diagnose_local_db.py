#!/usr/bin/env python3
"""Diagnostic script to check why local database queries return 0 results."""

import sys
from pathlib import Path
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import CACHE_DB
from app.schemas import ResearchProfile
from app.modules.local_repo import query_candidates

def diagnose_local_db():
    """Diagnose local database query issues."""
    print("=" * 60)
    print("Local Database Diagnostic Tool")
    print("=" * 60)
    print()
    
    # Check if database exists
    if not CACHE_DB.exists():
        print(f"❌ Database file not found: {CACHE_DB}")
        return
    
    print(f"✓ Database file exists: {CACHE_DB}")
    
    # Connect and check total records
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM supervisors")
    total_count = cursor.fetchone()[0]
    print(f"✓ Total records in database: {total_count}")
    print()
    
    if total_count == 0:
        print("❌ Database is empty. No records to query.")
        return
    
    # Check regions and countries
    print("Available regions and countries:")
    cursor.execute("""
        SELECT region, country, COUNT(*) as cnt 
        FROM supervisors 
        GROUP BY region, country 
        ORDER BY cnt DESC
    """)
    for row in cursor.fetchall():
        region, country, count = row
        print(f"  - {region or 'NULL'} / {country or 'NULL'}: {count} records")
    print()
    
    # Check sample keywords
    print("Sample keywords from database:")
    cursor.execute("SELECT keywords_text FROM supervisors LIMIT 5")
    for row in cursor.fetchall():
        keywords = row[0]
        if keywords:
            print(f"  - {keywords[:80]}...")
    print()
    
    # Test query with no constraints
    print("Test 1: Query with no constraints and no keywords")
    test_profile = ResearchProfile(core_keywords=[], adjacent_keywords=[])
    results = query_candidates(test_profile, None, limit=10, debug=True)
    print(f"  Result: {len(results)} candidates")
    print()
    
    # Test query with sample keywords
    print("Test 2: Query with sample keywords (medical imaging)")
    test_profile2 = ResearchProfile(
        core_keywords=["medical imaging", "machine learning"],
        adjacent_keywords=["AI", "deep learning"]
    )
    results2 = query_candidates(test_profile2, None, limit=10, debug=True)
    print(f"  Result: {len(results2)} candidates")
    print()
    
    # Test with region constraint
    print("Test 3: Query with region constraint (Europe)")
    results3 = query_candidates(test_profile2, {"regions": ["Europe"]}, limit=10, debug=True)
    print(f"  Result: {len(results3)} candidates")
    print()
    
    # Test with country constraint
    print("Test 4: Query with country constraint (United Kingdom)")
    results4 = query_candidates(test_profile2, {"countries": ["United Kingdom"]}, limit=10, debug=True)
    print(f"  Result: {len(results4)} candidates")
    print()
    
    # Check FTS5 table
    print("FTS5 Table Status:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='supervisors_fts'")
    fts_exists = cursor.fetchone() is not None
    if fts_exists:
        print("  ✓ FTS5 table exists")
        cursor.execute("SELECT COUNT(*) FROM supervisors_fts")
        fts_count = cursor.fetchone()[0]
        print(f"  ✓ FTS5 table has {fts_count} entries")
    else:
        print("  ⚠ FTS5 table does not exist (will use LIKE search)")
    print()
    
    conn.close()
    
    print("=" * 60)
    print("Diagnostic Complete")
    print("=" * 60)

if __name__ == "__main__":
    diagnose_local_db()

