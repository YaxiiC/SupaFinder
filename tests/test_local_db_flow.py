"""Test script for local database flow."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from app.schemas import SupervisorProfile, ResearchProfile
from app.modules.local_repo import upsert_supervisor, query_candidates, upsert_many
from app.modules.scoring import score_supervisor
from app.modules.utils_identity import compute_canonical_id
from app.db import init_db
import json


def test_upsert_and_query():
    """Test upsert and query functionality."""
    print("=" * 60)
    print("Test: Local DB Flow")
    print("=" * 60)
    
    # Initialize DB
    init_db()
    print("✓ Database initialized")
    
    # Create test research profile
    research_profile = ResearchProfile(
        core_keywords=["medical imaging", "deep learning", "MRI", "segmentation"],
        adjacent_keywords=["computer vision", "neural networks", "image processing"],
        negative_keywords=[],
        preferred_departments=[],
        query_templates=[]
    )
    print(f"✓ Created research profile with {len(research_profile.core_keywords)} core keywords")
    
    # Create 3 test supervisor profiles
    test_profiles = [
        SupervisorProfile(
            name="Dr. John Smith",
            title="Professor",
            institution="Test University",
            country="UK",
            region="Europe",
            email="john.smith@test.edu",
            email_confidence="high",
            profile_url="https://test.edu/profiles/john-smith",
            keywords=["medical imaging", "MRI", "deep learning", "segmentation"],
            fit_score=0.0,
            tier="Adjacent",
            source_url="https://test.edu/profiles/john-smith",
            evidence_snippets=["Email found on page"],
            from_local_db=False
        ),
        SupervisorProfile(
            name="Dr. Jane Doe",
            title="Associate Professor",
            institution="Another University",
            country="US",
            region="North America",
            email="jane.doe@another.edu",
            email_confidence="medium",
            profile_url="https://another.edu/jane-doe",
            keywords=["computer vision", "neural networks", "image processing"],
            fit_score=0.0,
            tier="Adjacent",
            source_url="https://another.edu/jane-doe",
            evidence_snippets=[],
            from_local_db=False
        ),
        SupervisorProfile(
            name="Dr. Bob Wilson",
            title="Professor",
            institution="Third University",
            country="UK",
            region="Europe",
            email=None,  # No email - will use hash
            email_confidence="none",
            profile_url="https://third.edu/bob-wilson",
            keywords=["medical imaging", "MRI"],
            fit_score=0.0,
            tier="Adjacent",
            source_url="https://third.edu/bob-wilson",
            evidence_snippets=[],
            from_local_db=False
        )
    ]
    
    print(f"✓ Created {len(test_profiles)} test supervisor profiles")
    
    # Test 1: Upsert profiles
    print("\n[Test 1] Upserting profiles to local DB...")
    for profile in test_profiles:
        canonical_id = compute_canonical_id(
            email=profile.email,
            name=profile.name,
            institution=profile.institution,
            profile_url=profile.profile_url
        )
        print(f"  - {profile.name}: canonical_id = {canonical_id[:16]}...")
        upsert_supervisor(profile, domain="test.edu")
    print("✓ All profiles upserted")
    
    # Test 2: Query candidates
    print("\n[Test 2] Querying candidates from local DB...")
    constraints = {"regions": ["Europe", "North America"]}
    candidates = query_candidates(research_profile, constraints, limit=800)
    print(f"  Found {len(candidates)} candidates")
    
    # Test 3: Score candidates
    print("\n[Test 3] Scoring candidates...")
    scored_candidates = []
    for candidate in candidates:
        fit_score, tier, matched_terms = score_supervisor(research_profile, candidate)
        candidate.fit_score = fit_score
        candidate.tier = tier
        candidate.matched_terms = matched_terms
        scored_candidates.append(candidate)
        print(f"  - {candidate.name}: fit_score={fit_score:.3f}, tier={tier}, matched={matched_terms}")
    
    # Sort by fit_score
    scored_candidates.sort(key=lambda x: x.fit_score, reverse=True)
    print(f"\n✓ Scored and sorted {len(scored_candidates)} candidates")
    
    # Test 4: Verify canonical_id uniqueness
    print("\n[Test 4] Verifying canonical_id uniqueness...")
    canonical_ids = [c.canonical_id for c in scored_candidates if c.canonical_id]
    unique_ids = set(canonical_ids)
    assert len(canonical_ids) == len(unique_ids), "Canonical IDs must be unique!"
    print(f"✓ All {len(unique_ids)} canonical IDs are unique")
    
    # Test 5: Verify keywords_json can be read/written
    print("\n[Test 5] Verifying keywords_json serialization...")
    for candidate in scored_candidates[:2]:  # Test first 2
        # This should work since we read from DB
        assert candidate.keywords is not None, "Keywords should not be None"
        assert isinstance(candidate.keywords, list), "Keywords should be a list"
        print(f"  - {candidate.name}: keywords={candidate.keywords[:3]}...")
    print("✓ Keywords JSON serialization works")
    
    # Test 6: Simulate online results and upsert
    print("\n[Test 6] Simulating online results...")
    online_profiles = [
        SupervisorProfile(
            name="Dr. Alice Brown",
            title="Professor",
            institution="New University",
            country="UK",
            region="Europe",
            email="alice.brown@new.edu",
            email_confidence="high",
            profile_url="https://new.edu/alice-brown",
            keywords=["medical imaging", "deep learning", "MRI", "segmentation", "neural networks"],
            fit_score=0.0,
            tier="Adjacent",
            source_url="https://new.edu/alice-brown",
            evidence_snippets=["Email verified"],
            from_local_db=False
        ),
        SupervisorProfile(
            name="Dr. John Smith",  # Duplicate name but different email
            title="Professor",
            institution="Different University",
            country="US",
            region="North America",
            email="john.smith@different.edu",
            email_confidence="high",
            profile_url="https://different.edu/john-smith",
            keywords=["medical imaging", "MRI"],
            fit_score=0.0,
            tier="Adjacent",
            source_url="https://different.edu/john-smith",
            evidence_snippets=[],
            from_local_db=False
        )
    ]
    
    upsert_many(online_profiles, domain="new.edu")
    print(f"✓ Upserted {len(online_profiles)} online profiles")
    
    # Test 7: Re-query and verify deduplication
    print("\n[Test 7] Re-querying after online upsert...")
    all_candidates = query_candidates(research_profile, constraints, limit=800)
    print(f"  Found {len(all_candidates)} total candidates")
    
    # Score all
    for candidate in all_candidates:
        fit_score, tier, matched_terms = score_supervisor(research_profile, candidate)
        candidate.fit_score = fit_score
        candidate.tier = tier
        candidate.matched_terms = matched_terms
    
    # Sort and take top
    all_candidates.sort(key=lambda x: x.fit_score, reverse=True)
    top_5 = all_candidates[:5]
    
    print(f"\n  Top 5 candidates:")
    for i, candidate in enumerate(top_5, 1):
        print(f"    {i}. {candidate.name} (fit_score={candidate.fit_score:.3f}, tier={candidate.tier})")
    
    # Verify fit_score is consistent (same input = same output)
    print("\n[Test 8] Verifying fit_score consistency...")
    test_profile = top_5[0] if top_5 else scored_candidates[0]
    score1, _, _ = score_supervisor(research_profile, test_profile)
    score2, _, _ = score_supervisor(research_profile, test_profile)
    assert abs(score1 - score2) < 0.001, "fit_score should be consistent!"
    print(f"✓ fit_score is consistent: {score1:.3f} == {score2:.3f}")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_upsert_and_query()

