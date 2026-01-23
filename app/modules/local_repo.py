"""Local repository for supervisor profiles."""

import sqlite3
import json
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from app.config import CACHE_DB, get_secret
from app.schemas import SupervisorProfile, SupervisorRecordDB
from app.modules.utils_identity import compute_canonical_id
from app.db_cloud import get_db_connection


def _is_postgresql(conn) -> bool:
    """Check if connection is PostgreSQL.
    
    Uses multiple methods for reliable detection:
    1. Check DB_TYPE from config (most reliable)
    2. Check connection module name
    3. Try PostgreSQL-specific query as last resort
    """
    # First, check DB_TYPE from config (most reliable, no query needed)
    from app.config import get_secret
    db_type = get_secret("DB_TYPE", "sqlite").lower()
    if db_type == "postgresql":
        return True
    
    # Second, check connection module name
    try:
        module_name = conn.__class__.__module__
        if 'psycopg2' in module_name or 'psycopg' in module_name:
            return True
    except Exception:
        pass
    
    # Last resort: try PostgreSQL-specific query (but this might fail on SQLite)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        if isinstance(version, str) and "PostgreSQL" in version:
            return True
    except Exception:
        # If query fails, assume SQLite
        pass
    
    # Default: assume SQLite
    return False


def upsert_supervisor(profile: SupervisorProfile, domain: Optional[str] = None) -> None:
    """
    Upsert a single supervisor profile to the local database.
    
    Logic:
    - Compute canonical_id
    - If exists: update last_seen_at, merge fields (don't overwrite non-empty with empty)
    - If new: insert
    - Update last_verified_at if email confidence is high/medium
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Compute canonical_id
    canonical_id = compute_canonical_id(
        email=profile.email,
        name=profile.name,
        institution=profile.institution,
        domain=domain,
        profile_url=profile.profile_url
    )
    
    # Check if exists
    cursor.execute("SELECT id, email, title, homepage, profile_url FROM supervisors WHERE canonical_id = ?", (canonical_id,))
    existing = cursor.fetchone()
    
    now = datetime.now().isoformat()
    evidence_snippets_json = json.dumps(profile.evidence_snippets)
    keywords_json = json.dumps(profile.keywords)
    keywords_text = ", ".join(profile.keywords) if profile.keywords else ""
    
    if existing:
        # Update existing record
        existing_id, existing_email, existing_title, existing_homepage, existing_profile_url = existing
        
        # Merge logic: don't overwrite non-empty with empty
        final_email = profile.email if profile.email else existing_email
        final_title = profile.title if profile.title else existing_title
        final_homepage = profile.homepage_url if profile.homepage_url else existing_homepage
        final_profile_url = profile.profile_url if profile.profile_url else existing_profile_url
        
        # Update last_verified_at if email confidence is high/medium
        last_verified_at = now if profile.email_confidence in ["high", "medium"] else None
        if existing[0]:  # If there was a previous verification, keep it if new one is None
            cursor.execute("SELECT last_verified_at FROM supervisors WHERE id = ?", (existing_id,))
            prev_verified = cursor.fetchone()
            if prev_verified and prev_verified[0] and not last_verified_at:
                last_verified_at = prev_verified[0]
        
        cursor.execute("""
            UPDATE supervisors SET
                name = ?,
                title = ?,
                institution = ?,
                domain = ?,
                country = ?,
                region = ?,
                email = ?,
                email_confidence = ?,
                homepage = ?,
                profile_url = ?,
                source_url = ?,
                evidence_email = ?,
                evidence_snippets_json = ?,
                keywords_json = ?,
                keywords_text = ?,
                last_seen_at = ?,
                last_verified_at = ?,
                updated_at = ?
            WHERE canonical_id = ?
        """, (
            profile.name,
            final_title,
            profile.institution,
            domain,
            profile.country,
            profile.region,
            final_email,
            profile.email_confidence,
            final_homepage,
            final_profile_url,
            profile.source_url,
            profile.evidence_snippets[0] if profile.evidence_snippets else None,
            evidence_snippets_json,
            keywords_json,
            keywords_text,
            now,
            last_verified_at,
            now,
            canonical_id
        ))
    else:
        # Insert new record
        last_verified_at = now if profile.email_confidence in ["high", "medium"] else None
        
        cursor.execute("""
            INSERT INTO supervisors (
                canonical_id, name, title, institution, domain, country, region,
                email, email_confidence, homepage, profile_url, source_url,
                evidence_email, evidence_snippets_json, keywords_json, keywords_text,
                last_seen_at, last_verified_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            canonical_id,
            profile.name,
            profile.title,
            profile.institution,
            domain,
            profile.country,
            profile.region,
            profile.email,
            profile.email_confidence,
            profile.homepage_url,
            profile.profile_url,
            profile.source_url,
            profile.evidence_snippets[0] if profile.evidence_snippets else None,
            evidence_snippets_json,
            keywords_json,
            keywords_text,
            now,
            last_verified_at,
            now,
            now
        ))
    
    conn.commit()
    conn.close()


