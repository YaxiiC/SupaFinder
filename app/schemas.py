"""Pydantic models for PhD Supervisor Finder."""

from typing import Optional
from pydantic import BaseModel, Field


class ResearchProfile(BaseModel):
    """Research profile extracted from CV."""
    core_keywords: list[str] = Field(default_factory=list)
    adjacent_keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    preferred_departments: list[str] = Field(default_factory=list)
    query_templates: list[str] = Field(default_factory=list)


class University(BaseModel):
    """University record."""
    institution: str
    domain: str
    country: str
    region: str
    qs_rank: Optional[int] = None
    notes: Optional[str] = None


class SupervisorProfile(BaseModel):
    """Extracted supervisor profile with evidence."""
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    institution: str
    country: str
    region: str
    qs_rank: Optional[int] = None
    email: Optional[str] = None
    email_confidence: str = "none"  # high|medium|low|none
    profile_url: Optional[str] = None
    homepage_url: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    publications_links: list[str] = Field(default_factory=list)
    scholar_search_url: Optional[str] = None
    fit_score: float = 0.0
    tier: str = "Adjacent"  # Core|Adjacent
    source_url: str
    evidence_snippets: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    # New fields for local DB persistence
    canonical_id: Optional[str] = None
    keywords_text: Optional[str] = None
    last_seen_at: Optional[str] = None
    last_verified_at: Optional[str] = None
    from_local_db: bool = False  # Mark if this result came from local DB
    matched_terms: list[str] = Field(default_factory=list)  # Keywords that matched during search


class ProfileExtraction(BaseModel):
    """LLM extraction result from profile page."""
    keywords: list[str] = Field(default_factory=list)
    fit_score: float = 0.0
    one_sentence_reason: str = ""


class DirectorySelection(BaseModel):
    """LLM directory URL selection."""
    directory_urls: list[str] = Field(default_factory=list)


class SupervisorRecordDB(BaseModel):
    """Database record for supervisor (with JSON serialization for keywords/evidence)."""
    id: Optional[int] = None
    canonical_id: str
    name: str
    title: Optional[str] = None
    institution: str
    domain: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    email: Optional[str] = None
    email_confidence: Optional[str] = None
    homepage: Optional[str] = None
    profile_url: Optional[str] = None
    source_url: str
    evidence_email: Optional[str] = None
    evidence_snippets_json: str  # JSON string
    keywords_json: str  # JSON string (list[str])
    keywords_text: str  # ', '.join(keywords)
    last_seen_at: str  # ISO datetime
    last_verified_at: Optional[str] = None  # ISO datetime
    created_at: str  # ISO datetime
    updated_at: str  # ISO datetime
    
    @classmethod
    def from_supervisor_profile(cls, profile: SupervisorProfile, canonical_id: str, domain: Optional[str] = None) -> "SupervisorRecordDB":
        """Create DB record from SupervisorProfile."""
        import json
        from datetime import datetime
        
        now = datetime.now().isoformat()
        
        return cls(
            canonical_id=canonical_id,
            name=profile.name,
            title=profile.title,
            institution=profile.institution,
            domain=domain,
            country=profile.country,
            region=profile.region,
            email=profile.email,
            email_confidence=profile.email_confidence,
            homepage=profile.homepage_url,
            profile_url=profile.profile_url,
            source_url=profile.source_url,
            evidence_email=profile.evidence_snippets[0] if profile.evidence_snippets else None,
            evidence_snippets_json=json.dumps(profile.evidence_snippets),
            keywords_json=json.dumps(profile.keywords),
            keywords_text=", ".join(profile.keywords) if profile.keywords else "",
            last_seen_at=now,
            last_verified_at=now if profile.email_confidence in ["high", "medium"] else None,
            created_at=now,
            updated_at=now
        )
    
    def to_supervisor_profile(self) -> SupervisorProfile:
        """Convert DB record to SupervisorProfile."""
        import json
        
        keywords = json.loads(self.keywords_json) if self.keywords_json else []
        evidence_snippets = json.loads(self.evidence_snippets_json) if self.evidence_snippets_json else []
        
        return SupervisorProfile(
            name=self.name,
            title=self.title,
            institution=self.institution,
            country=self.country or "",
            region=self.region or "",
            email=self.email,
            email_confidence=self.email_confidence or "none",
            profile_url=self.profile_url,
            homepage_url=self.homepage,
            keywords=keywords,
            fit_score=0.0,  # Will be recalculated
            tier="Adjacent",
            source_url=self.source_url,
            evidence_snippets=evidence_snippets,
            canonical_id=self.canonical_id,
            keywords_text=self.keywords_text,
            last_seen_at=self.last_seen_at,
            last_verified_at=self.last_verified_at,
            from_local_db=True
        )


class User(BaseModel):
    """User model."""
    id: Optional[int] = None
    email: str
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None


class Subscription(BaseModel):
    """Subscription model."""
    id: Optional[int] = None
    user_id: int
    subscription_type: str  # 'free', 'individual', 'enterprise'
    status: str  # 'active', 'expired', 'cancelled'
    searches_per_month: int
    remaining_searches: int
    started_at: str
    expires_at: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

