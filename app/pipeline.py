"""Pipeline orchestrator for PhD Supervisor Finder."""

from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable
import pandas as pd
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from app.config import TARGET_SUPERVISORS, MAX_PAGES_PER_SCHOOL, MIN_TEXT_LENGTH_FOR_EXTRACTION, MIN_TEXT_LENGTH_FOR_PROFILE_URL
from app.schemas import University, ResearchProfile, SupervisorProfile
from app.modules.llm_deepseek import llm_client
from app.modules.search import search_client
from app.modules.crawl import crawler
from app.modules.directory import directory_parser
from app.modules.profile import profile_extractor
from app.modules.scoring import select_top_n, select_with_diversity, score_supervisor
from app.modules.validators import validate_profile, deduplicate_profiles
from app.modules.export_excel import export_to_excel
from app.modules.cv_extractor import cv_extractor
from app.modules.local_repo import query_candidates, upsert_many
from app.db_cloud import init_db
from app.modules.subscription import can_perform_search, consume_search

console = Console()


def _infer_domain_from_institution(institution: str, country: str) -> str:
    """Infer domain from institution name when domain is missing."""
    institution_lower = institution.lower()
    country_lower = country.lower() if country else ""
    
    # Known mappings for top universities
    domain_mappings = {
        "imperial college london": "imperial.ac.uk",
        "university of oxford": "ox.ac.uk",
        "oxford": "ox.ac.uk",
        "university of cambridge": "cam.ac.uk",
        "cambridge": "cam.ac.uk",
        "eth zurich": "ethz.ch",
        "eth": "ethz.ch",
        "ucl": "ucl.ac.uk",
        "university college london": "ucl.ac.uk",
        "king's college london": "kcl.ac.uk",
        "kings college london": "kcl.ac.uk",
        "lse": "lse.ac.uk",
        "london school of economics": "lse.ac.uk",
        "edinburgh": "ed.ac.uk",
        "university of edinburgh": "ed.ac.uk",
        "manchester": "manchester.ac.uk",
        "university of manchester": "manchester.ac.uk",
    }
    
    # Try exact match first
    for key, domain in domain_mappings.items():
        if key in institution_lower:
            return domain
    
    # Try to infer from institution name patterns
    # UK universities often end with .ac.uk
    if "united kingdom" in country_lower or "uk" in country_lower:
        # Extract key words from institution name
        words = institution_lower.split()
        # Remove common words
        key_words = [w for w in words if w not in ["university", "of", "the", "college", "london", "school"]]
        if key_words:
            # Use first significant word
            first_word = key_words[0]
            # Common UK patterns
            if first_word in ["imperial", "oxford", "cambridge", "ucl", "kcl", "lse", "edinburgh", "manchester"]:
                return domain_mappings.get(first_word, "")
            # Generic pattern: firstword.ac.uk
            if len(first_word) > 2:
                return f"{first_word}.ac.uk"
    
    return ""


def load_universities(path: Path) -> list[University]:
    """Load universities from Excel file."""
    df = pd.read_excel(path)
    universities = []
    
    for _, row in df.iterrows():
        # Check include flag (if column exists and is 0, skip this university)
        if "include" in row and pd.notna(row.get("include")) and row.get("include") == 0:
            continue
        
        # Support both qs_rank and qs_rank_2026 field names
        qs_rank = None
        if "qs_rank_2026" in row and pd.notna(row.get("qs_rank_2026")):
            qs_rank = int(row.get("qs_rank_2026"))
        elif "qs_rank" in row and pd.notna(row.get("qs_rank")):
            qs_rank = int(row.get("qs_rank"))
        
        institution = row["institution"]
        country = row["country"] if pd.notna(row.get("country")) else ""
        
        # Get domain, infer if missing (but don't print here - will print after filtering)
        domain = row["domain"] if pd.notna(row.get("domain")) else ""
        if not domain or domain.strip() == "":
            domain = _infer_domain_from_institution(institution, country)
        
        universities.append(University(
            institution=institution,
            domain=domain,
            country=country,
            region=row.get("region", "") if pd.notna(row.get("region", "")) else "",
            qs_rank=qs_rank,
            notes=row.get("notes") if pd.notna(row.get("notes")) else None
        ))
    
    return universities


def parse_cv(cv_path: Path) -> str:
    """Extract text from CV (PDF or text)."""
    if cv_path.suffix.lower() == ".pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(cv_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    else:
        return cv_path.read_text()


