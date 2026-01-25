"""Relevance scoring and tiering."""

from typing import List, Tuple
from app.schemas import SupervisorProfile, ResearchProfile
from app.config import CORE_THRESHOLD, ADJACENT_THRESHOLD


def score_and_tier(profiles: List[SupervisorProfile]) -> List[SupervisorProfile]:
    """
    Apply tier labels based on fit scores.
    Uses a hybrid approach: absolute threshold + percentile-based for better distribution.
    """
    if not profiles:
        return profiles
    
    # Extract all fit scores
    scores = [p.fit_score for p in profiles]
    
    # Calculate percentile thresholds for better distribution
    # Use top 35% as Core (ensures at least ~35% are Core if scores are decent)
    sorted_scores = sorted(scores, reverse=True)
    n = len(scores)
    
    # Top 35% threshold - the score at 35th position from top
    # For n=64, this would be scores[22], meaning top 22 (34%) would be Core
    percentile_core_idx = int(n * 0.35) if n > 2 else 0
    percentile_core_threshold = sorted_scores[percentile_core_idx] if n > 0 else 0.0
    
    # Use the LOWER of absolute threshold or percentile threshold
    # This ensures we get enough Core supervisors (at least ~35% if scores allow)
    # If percentile threshold is lower than absolute, use it for more Core
    effective_core_threshold = min(CORE_THRESHOLD, percentile_core_threshold) if percentile_core_threshold > 0 else CORE_THRESHOLD
    
    # Apply tiering
    for profile in profiles:
        if profile.fit_score >= effective_core_threshold:
            profile.tier = "Core"
        elif profile.fit_score >= ADJACENT_THRESHOLD:
            profile.tier = "Adjacent"
        else:
            profile.tier = "Adjacent"  # Keep as Adjacent for low scores too
    
    return profiles


def rank_profiles(profiles: List[SupervisorProfile]) -> List[SupervisorProfile]:
    """Rank profiles: Core first, then by fit score."""
    return sorted(
        profiles,
        key=lambda p: (0 if p.tier == "Core" else 1, -p.fit_score)
    )


def select_top_n(profiles: List[SupervisorProfile], n: int = 100) -> List[SupervisorProfile]:
    """Select top N profiles, prioritizing Core tier."""
    # First filter out profiles with fit_score = 0 or very low (not relevant at all)
    # Also filter out profiles with no matched terms (likely from wrong field)
    filtered_profiles = [
        p for p in profiles 
        if p.fit_score > 0.15 and len(p.matched_terms) > 0  # Must have some relevance and matched terms
    ]
    
    scored = score_and_tier(filtered_profiles)
    ranked = rank_profiles(scored)
    return ranked[:n]


