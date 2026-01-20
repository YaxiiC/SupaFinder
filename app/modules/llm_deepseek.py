"""DeepSeek LLM client with JSON mode and retries."""

import json
from typing import Type, TypeVar
from openai import OpenAI
from pydantic import BaseModel

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from app.schemas import ResearchProfile, ProfileExtraction, DirectorySelection

T = TypeVar("T", bound=BaseModel)


class DeepSeekClient:
    """DeepSeek API client using OpenAI-compatible interface."""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        self.model = DEEPSEEK_MODEL
    
    def _call(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
        """Make an API call with retries."""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
        return ""
    
    def _parse_json(self, text: str, model_class: Type[T]) -> T:
        """Parse JSON response into Pydantic model."""
        try:
            data = json.loads(text)
            return model_class(**data)
        except Exception:
            return model_class()
    
    def cv_to_research_profile(self, cv_text: str, keywords: str) -> ResearchProfile:
        """Extract research profile from CV and keywords.
        
        Args:
            cv_text: CV text (can be empty string if CV not provided)
            keywords: User-provided keywords (can be empty string if keywords not provided)
        """
        # Adjust prompt based on what's available
        if not cv_text and not keywords:
            # Should not happen, but handle gracefully
            cv_text = "No CV provided"
            keywords = "No keywords provided"
        elif not cv_text:
            # Only keywords provided
            cv_text = "No CV provided - using keywords only"
        elif not keywords:
            # Only CV provided
            keywords = "No explicit keywords provided - extract from CV"
        
        system_prompt = """You are a PhD supervisor search assistant. From the user's CV text and keywords, output strict JSON:
- core_keywords (10-20): PRIMARY, HIGH-LEVEL, GENERAL research field terms (e.g., "clinical medicine", "oncology", "cancer research", "biomedical engineering")
  CRITICAL: Use ONLY broad, high-level research field terms. DO NOT include:
    - Specific technical terms (e.g., "NSCLC", "CRISPR-Cas9", "EGFR-TKI resistance")
    - Gene names, protein names, or molecular pathways
    - Specific methodologies or techniques (e.g., "RNA-seq", "ChIP-seq")
    - Specific diseases or conditions (unless it's the main field, e.g., "lung cancer" is OK, but "non-small cell lung cancer" is too specific)
  Examples of GOOD keywords: "oncology", "cancer research", "medical imaging", "biomedical sciences"
  Examples of BAD keywords: "NSCLC", "EGFR mutation", "CRISPR gene editing", "single-cell RNA sequencing"
  
- adjacent_keywords (10-20): related/broader HIGH-LEVEL terms (e.g., "biomedical research", "medical sciences", "health sciences", NOT "EGFR-TKI resistance" or "tumor microenvironment signaling")
  Same rules: only high-level, general terms. Think of terms that describe research AREAS, not specific projects or techniques.

- negative_keywords (5-10): terms to exclude - ONLY include fields that are COMPLETELY unrelated to the research area
  CRITICAL: DO NOT include engineering, computer science, physics, chemistry, mathematics, or other STEM fields as negative keywords, as these may be relevant (e.g., biomedical engineering, computational medicine, medical physics, pharmaceutical chemistry).
  Only include truly unrelated fields like: political science, economics (if not health economics), literature, arts, etc.

- preferred_departments (3-8): likely department names
- query_templates (5-10): search templates, MUST include placeholder site:{domain}

CRITICAL: Focus ONLY on HIGH-LEVEL, GENERAL research fields. Think of terms that supervisors would use to broadly describe their research area in a department website or conference. Avoid any specific technical details, methodologies, or narrow topics.

Output JSON only. No explanation.

If CV text is not provided, extract keywords based on the user-provided keywords only.
If keywords are not provided, extract keywords from the CV text.
If both are provided, use both to extract the most accurate research profile."""
        
        user_prompt = f"CV:\n{cv_text}\n\nUser-provided keywords:\n{keywords}\n\nExtract ONLY HIGH-LEVEL, GENERAL research field keywords. Do NOT include specific technical terms, gene names, methodologies, or detailed techniques. Think broad research areas, not specific projects. Do NOT exclude engineering, computer science, physics, chemistry, or mathematics as these may be relevant to medical research."
        response = self._call(system_prompt, user_prompt)
        return self._parse_json(response, ResearchProfile)
    
    def extract_profile_keywords(self, page_text: str, research_profile: ResearchProfile) -> ProfileExtraction:
        """Extract keywords and fit score from profile page."""
        system_prompt = """Given a supervisor profile page text and the user research profile, output strict JSON:
- keywords (5-12): HIGH-LEVEL, GENERAL research keywords from this supervisor's profile
  CRITICAL: Extract ONLY broad, high-level research field terms. DO NOT include:
    - Specific technical terms, gene names, protein names, or molecular pathways
    - Specific methodologies or techniques (e.g., "RNA-seq", "CRISPR", "flow cytometry")
    - Specific project details or narrow research topics
  Examples of GOOD keywords: "oncology", "cancer research", "medical imaging", "biomedical engineering", "translational medicine"
  Examples of BAD keywords: "EGFR mutation", "CRISPR-Cas9", "single-cell sequencing", "tumor microenvironment signaling pathways"
  Think of terms that broadly describe the supervisor's research AREA, not specific projects or techniques.
  
- fit_score (0-1): relevance to user's research (based on high-level field match, not specific technical details)
- one_sentence_reason: brief explanation of the high-level field match

Do not invent facts not present in the text. Focus on HIGH-LEVEL research areas only. Output JSON only."""
        
        user_prompt = f"""User research profile (HIGH-LEVEL keywords):
Core keywords: {', '.join(research_profile.core_keywords)}
Adjacent keywords: {', '.join(research_profile.adjacent_keywords)}

Supervisor page text:
{page_text[:4000]}

Extract ONLY HIGH-LEVEL, GENERAL research keywords from the supervisor's profile. Match based on broad research fields, not specific technical details."""  # Limit tokens
        
        response = self._call(system_prompt, user_prompt)
        return self._parse_json(response, ProfileExtraction)
    
    def select_directory_urls(self, candidate_urls: list[str], domain: str) -> DirectorySelection:
        """Select best directory URLs from candidates."""
        system_prompt = """You are given candidate URLs for a university domain. Choose 5-10 most likely staff/faculty/people directory pages.
Output JSON: { "directory_urls": [ ... ] }"""
        
        user_prompt = f"Domain: {domain}\n\nCandidate URLs:\n" + "\n".join(candidate_urls[:50])
        response = self._call(system_prompt, user_prompt)
        return self._parse_json(response, DirectorySelection)


# Global client instance
llm_client = DeepSeekClient()