def retrieve_local_candidates(
    research_profile: ResearchProfile,
    constraints: Optional[dict] = None,
    limit: int = 800,
    universities: Optional[List[University]] = None
) -> List[SupervisorProfile]:
    """
    Retrieve candidates from local database and score them.
    
    Args:
        research_profile: ResearchProfile with keywords
        constraints: Dict with optional keys: regions (list), countries (list), qs_min (int), qs_max (int)
        limit: Maximum candidates to retrieve
        universities: Optional list of universities for QS rank filtering
    
    Returns:
        List of SupervisorProfile objects with fit_score and tier set
    """
    # Query from local DB (without QS rank filter in SQL, since table doesn't have qs_rank column)
    from app.modules.local_repo import query_candidates
    local_profiles = query_candidates(research_profile, constraints, limit, debug=False)
    
    # Apply QS rank and institution filtering if universities list is provided
    # This ensures we only return results from universities that match the region/country/QS filters
    if universities:
        constraints_dict = constraints or {}
        qs_min = constraints_dict.get("qs_min")
        qs_max = constraints_dict.get("qs_max")
        
        # Create mapping from institution name to qs_rank
        # Also create a set of allowed institution names (already filtered by region/country)
        inst_to_qs = {u.institution: u.qs_rank for u in universities if u.qs_rank is not None}
        allowed_institutions = set(u.institution for u in universities)
        
        filtered_profiles = []
        for profile in local_profiles:
            # First check if institution is in the allowed list
            # This respects region/country filtering already applied to universities list
            if profile.institution not in allowed_institutions:
                # Institution not in filtered universities list, skip it
                continue
            
            # Try to match institution to get qs_rank
            qs_rank = inst_to_qs.get(profile.institution)
            
            # If QS rank filtering is specified, apply it strictly
            if qs_min is not None or qs_max is not None:
                if qs_rank is not None:
                    # Apply QS rank filter
                    if qs_min is not None and qs_max is not None:
                        if qs_min <= qs_rank <= qs_max:
                            profile.qs_rank = qs_rank
                            filtered_profiles.append(profile)
                    elif qs_min is not None:
                        if qs_rank >= qs_min:
                            profile.qs_rank = qs_rank
                            filtered_profiles.append(profile)
                    elif qs_max is not None:
                        if qs_rank <= qs_max:
                            profile.qs_rank = qs_rank
                            filtered_profiles.append(profile)
                # If QS rank filtering is specified but institution has no QS rank, exclude it
                # This ensures we only return results from universities with known QS ranks
                else:
                    # Institution is in allowed list but has no QS rank
                    # Since QS filtering is specified, exclude records without QS rank
                    pass
            else:
                # No QS rank filtering, but still respect institution filtering
                # Include all profiles from allowed institutions
                if qs_rank is not None:
                    profile.qs_rank = qs_rank
                filtered_profiles.append(profile)
        
        local_profiles = filtered_profiles
    
    # Score each candidate
    scored_profiles = []
    for profile in local_profiles:
        fit_score, tier, matched_terms = score_supervisor(research_profile, profile)
        profile.fit_score = fit_score
        profile.tier = tier
        profile.matched_terms = matched_terms
        scored_profiles.append(profile)
    
    return scored_profiles


def save_to_local_db(profiles: List[SupervisorProfile], domain: Optional[str] = None) -> None:
    """Save supervisor profiles to local database."""
    upsert_many(profiles, domain)