def select_with_diversity(
    profiles: List[SupervisorProfile], 
    n: int = 100, 
    max_per_institution: int = 10,
    min_institutions: int = 1,
    strict_limit: bool = False
) -> List[SupervisorProfile]:
    """
    Select top N profiles with diversity constraint: maximum M profiles per institution.
    Ensures minimum coverage of institutions if specified.
    
    STRICTLY enforces target count by:
    1. Progressively lowering fit_score threshold
    2. Relaxing matched_terms requirement if needed
    3. Relaxing diversity constraint (max_per_institution) if needed (unless strict_limit=True)
    4. If still not enough, returns all available profiles up to target (with strict limit applied)
    
    Args:
        profiles: List of supervisor profiles (should be pre-scored and ranked)
        n: Total number of profiles to select (TARGET - must be met if possible)
        max_per_institution: Maximum number of profiles per institution (relaxed if needed, unless strict_limit=True)
        min_institutions: Minimum number of institutions to cover (default: 1, meaning no minimum requirement)
        strict_limit: If True, strictly enforce max_per_institution limit, never exceed it
    
    Returns:
        List of selected profiles with diversity constraint applied (as close to n as possible)
    """
    if not profiles:
        return []
    
    # Strategy 1: Try with matched_terms requirement and diversity constraint
    thresholds = [0.15, 0.1, 0.05, 0.0]
    # If strict_limit is True, never relax max_per_institution; otherwise allow relaxation
    if strict_limit:
        max_per_inst_options = [max_per_institution]  # Only use the strict limit
    else:
        max_per_inst_options = [max_per_institution, max_per_institution * 2, max_per_institution * 5, None]  # None = no limit
    
    best_result = []
    
    for threshold in thresholds:
        for max_per_inst in max_per_inst_options:
            # Filter profiles based on current threshold
            # Start with matched_terms requirement
            filtered_profiles = [
                p for p in profiles 
                if p.fit_score > threshold and len(p.matched_terms) > 0
            ]
            
            if len(filtered_profiles) == 0:
                continue  # Try next threshold
            
            # We have some candidates, proceed with selection
            scored = score_and_tier(filtered_profiles)
            ranked = rank_profiles(scored)
            
            # Apply diversity constraint
            selected = []
            institution_count = {}  # Track count per institution
            unique_institutions = set()  # Track unique institutions
            
            # First pass: Try to ensure minimum institutions coverage
            if min_institutions > 1:
                by_institution = {}
                for profile in ranked:
                    institution = profile.institution.lower().strip() if profile.institution else ""
                    if institution not in by_institution:
                        by_institution[institution] = []
                    by_institution[institution].append(profile)
                
                institutions_sorted = sorted(
                    by_institution.keys(),
                    key=lambda inst: max(p.fit_score for p in by_institution[inst]) if by_institution[inst] else 0,
                    reverse=True
                )
                
                for institution in institutions_sorted[:min_institutions]:
                    if len(selected) < n and by_institution[institution]:
                        profile = by_institution[institution][0]
                        selected.append(profile)
                        institution_count[institution] = 1
                        unique_institutions.add(institution)
            
            # Second pass: Fill remaining slots with diversity constraint
            for profile in ranked:
                if profile in selected:
                    continue
                    
                institution = profile.institution.lower().strip() if profile.institution else ""
                current_count = institution_count.get(institution, 0)
                
                if len(selected) < n:
                    # Apply diversity constraint (or skip if max_per_inst is None)
                    if max_per_inst is None or current_count < max_per_inst:
                        selected.append(profile)
                        institution_count[institution] = current_count + 1
                        unique_institutions.add(institution)
                
                # Update best result if this is better
                if len(selected) > len(best_result):
                    best_result = selected
                
                # If we reached target count, return immediately
                if len(selected) >= n:
                    return selected
    
    # Strategy 2: If still not enough, relax matched_terms requirement
    if len(best_result) < n:
        for threshold in thresholds:
            for max_per_inst in max_per_inst_options:
                # Remove matched_terms requirement
                filtered_profiles = [
                    p for p in profiles 
                    if p.fit_score > threshold
                ]
                
                if len(filtered_profiles) == 0:
                    continue
                
                scored = score_and_tier(filtered_profiles)
                ranked = rank_profiles(scored)
                
                selected = []
                institution_count = {}
                unique_institutions = set()
                
                # Apply diversity constraint (relaxed)
                for profile in ranked:
                    if len(selected) >= n:
                        break
                    
                    institution = profile.institution.lower().strip() if profile.institution else ""
                    current_count = institution_count.get(institution, 0)
                    
                    if max_per_inst is None or current_count < max_per_inst:
                        selected.append(profile)
                        institution_count[institution] = current_count + 1
                        unique_institutions.add(institution)
                
                if len(selected) > len(best_result):
                    best_result = selected
                
                if len(selected) >= n:
                    return selected
    
    # Strategy 3: If still not enough, return top N with diversity constraint applied
    if len(best_result) < n:
        # Take top N by score, but still apply diversity constraint if strict_limit is True
        scored = score_and_tier(profiles)
        ranked = rank_profiles(scored)
        
        if strict_limit:
            # First try with strict limit
            selected = []
            institution_count = {}
            for profile in ranked:
                if len(selected) >= n:
                    break
                institution = profile.institution.lower().strip() if profile.institution else ""
                current_count = institution_count.get(institution, 0)
                if current_count < max_per_institution:
                    selected.append(profile)
                    institution_count[institution] = current_count + 1
            
            # If we still don't have enough and there are enough candidates available,
            # calculate the minimum per-institution limit needed to reach target
            if len(selected) < n and len(ranked) >= n:
                # Count unique institutions in top candidates
                unique_institutions = set()
                for profile in ranked[:min(n * 2, len(ranked))]:  # Check first 2n profiles or all if less
                    inst = profile.institution.lower().strip() if profile.institution else ""
                    if inst:  # Only count non-empty institutions
                        unique_institutions.add(inst)
                
                num_institutions = len(unique_institutions)
                if num_institutions > 0:
                    # Calculate needed per-institution limit to reach target
                    needed_per_inst = (n + num_institutions - 1) // num_institutions  # Ceiling division
                    # If we have enough candidates to meet target, use the calculated limit
                    # But cap it at a reasonable maximum (e.g., n/2 to ensure some diversity)
                    max_reasonable = max(n // 2, max_per_institution * 2)  # At least 2x original, or n/2
                    effective_limit = min(needed_per_inst, max_reasonable)
                    
                    # Only use this if it's better than what we have
                    if effective_limit > max_per_institution:
                        selected = []
                        institution_count = {}
                        for profile in ranked:
                            if len(selected) >= n:
                                break
                            institution = profile.institution.lower().strip() if profile.institution else ""
                            current_count = institution_count.get(institution, 0)
                            if current_count < effective_limit:
                                selected.append(profile)
                                institution_count[institution] = current_count + 1
            
            return selected
        else:
            return ranked[:n]
    
    # Apply final strict limit check if strict_limit is True
    if strict_limit:
        # First apply strict limit
        final_selected = []
        institution_count = {}
        for profile in best_result:
            institution = profile.institution.lower().strip() if profile.institution else ""
            current_count = institution_count.get(institution, 0)
            if current_count < max_per_institution:
                final_selected.append(profile)
                institution_count[institution] = current_count + 1
        
        # If filtering reduced us below target and we have enough candidates, relax limit
        if len(final_selected) < n and len(best_result) >= n:
            # Calculate needed per-institution limit
            unique_institutions = set()
            for profile in best_result:
                inst = profile.institution.lower().strip() if profile.institution else ""
                if inst:
                    unique_institutions.add(inst)
            num_institutions = len(unique_institutions)
            if num_institutions > 0:
                needed_per_inst = (n + num_institutions - 1) // num_institutions
                # Cap at reasonable maximum
                max_reasonable = max(n // 2, max_per_institution * 2)
                effective_limit = min(needed_per_inst, max_reasonable)
                
                if effective_limit > max_per_institution:
                    final_selected = []
                    institution_count = {}
                    for profile in best_result:
                        if len(final_selected) >= n:
                            break
                        institution = profile.institution.lower().strip() if profile.institution else ""
                        current_count = institution_count.get(institution, 0)
                        if current_count < effective_limit:
                            final_selected.append(profile)
                            institution_count[institution] = current_count + 1
        
        return final_selected
    
    # Return best result found
    return best_result


def _detect_arts_keywords(keywords: List[str]) -> Tuple[List[str], List[str]]:
    """
    Detect if keywords contain arts-related terms and extract them.
    
    Returns:
        Tuple of (arts_keywords, non_arts_keywords)
        - arts_keywords: List of arts-related keywords (music, art, dance, theater, etc.)
        - non_arts_keywords: List of other keywords (education, psychology, therapy, etc.)
    """
    arts_terms = [
        "music", "musical", "musician", "musicality",
        "art", "arts", "artistic", "artist",
        "dance", "dancing", "choreography", "choreographer",
        "theater", "theatre", "drama", "dramatic", "theatrical",
        "performance", "performing", "performer",
        "visual arts", "fine arts", "creative arts",
        "composition", "composer", "composing"
    ]
    
    arts_keywords = []
    non_arts_keywords = []
    
    for kw in keywords:
        kw_lower = kw.lower().strip()
        is_arts = False
        
        # Check if keyword contains arts terms
        for arts_term in arts_terms:
            if arts_term in kw_lower:
                arts_keywords.append(kw)
                is_arts = True
                break
        
        if not is_arts:
            non_arts_keywords.append(kw)
    
    return arts_keywords, non_arts_keywords


def _requires_arts_context(keywords: List[str]) -> bool:
    """Check if keywords require arts context (e.g., music education, art therapy)."""
    arts_keywords, non_arts_keywords = _detect_arts_keywords(keywords)
    
    # If we have both arts keywords and domain keywords (education, therapy, psychology),
    # then we require arts context
    domain_terms = ["education", "therapy", "psychology", "counseling", "counselling", 
                    "pedagogy", "teaching", "learning", "development"]
    
    has_domain = any(domain_term in kw.lower() for kw in non_arts_keywords for domain_term in domain_terms)
    
    return len(arts_keywords) > 0 and has_domain


def score_supervisor(
    research_profile: ResearchProfile,
    supervisor: SupervisorProfile
) -> Tuple[float, str, List[str]]:
    """
    Compute fit score for a supervisor based on research profile.
    
    This is a rule-based scoring function that ensures consistency.
    LLM scores can be used as reference but final sorting uses this.
    
    Special handling for arts-related keywords (music, art, etc.):
    - If research includes arts + domain (e.g., "music education", "art therapy"),
      require supervisor to have BOTH arts and domain keywords
    - This prevents matching "music education" to general "education" or "psychology"
    
    Args:
        research_profile: ResearchProfile with core_keywords and adjacent_keywords
        supervisor: SupervisorProfile to score
    
    Returns:
        Tuple of (fit_score, tier, matched_terms)
        - fit_score: float between 0.0 and 1.0
        - tier: "Core" or "Adjacent"
        - matched_terms: list of keywords that matched
    """
    # Normalize keywords for matching
    def normalize_keyword(kw: str) -> str:
        return kw.lower().strip()
    
    supervisor_keywords = [normalize_keyword(k) for k in supervisor.keywords]
    supervisor_text = " ".join([supervisor.name, supervisor.title or "", supervisor.institution] + supervisor_keywords).lower()
    
    core_keywords = [normalize_keyword(k) for k in research_profile.core_keywords]
    adjacent_keywords = [normalize_keyword(k) for k in research_profile.adjacent_keywords]
    negative_keywords = [normalize_keyword(k) for k in research_profile.negative_keywords]
    
    # Check for negative keywords (penalty)
    negative_matches = sum(1 for nk in negative_keywords if nk in supervisor_text)
    if negative_matches > 0:
        return (0.0, "Adjacent", [])
    
    # Check if research requires arts context (e.g., "music education", "art therapy")
    all_research_keywords = core_keywords + adjacent_keywords
    requires_arts_context = _requires_arts_context([k for k in research_profile.core_keywords + research_profile.adjacent_keywords])
    
    if requires_arts_context:
        # Extract arts and domain keywords from research profile
        research_arts_keywords, research_domain_keywords = _detect_arts_keywords(
            research_profile.core_keywords + research_profile.adjacent_keywords
        )
        
        # Check if supervisor has arts keywords
        supervisor_has_arts = any(
            arts_kw.lower() in supervisor_text 
            for arts_kw in research_arts_keywords
        )
        
        # Check if supervisor has domain keywords
        domain_terms = ["education", "therapy", "psychology", "counseling", "counselling", 
                       "pedagogy", "teaching", "learning", "development"]
        supervisor_has_domain = any(
            domain_term in supervisor_text 
            for domain_term in domain_terms
        )
        
        # If research requires arts context, supervisor MUST have arts keywords
        # This ensures "music education" doesn't match general "education" or "psychology"
        if not supervisor_has_arts:
            # No arts keywords in supervisor profile - reject
            # Example: "music education" should not match supervisor with only "education" or "psychology"
            return (0.0, "Adjacent", [])
        
        # If research has domain keywords (e.g., "music education", "art therapy"), 
        # supervisor should also have domain keywords (not just arts alone)
        # This ensures "music education" matches "music education" or "musical psychology",
        # but not just "music" without any educational/psychological context
        if len(research_domain_keywords) > 0 and not supervisor_has_domain:
            # Research has domain keywords but supervisor doesn't - likely not a match
            # Example: "music education" research should not match supervisor with only "music" (no education/psychology)
            # But "music" alone (without education/therapy) can still match "music" supervisors
            # So we only reject if research explicitly has domain terms
            return (0.0, "Adjacent", [])
    
    # Score based on keyword matches
    core_matches = []
    adjacent_matches = []
    
    # Check core keywords
    for ck in core_keywords:
        if ck in supervisor_text:
            core_matches.append(ck)
    
    # Check adjacent keywords
    for ak in adjacent_keywords:
        if ak in supervisor_text:
            adjacent_matches.append(ak)
    
    
    # Calculate score
    # Core keywords are worth more (0.1 each, max 1.0)
    # Adjacent keywords are worth less (0.05 each, max 0.5)
    core_score = min(len(core_matches) * 0.1, 1.0)
    adjacent_score = min(len(adjacent_matches) * 0.05, 0.5)
    
    # Base score
    fit_score = core_score + adjacent_score
    
    # Bonus for having email (0.1)
    if supervisor.email:
        fit_score += 0.1
    
    # Bonus for high email confidence (0.05)
    if supervisor.email_confidence == "high":
        fit_score += 0.05
    
    # Normalize to [0, 1]
    fit_score = min(fit_score, 1.0)
    
    # Determine tier
    if fit_score >= CORE_THRESHOLD:
        tier = "Core"
    elif fit_score >= ADJACENT_THRESHOLD:
        tier = "Adjacent"
    else:
        tier = "Adjacent"  # Keep as Adjacent even for low scores
    
    # Collect matched terms
    matched_terms = list(set(core_matches + adjacent_matches))
    
    return (fit_score, tier, matched_terms)