def upsert_many(profiles: List[SupervisorProfile], domain: Optional[str] = None) -> None:
    """
    Upsert multiple supervisor profiles.
    
    After batch update, automatically runs lightweight cleanup to keep database size manageable.
    """
    for profile in profiles:
        upsert_supervisor(profile, domain)
    
    # Auto cleanup after batch update (lightweight - only page_cache)
    # This helps keep database size manageable without running expensive VACUUM
    try:
        from app.modules.db_cleanup import auto_cleanup_page_cache
        
        # Only cleanup if we have a significant number of profiles (>= 10)
        # This avoids cleanup overhead for small updates
        if len(profiles) >= 10:
            # Delete all page_cache entries (they can be regenerated during searches)
            # Limit cache to 500 entries max to prevent database bloat
            cleanup_stats = auto_cleanup_page_cache(keep_days=0, max_cache_entries=500)
            if cleanup_stats.get('deleted', 0) > 0:
                # Optional: log cleanup (commented out to avoid noise)
                # print(f"Auto cleanup: deleted {cleanup_stats['deleted']} page_cache entries")
                pass
    except Exception:
        # Don't fail if cleanup fails - it's optional and shouldn't break the main flow
        pass


def query_candidates(
    research_profile,
    constraints: Optional[dict] = None,
    limit: int = 800,
    debug: bool = False
) -> List[SupervisorProfile]:
    """
    Query candidates from local database.
    
    Args:
        research_profile: ResearchProfile object with core_keywords and adjacent_keywords
        constraints: Dict with optional keys: regions (list), countries (list), qs_min (int), qs_max (int), country (str, deprecated, use countries)
        limit: Maximum number of candidates to return
        debug: If True, print debug information
    
    Returns:
        List of SupervisorProfile objects (from_local_db=True)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check database type early for parameter placeholder
    is_pg = _is_postgresql(conn)
    param_placeholder = "%s" if is_pg else "?"
    
    # Build WHERE clause
    where_clauses = []
    params = []
    
    if constraints:
        if "regions" in constraints and constraints["regions"]:
            placeholders = ",".join([param_placeholder] * len(constraints["regions"]))
            where_clauses.append(f"LOWER(region) IN ({placeholders})")
            params.extend([r.strip().lower() for r in constraints["regions"]])
            if debug:
                print(f"  [DEBUG] Region filter: {constraints['regions']}")
        
        # Support both "countries" (list) and "country" (single, for backward compatibility)
        if "countries" in constraints and constraints["countries"]:
            placeholders = ",".join([param_placeholder] * len(constraints["countries"]))
            where_clauses.append(f"LOWER(country) IN ({placeholders})")
            params.extend([c.strip().lower() for c in constraints["countries"]])
            if debug:
                print(f"  [DEBUG] Country filter: {constraints['countries']}")
        elif "country" in constraints and constraints["country"]:
            # Backward compatibility: single country
            where_clauses.append(f"LOWER(country) = {param_placeholder}")
            params.append(constraints["country"].strip().lower())
            if debug:
                print(f"  [DEBUG] Country filter (single): {constraints['country']}")
        
        # NOTE: QS rank filtering is done in Python after query, not in SQL
        # because the supervisors table doesn't have qs_rank column
        # We'll filter by matching institution names to universities list
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Build keyword search
    all_keywords = research_profile.core_keywords + research_profile.adjacent_keywords
    if debug:
        print(f"  [DEBUG] Total keywords: {len(all_keywords)} (core: {len(research_profile.core_keywords)}, adjacent: {len(research_profile.adjacent_keywords)})")
        print(f"  [DEBUG] Keywords: {all_keywords[:10]}")
        print(f"  [DEBUG] Database type: {'PostgreSQL' if is_pg else 'SQLite'}")
    
    if not all_keywords:
        # No keywords, just return all matching constraints
        query = f"""
            SELECT * FROM supervisors
            WHERE {where_sql}
            ORDER BY last_seen_at DESC
            LIMIT {param_placeholder}
        """
        params.append(limit)
        if debug:
            print(f"  [DEBUG] Query (no keywords): {query}")
            print(f"  [DEBUG] Params: {params}")
        cursor.execute(query, params)
    else:
        # Try FTS5 search first, fallback to LIKE
        search_terms = " OR ".join([f'"{kw}"' for kw in all_keywords[:10]])  # Limit to 10 terms
        
        # PostgreSQL doesn't support SQLite FTS5, always use LIKE for PostgreSQL
        # For SQLite, try FTS5 first, fallback to LIKE
        fts_exists = False
        
        # Only check for FTS5 on SQLite (never on PostgreSQL)
        # Double-check is_pg to be absolutely sure
        if not is_pg:
            # Verify it's really SQLite by checking connection type again
            try:
                module_name = conn.__class__.__module__
                if 'sqlite' in module_name.lower():
                    # SQLite only: Check if FTS5 table exists
                    try:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='supervisors_fts'")
                        fts_exists = cursor.fetchone() is not None
                    except Exception:
                        # If query fails, FTS5 is not available
                        fts_exists = False
            except Exception:
                # If we can't verify, don't use FTS5
                fts_exists = False
        
        if fts_exists and not is_pg:
            # Try FTS5 (SQLite only)
            try:
                fts_query = f"""
                    SELECT DISTINCT s.* FROM supervisors s
                    INNER JOIN supervisors_fts ON s.id = supervisors_fts.rowid
                    WHERE {where_sql} AND supervisors_fts MATCH {param_placeholder}
                    ORDER BY s.last_seen_at DESC
                    LIMIT {param_placeholder}
                """
                params_fts = params + [search_terms, limit]
                if debug:
                    print(f"  [DEBUG] Using FTS5 search (SQLite)")
                    print(f"  [DEBUG] Query: {fts_query}")
                    print(f"  [DEBUG] Search terms: {search_terms}")
                    print(f"  [DEBUG] Params: {params_fts}")
                cursor.execute(fts_query, params_fts)
            except Exception as e:
                if debug:
                    print(f"  [DEBUG] FTS5 query failed: {e}, falling back to LIKE")
                # Fall through to LIKE search
                fts_exists = False
        
        if not fts_exists:
            # Use LIKE search (works for both SQLite and PostgreSQL)
            if debug:
                print(f"  [DEBUG] Using LIKE search ({'PostgreSQL' if is_pg else 'SQLite'})")
            
            # Use appropriate parameter placeholder for database type
            like_patterns = " OR ".join([f"LOWER(keywords_text) LIKE {param_placeholder}" for _ in all_keywords[:10]])
            query = f"""
                SELECT * FROM supervisors
                WHERE {where_sql} AND ({like_patterns})
                ORDER BY last_seen_at DESC
                LIMIT {param_placeholder}
            """
            like_params = params + [f"%{kw.lower()}%" for kw in all_keywords[:10]] + [limit]
            if debug:
                print(f"  [DEBUG] Query (LIKE): {query}")
                print(f"  [DEBUG] Params: {like_params}")
            cursor.execute(query, like_params)
    
    rows = cursor.fetchall()
    if debug:
        print(f"  [DEBUG] Found {len(rows)} rows from database")
    conn.close()
    
    # Convert to SupervisorProfile
    profiles = []
    for row in rows:
        record = SupervisorRecordDB(
            id=row[0],
            canonical_id=row[1],
            name=row[2],
            title=row[3],
            institution=row[4],
            domain=row[5],
            country=row[6],
            region=row[7],
            email=row[8],
            email_confidence=row[9],
            homepage=row[10],
            profile_url=row[11],
            source_url=row[12],
            evidence_email=row[13],
            evidence_snippets_json=row[14],
            keywords_json=row[15],
            keywords_text=row[16],
            last_seen_at=row[17],
            last_verified_at=row[18],
            created_at=row[19],
            updated_at=row[20]
        )
        profiles.append(record.to_supervisor_profile())
    
    return profiles