def run_pipeline(
    cv_path: Optional[Path],
    keywords: Optional[str],
    universities_path: Path,
    output_path: Path,
    regions: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
    qs_min: Optional[int] = None,
    qs_max: Optional[int] = None,
    target: int = TARGET_SUPERVISORS,
    local_first: bool = True,
    user_id: Optional[int] = None,
    progress_callback: Optional[Any] = None  # Callable[[str, float, str], None] - simplified for compatibility
) -> None:
    """Run the full supervisor discovery pipeline.
    
    Args:
        user_id: Optional user ID for subscription tracking. If None, subscription checks are skipped (CLI mode).
        progress_callback: Optional callback function for progress updates. 
                          Should accept (step: str, progress: float, message: str, **kwargs)
    """
    
    # Initialize database tables if they don't exist
    init_db()
    
    # Check subscription if user_id is provided
    subscription_info = None
    is_free_user = False
    if user_id is not None:
        can_search, error_msg, subscription_info = can_perform_search(user_id)
        if not can_search:
            raise ValueError(error_msg or "Cannot perform search. Please check your subscription.")
        if subscription_info and subscription_info['type'] == 'developer':
            console.print(f"[bold green]Developer Mode: Unlimited access[/bold green]")
        elif subscription_info and subscription_info['type'] == 'beta':
            console.print(f"[cyan]Beta User: {subscription_info['remaining_searches']} free searches remaining[/cyan]")
            subscription_type = 'beta'
            is_free_user = False  # Beta users can still subscribe
        else:
            subscription_type = subscription_info['type'] if subscription_info else 'unknown'
            is_free_user = (subscription_type == 'free')
            console.print(f"[green]Subscription: {subscription_type} plan - {subscription_info['remaining_searches']} searches remaining[/green]")
            # Free users get 10 supervisors; paid users get target (default 100)
            if is_free_user:
                target = 10
                console.print(f"[yellow]Free trial: Limited to 10 supervisors from different institutions[/yellow]")
    
    console.print("[bold blue]PhD Supervisor Finder[/bold blue]")
    console.print()
    
    # Step 1: Load inputs
    console.print("[yellow]Loading inputs...[/yellow]")
    if progress_callback:
        progress_callback("loading", 0.05, "Loading universities...")
    universities = load_universities(universities_path)
    initial_count = len(universities)
    if progress_callback:
        progress_callback("loading", 0.10, f"Loaded {initial_count} universities")
    
    # Filter by region
    if regions:
        regions_normalized = [r.strip().lower() for r in regions]
        universities_before_region = len(universities)
        universities = [u for u in universities if u.region.lower() in regions_normalized]
        console.print(f"  Filtered by region {regions}: {universities_before_region} -> {len(universities)} universities")
    
    # Filter by country
    if countries:
        countries_normalized = [c.strip().lower() for c in countries]
        universities_before_country = len(universities)
        universities = [u for u in universities if u.country.lower() in countries_normalized]
        console.print(f"  Filtered by country {countries}: {universities_before_country} -> {len(universities)} universities")
    
    # Filter by QS rank range
    if qs_min is not None or qs_max is not None:
        universities_before_qs = len(universities)
        
        if qs_min is not None and qs_max is not None:
            universities = [u for u in universities 
                          if u.qs_rank is not None and qs_min <= u.qs_rank <= qs_max]
            console.print(f"  Filtered by QS rank [{qs_min}, {qs_max}]: {universities_before_qs} -> {len(universities)} universities")
        elif qs_min is not None:
            universities = [u for u in universities 
                          if u.qs_rank is not None and u.qs_rank >= qs_min]
            console.print(f"  Filtered by QS rank >= {qs_min}: {universities_before_qs} -> {len(universities)} universities")
        elif qs_max is not None:
            universities = [u for u in universities 
                          if u.qs_rank is None or u.qs_rank <= qs_max]
            console.print(f"  Filtered by QS rank <= {qs_max}: {universities_before_qs} -> {len(universities)} universities")
    
    # After filtering, infer domains for remaining universities and print only those
    inferred_count = 0
    for university in universities:
        if not university.domain or university.domain.strip() == "":
            inferred_domain = _infer_domain_from_institution(university.institution, university.country)
            if inferred_domain:
                university.domain = inferred_domain
                inferred_count += 1
                console.print(f"  [yellow]Inferred domain for {university.institution}: {inferred_domain}[/yellow]")
    
    console.print(f"  Final: {len(universities)} universities (from {initial_count} total)")
    if inferred_count > 0:
        console.print(f"  [yellow]Inferred {inferred_count} missing domains[/yellow]")
    
    # Step 2: Parse CV and build research profile
    # At least one of CV or keywords must be provided
    if not cv_path and not keywords:
        raise ValueError("At least one of CV or keywords must be provided")
    
    cv_key_sections = ""
    if cv_path:
        console.print("[yellow]Analyzing CV...[/yellow]")
        if progress_callback:
            progress_callback("cv_analysis", 0.15, "Analyzing CV...")
        cv_full_text = parse_cv(cv_path)
        # Extract only key sections to reduce token usage
        cv_key_sections = cv_extractor.extract_key_sections(cv_full_text, max_length=3000)
        console.print(f"  Extracted key sections ({len(cv_key_sections)} chars)")
    else:
        console.print("[yellow]No CV provided, using keywords only...[/yellow]")
        if progress_callback:
            progress_callback("cv_analysis", 0.15, "Using keywords only...")
    
    # Normalize keywords to empty string if None
    keywords_text = keywords.strip() if keywords else ""
    
    if progress_callback:
        progress_callback("keywords", 0.20, "Extracting research profile from CV/keywords...")
    research_profile = llm_client.cv_to_research_profile(cv_key_sections, keywords_text)
    if progress_callback:
        progress_callback("keywords", 0.25, f"Extracted {len(research_profile.core_keywords)} core keywords")
    
    # Print extracted keywords for search
    console.print(f"\n[yellow]Extracted keywords for search:[/yellow]")
    console.print(f"  [cyan]Core keywords ({len(research_profile.core_keywords)}):[/cyan] {', '.join(research_profile.core_keywords)}")
    console.print(f"  [cyan]Adjacent keywords ({len(research_profile.adjacent_keywords)}):[/cyan] {', '.join(research_profile.adjacent_keywords)}")
    if research_profile.negative_keywords:
        console.print(f"  [red]Negative keywords ({len(research_profile.negative_keywords)}):[/red] {', '.join(research_profile.negative_keywords)}")
    console.print("")  # Empty line for readability
    
    # Step 3: Local-first retrieval (if enabled)
    all_profiles: List[SupervisorProfile] = []
    local_hit_count = 0
    online_fetched_count = 0
    
    if local_first:
        console.print("[yellow]Retrieving from local database...[/yellow]")
        if progress_callback:
            progress_callback("local_db", 0.30, "Searching local database...")
        constraints = {}
        if regions:
            constraints["regions"] = regions
        if qs_min is not None:
            constraints["qs_min"] = qs_min
        if qs_max is not None:
            constraints["qs_max"] = qs_max
        
        # Add countries to constraints if specified
        if countries:
            constraints["countries"] = countries
        
        local_candidates = retrieve_local_candidates(research_profile, constraints, limit=800, universities=universities)
        console.print(f"  Found {len(local_candidates)} candidates in local database")
        if progress_callback:
            progress_callback("local_db", 0.40, f"Found {len(local_candidates)} candidates in local database")
        
        # If no candidates found, provide diagnostic information
        if len(local_candidates) == 0:
            console.print(f"  [yellow]Warning: No candidates found. This might be due to:[/yellow]")
            console.print(f"    - Keyword matching too strict (trying to match: {len(research_profile.core_keywords + research_profile.adjacent_keywords)} keywords)")
            if constraints:
                console.print(f"    - Constraints: {constraints}")
            
            # Try query without keyword matching to see if constraints are too strict
            from app.modules.local_repo import query_candidates
            test_profile = ResearchProfile(core_keywords=[], adjacent_keywords=[])
            test_candidates = query_candidates(test_profile, constraints, limit=10, debug=False)
            if len(test_candidates) > 0:
                console.print(f"    [dim]Without keyword filter: {len(test_candidates)} candidates match constraints (keywords might be too strict)[/dim]")
            else:
                console.print(f"    [dim]Without keyword filter: 0 candidates (constraints might be too strict)[/dim]")
        
        # Select top candidates from local
        selected_local = select_top_n(local_candidates, n=target)
        local_hit_count = len(selected_local)
        all_profiles.extend(selected_local)
        console.print(f"  Selected {local_hit_count} from local database")
        if progress_callback:
            progress_callback("local_db", 0.45, f"Selected {local_hit_count} supervisors from local database")
    
    # Step 4: Online search if needed
    need_count = target - len(all_profiles)
    
    # Initialize statistics variables (needed for final summary even if no online search)
    total_profile_pages = 0
    total_crawled_ok = 0
    total_reclassified_as_profile = 0
    total_extracted_ok = 0
    total_dropped_reasons = {
        "domain_mismatch": 0,
        "validate_failed": 0,
        "text_too_short": 0,
        "not_a_person": 0,
        "fetch_failed": 0,
        "extraction_failed": 0,
        "extraction_failed: no_name": 0,
        "extraction_failed: invalid_name": 0,
        "extraction_failed: student_postdoc": 0,
        "extraction_failed: negative_keyword": 0,
        "extraction_failed: very_low_fit_score": 0,
        "other": 0
    }
    
    if need_count > 0:
        console.print(f"[yellow]Need {need_count} more supervisors, searching online...[/yellow]")
        if progress_callback:
            progress_callback("online_search", 0.50, f"Need {need_count} more supervisors, searching online...")
        
        online_profiles: List[SupervisorProfile] = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing universities...", total=len(universities))
            
            for idx, university in enumerate(universities):
                progress.update(task, description=f"Processing {university.institution}...")
                
                # Update progress callback
                if progress_callback:
                    uni_progress = 0.50 + (idx / len(universities)) * 0.35
                    progress_callback(
                        "online_search", 
                        uni_progress, 
                        f"Processing {university.institution}... ({idx+1}/{len(universities)})",
                        found_count=len(online_profiles)
                    )
                
                try:
                    profiles, stats = process_university(university, research_profile)
                    online_profiles.extend(profiles)
                    
                    # Accumulate statistics
                    total_profile_pages += stats.get("profile_pages_total", 0)
                    total_crawled_ok += stats.get("crawled_ok", 0)
                    total_extracted_ok += stats["extracted"]
                    total_reclassified_as_profile += stats["reclassified_as_profile"]
                    for reason, count in stats["dropped_reasons"].items():
                        total_dropped_reasons[reason] += count
                    
                    # Update progress with found count
                    if progress_callback:
                        progress_callback(
                            "online_search",
                            uni_progress,
                            f"Found {len(online_profiles)} supervisors so far...",
                            found_count=len(online_profiles)
                        )
                    
                    # Early exit if we have enough
                    if len(online_profiles) >= need_count * 2:
                        console.print(f"  [green]Collected enough candidates ({len(online_profiles)})[/green]")
                        if progress_callback:
                            progress_callback(
                                "online_search",
                                0.85,
                                f"Collected enough candidates ({len(online_profiles)})",
                                found_count=len(online_profiles)
                            )
                        break
                except Exception as e:
                    console.print(f"  [red]Error processing {university.institution}: {e}[/red]")
                
                progress.advance(task)
        
        # Validate and deduplicate online profiles
        console.print("[yellow]Validating and deduplicating online profiles...[/yellow]")
        if progress_callback:
            progress_callback("validation", 0.86, f"Validating {len(online_profiles)} profiles...")
        valid_online = []
        validation_dropped = 0
        for p in online_profiles:
            is_valid, reason = validate_profile(p)
            if is_valid:
                valid_online.append(p)
            else:
                validation_dropped += 1
                total_dropped_reasons[reason or "validate_failed"] += 1
        
        unique_online = deduplicate_profiles(valid_online)
        console.print(f"  {len(unique_online)} unique valid online profiles (dropped {validation_dropped} during validation)")
        if progress_callback:
            progress_callback("validation", 0.90, f"Validated: {len(unique_online)} unique profiles")
        
        # Score online profiles and filter out irrelevant ones
        scored_online = []
        for profile in unique_online:
            fit_score, tier, matched_terms = score_supervisor(research_profile, profile)
            profile.fit_score = fit_score
            profile.tier = tier
            profile.matched_terms = matched_terms
            
            # Check if this is a PI (Principal Investigator)
            # PI should be saved even with low fit_score if they are valid supervisors
            is_pi = False
            if profile.notes:
                notes_lower = profile.notes.lower()
                pi_indicators = ["principal investigator", "pi", "group leader", "lab head", "lab director"]
                is_pi = any(indicator in notes_lower for indicator in pi_indicators)
            
            if not is_pi and profile.keywords:
                keywords_text = " ".join(profile.keywords).lower()
                pi_indicators = ["principal investigator", "pi", "group leader", "lab head"]
                is_pi = any(indicator in keywords_text for indicator in pi_indicators)
            
            # Filter out profiles with very low relevance or no matched terms
            # BUT: Allow PI even with low fit_score (they might be valid supervisors)
            # This prevents profiles from completely different fields (e.g., political science)
            if (fit_score >= 0.15 and len(matched_terms) > 0) or (is_pi and fit_score >= 0.05):
                scored_online.append(profile)
                if is_pi and fit_score < 0.15:
                    console.print(f"    [dim]Including PI {profile.name} ({profile.institution}) despite low score (score={fit_score:.2f})[/dim]")
            else:
                console.print(f"    [dim]Filtered out {profile.name} ({profile.institution}): low relevance (score={fit_score:.2f}, matched={len(matched_terms)})[/dim]")
        
        unique_online = scored_online
        console.print(f"  After relevance filtering: {len(unique_online)} profiles")
        
        # Save online profiles to local DB
        console.print("[yellow]Saving online profiles to local database...[/yellow]")
        # Create mappings for domain matching
        inst_to_domain = {uni.institution: uni.domain for uni in universities}
        domain_to_university = {uni.domain: uni for uni in universities}
        
        for profile in unique_online:
            # Try to match university by profile URL domain (more reliable than institution name)
            matched_domain = None
            if profile.profile_url:
                from urllib.parse import urlparse
                parsed_url = urlparse(profile.profile_url)
                url_domain = parsed_url.netloc.lower()
                
                # Try to match URL domain to university domain
                for uni_domain, uni in domain_to_university.items():
                    if not uni_domain:
                        continue
                    uni_domain_lower = uni_domain.lower()
                    
                    # Direct match
                    if url_domain == uni_domain_lower:
                        matched_domain = uni_domain
                        # Update profile with correct institution info
                        profile.institution = uni.institution
                        profile.country = uni.country
                        profile.region = uni.region
                        profile.qs_rank = uni.qs_rank
                        break
                    
                    # Check for profiles subdomain
                    if url_domain.startswith("profiles."):
                        base_domain = url_domain.replace("profiles.", "", 1)
                        if base_domain == uni_domain_lower or base_domain.endswith("." + uni_domain_lower):
                            matched_domain = uni_domain
                            profile.institution = uni.institution
                            profile.country = uni.country
                            profile.region = uni.region
                            profile.qs_rank = uni.qs_rank
                            break
                    
                    # Check if URL domain is a suffix of university domain
                    if url_domain.endswith("." + uni_domain_lower):
                        matched_domain = uni_domain
                        profile.institution = uni.institution
                        profile.country = uni.country
                        profile.region = uni.region
                        profile.qs_rank = uni.qs_rank
                        break
            
            # Fallback to institution name mapping if domain matching failed
            if not matched_domain:
                matched_domain = inst_to_domain.get(profile.institution)
            
            save_to_local_db([profile], matched_domain)
        
        online_fetched_count = len(unique_online)
        all_profiles.extend(unique_online)
        
        # Re-retrieve from local to merge and deduplicate
        if local_first:
            console.print("[yellow]Re-retrieving from local database to merge...[/yellow]")
            merged_local = retrieve_local_candidates(research_profile, constraints, limit=800, universities=universities)
            # Deduplicate by canonical_id
            seen_ids = {p.canonical_id for p in all_profiles if p.canonical_id}
            for profile in merged_local:
                if profile.canonical_id and profile.canonical_id not in seen_ids:
                    all_profiles.append(profile)
                    seen_ids.add(profile.canonical_id)
    else:
        console.print("[green]Sufficient candidates from local database, skipping online search[/green]")
    
    # Step 5: Final deduplication and selection with diversity
    console.print("[yellow]Final deduplication and ranking...[/yellow]")
    if progress_callback:
        progress_callback("final_selection", 0.92, f"Final selection from {len(all_profiles)} candidates...")
    unique_profiles = deduplicate_profiles(all_profiles)
    
    # Apply diversity constraints based on subscription type
    if is_free_user:
        # Free users: 10 supervisors, max 1 per institution, minimum 3 institutions
        final_profiles = select_with_diversity(unique_profiles, n=10, max_per_institution=1, min_institutions=3)
        console.print(f"[yellow]Free trial: Selected 10 supervisors from different institutions (minimum 3 schools)[/yellow]")
    else:
        # Paid users: target supervisors (default 100), max 10 per institution
        final_profiles = select_with_diversity(unique_profiles, n=target, max_per_institution=10)
    
    core_count = sum(1 for p in final_profiles if p.tier == "Core")
    # Show diversity statistics
    institutions_in_results = len(set(p.institution.lower().strip() if p.institution else "" for p in final_profiles))
    console.print(f"  Selected {len(final_profiles)} supervisors ({core_count} Core, {len(final_profiles) - core_count} Adjacent)")
    console.print(f"  From {institutions_in_results} different institutions")
    if progress_callback:
        progress_callback("final_selection", 0.96, f"Selected {len(final_profiles)} final supervisors")
    
    # Step 6: Export
    console.print("[yellow]Exporting to Excel...[/yellow]")
    if progress_callback:
        progress_callback("export", 0.98, "Exporting to Excel...")
    export_to_excel(final_profiles, output_path)
    if progress_callback:
        progress_callback("export", 1.0, f"Done! {len(final_profiles)} supervisors exported")
    
    # Print final statistics summary
    console.print()
    console.print("[bold yellow]Pipeline Statistics Summary:[/bold yellow]")
    console.print(f"  Profile pages total: {total_profile_pages}")
    console.print(f"  Crawled OK: {total_crawled_ok}")
    console.print(f"  Reclassified as profile: {total_reclassified_as_profile}")
    console.print(f"  Extracted OK: {total_extracted_ok}")
    console.print(f"  Saved to DB: {online_fetched_count}")
    console.print(f"  Dropped reasons:")
    for reason, count in total_dropped_reasons.items():
        if count > 0:
            console.print(f"    - {reason}: {count}")
    
    console.print()
    console.print(f"[bold green]Done! Output saved to {output_path}[/bold green]")
    console.print(f"  Local hits: {local_hit_count}, Online fetched: {online_fetched_count}, Final selected: {len(final_profiles)}")
    
    # Record search in subscription system if user_id is provided
    if user_id is not None and subscription_info is not None:
        subscription_id = subscription_info.get("id")  # None for developers
        consume_search(
            user_id=user_id,
            subscription_id=subscription_id,
            search_info={
                "keywords": keywords,
                "universities_count": len(universities),
                "regions": ", ".join(regions) if regions else None,
                "countries": ", ".join(countries) if countries else None,
                "result_count": len(final_profiles)
            }
        )
        # Get updated subscription info (skip for developers and beta users using free searches)
        if subscription_info['type'] not in ['developer', 'beta']:
            from app.modules.subscription import get_user_subscription
            updated_sub = get_user_subscription(user_id)
            if updated_sub:
                console.print(f"[green]Subscription: {updated_sub['remaining_searches']} searches remaining[/green]")


def process_university(university: University, research_profile: ResearchProfile) -> Tuple[List[SupervisorProfile], Dict]:
    """Process a single university to find supervisors.
    
    Returns:
        Tuple of (profiles_list, statistics_dict)
    """
    profiles = []
    
    # Skip if domain is missing (can't search without domain)
    if not university.domain or university.domain.strip() == "":
        console.print(f"    [red]Skipping {university.institution}: domain is missing[/red]")
        return profiles, {
            "profile_pages_total": 0,
            "crawled_ok": 0,
            "extracted": 0,
            "dropped": 0,
            "dropped_reasons": {},
            "reclassified_as_profile": 0
        }
    
    # Search for directory pages
    directory_results = search_client.find_directory_pages(university.domain)
    console.print(f"    Found {len(directory_results)} directory pages")
    
    # Also search for researcher profiles directly - use both core and adjacent keywords
    all_keywords = research_profile.core_keywords + research_profile.adjacent_keywords[:5]
    researcher_results = search_client.find_researcher_profiles(
        university.domain,
        all_keywords
    )
    console.print(f"    Found {len(researcher_results)} researcher profile pages")
    
    # Combine and deduplicate URLs
    all_urls = set()
    for r in directory_results + researcher_results:
        all_urls.add(r["link"])
    
    # Fetch and parse directory pages to get profile URLs
    profile_urls = set()
    reclassified_as_profile = []  # URLs that were directory candidates but are actually profile pages
    
    # Process more directory pages (increased from 15 to 30)
    for url in list(all_urls)[:30]:
        page = crawler.fetch(url)
        if page["status_code"] == 200:
            # Check if this URL is actually a profile page, not a directory
            is_directory = directory_parser.is_directory_like_page(
                page["text_content"] or "",
                page["html"],
                url
            )
            
            if not is_directory:
                # This is actually a profile page, not a directory
                profile_urls.add(url)
                reclassified_as_profile.append(url)
                console.print(f"    [dim]Reclassified as profile: {url[:60]}...[/dim]")
            else:
                # It's a directory page, extract profile URLs from it
                found_urls = directory_parser.extract_profile_urls(page["html"], url)
                profile_urls.update(found_urls)
                if found_urls:
                    console.print(f"    Extracted {len(found_urls)} profile URLs from {url[:60]}...")
    
    # Add direct researcher URLs
    for r in researcher_results:
        profile_urls.add(r["link"])
    
    console.print(f"    Total profile URLs found: {len(profile_urls)}")
    
    # Store total for statistics
    total_profile_pages_for_uni = len(profile_urls)
    
    # Increase limit significantly to get more profiles (was 60, now 200)
    # This allows processing more profiles per university
    profile_urls = list(profile_urls)[:200]
    
    # Extract profiles from each URL with detailed tracking
    extracted_count = 0
    dropped_urls = []  # List of (url, reason) tuples
    dropped_reasons_count = {
        "domain_mismatch": 0,
        "validate_failed": 0,
        "text_too_short": 0,
        "not_a_person": 0,
        "fetch_failed": 0,
        "extraction_failed": 0,
        "extraction_failed: no_name": 0,
        "extraction_failed: invalid_name": 0,
        "extraction_failed: student_postdoc": 0,
        "extraction_failed: negative_keyword": 0,
        "extraction_failed: very_low_fit_score": 0,
        "other": 0
    }
    
    for url in profile_urls:
        try:
            page = crawler.fetch(url)
            if page["status_code"] != 200:
                dropped_urls.append((url, "fetch_failed"))
                dropped_reasons_count["fetch_failed"] += 1
                continue
            
            # Check text length - be more lenient, especially for profile URLs
            # Profile URLs (like profiles.ucl.ac.uk) may have structured data in HTML
            # even if extracted text is short
            text_content = page.get("text_content", "") or ""
            url_lower = url.lower()
            is_profile_url = "profiles." in url_lower or "/people/" in url_lower or "/profile/" in url_lower
            
            # Set minimum text length based on URL type
            min_text_length = MIN_TEXT_LENGTH_FOR_PROFILE_URL if is_profile_url else MIN_TEXT_LENGTH_FOR_EXTRACTION
            
            if not text_content or len(text_content.strip()) < min_text_length:
                # Even if text is short, try extraction if HTML exists and it's a profile URL
                # Some pages have structured data in HTML even if text extraction is minimal
                if is_profile_url and page.get("html"):
                    # Try extraction anyway - HTML might have structured data
                    pass  # Continue to extraction
                else:
                    dropped_urls.append((url, f"text_too_short ({len(text_content)} chars)"))
                    dropped_reasons_count["text_too_short"] += 1
                    continue
            
            # Attempt extraction - even with short text, HTML might have useful data
            profile = None
            extraction_failure_reason = None
            extraction_error = None
            
            try:
                profile, extraction_failure_reason = profile_extractor.extract(
                    page["html"],
                    text_content,
                    url,
                    university,
                    research_profile,
                    debug=False  # Set to True for detailed debugging
                )
            except Exception as e:
                extraction_error = str(e)
                extraction_failure_reason = f"exception: {str(e)[:100]}"
                # Log but continue - will be marked as extraction_failed
            
            if profile:
                # Validate the profile
                is_valid, reason = validate_profile(profile)
                if is_valid:
                    profiles.append(profile)
                    extracted_count += 1
                else:
                    dropped_urls.append((url, reason or "validate_failed"))
                    dropped_reasons_count[reason or "validate_failed"] += 1
            else:
                # Use the detailed failure reason from extract method
                if extraction_failure_reason:
                    # Map detailed reasons to categories for statistics
                    if "no_name" in extraction_failure_reason:
                        reason_category = "extraction_failed: no_name"
                    elif "invalid_name" in extraction_failure_reason:
                        reason_category = "extraction_failed: invalid_name"
                    elif "domain_mismatch" in extraction_failure_reason:
                        reason_category = "domain_mismatch"
                    elif "student_postdoc" in extraction_failure_reason:
                        reason_category = "extraction_failed: student_postdoc"
                    elif "negative_keyword" in extraction_failure_reason:
                        reason_category = "extraction_failed: negative_keyword"
                    elif "very_low_fit_score" in extraction_failure_reason:
                        reason_category = "extraction_failed: very_low_fit_score"
                    else:
                        reason_category = "extraction_failed"
                    
                    dropped_urls.append((url, extraction_failure_reason))
                    dropped_reasons_count[reason_category] = dropped_reasons_count.get(reason_category, 0) + 1
                elif extraction_error:
                    dropped_urls.append((url, f"extraction_failed: exception - {extraction_error[:50]}"))
                    dropped_reasons_count["extraction_failed"] += 1
                else:
                    # Fallback - shouldn't happen but just in case
                    dropped_urls.append((url, "extraction_failed: unknown_reason"))
                    dropped_reasons_count["extraction_failed"] += 1
                
        except Exception as e:
            dropped_urls.append((url, f"other: {str(e)[:50]}"))
            dropped_reasons_count["other"] += 1
            continue
    
    # Print summary with dropped reasons (limit to first 30 for readability)
    console.print(f"    Extracted {extracted_count} profiles")
    if dropped_urls:
        console.print(f"    Dropped {len(dropped_urls)} URLs")
        # Show first 30 dropped URLs with reasons
        for url, reason in dropped_urls[:30]:
            console.print(f"      [dim]Dropped {url[:60]}...: {reason}[/dim]")
        if len(dropped_urls) > 30:
            console.print(f"      [dim]... and {len(dropped_urls) - 30} more[/dim]")
    
    # Store statistics for final summary
    return profiles, {
        "profile_pages_total": total_profile_pages_for_uni,
        "crawled_ok": len([u for u in profile_urls if True]),  # All URLs we attempted to crawl
        "extracted": extracted_count,
        "dropped": len(dropped_urls),
        "dropped_reasons": dropped_reasons_count,
        "reclassified_as_profile": len(reclassified_as_profile)
    }

