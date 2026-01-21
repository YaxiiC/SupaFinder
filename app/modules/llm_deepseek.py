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
- core_keywords (10-20): PRIMARY, HIGH-LEVEL, GENERAL research field terms 
  CRITICAL: Use ONLY broad, high-level research field terms. DO NOT include:
    - Specific technical terms (e.g., "NSCLC", "CRISPR-Cas9", "EGFR-TKI resistance")
    - Gene names, protein names, or molecular pathways
    - Specific methodologies or techniques (e.g., "RNA-seq", "ChIP-seq")
    - Specific diseases or conditions (unless it's the main field, e.g., "lung cancer" is OK, but "non-small cell lung cancer" is too specific)
  
  IMPORTANT: Accurately identify the PRIMARY field category:
    - If the research is SOCIAL SCIENCES/EDUCATION/PSYCHOLOGY related (e.g., music therapy, music education, educational psychology, social work, counseling, therapy in social contexts), use keywords from: psychology, education, social sciences, educational sciences, counseling psychology, music education, educational psychology, social psychology, developmental psychology, etc.
    - If the research is CLINICAL/MEDICAL related (e.g., clinical medicine, medical treatment, hospital-based therapy, medical rehabilitation), use keywords from: clinical medicine, health sciences, medical sciences, rehabilitation medicine, etc.
    - If the research is in between, prioritize the PRIMARY context. For example:
      * "Music therapy" → PRIMARY field is PSYCHOLOGY/EDUCATION, NOT clinical medicine
      * "Art therapy" → PRIMARY field is PSYCHOLOGY/SOCIAL SCIENCES
      * "Occupational therapy" → Can be both, but if mentioned with "education" or "psychology", prioritize education/psychology
      * "Speech therapy" → Can be clinical OR educational; determine from context
  
  Examples of GOOD keywords by category:
    - Social/Educational: "psychology", "education", "educational psychology", "music education", "counseling psychology", "social sciences", "developmental psychology"
    - Medical/Clinical: "clinical medicine", "medical sciences", "health sciences", "rehabilitation medicine", "biomedical sciences"
    - Music therapy specifically: "music therapy", "music psychology", "music education", "therapeutic music", "applied music psychology", NOT "clinical medicine" or "medical sciences" unless explicitly in a medical context
  
  Examples of BAD keywords: "NSCLC", "EGFR mutation", "CRISPR gene editing", "single-cell RNA sequencing"
  
- adjacent_keywords (10-20): related/broader HIGH-LEVEL terms that are RELEVANT to the same field category
  IMPORTANT: Match the field category of core_keywords:
    - If core_keywords are psychology/education: use terms like "psychology", "education", "cognitive sciences", "behavioral sciences", "human development", "social sciences", "educational research"
    - If core_keywords are medical/clinical: use terms like "biomedical research", "medical sciences", "health sciences", "clinical sciences", "public health"
    - Do NOT mix categories: if core is psychology/education, do NOT add "clinical medicine" or "medical sciences" as adjacent keywords
  
  Same rules: only high-level, general terms. Think of terms that describe research AREAS, not specific projects or techniques.

- negative_keywords (5-10): terms to exclude - ONLY include fields that are COMPLETELY unrelated to the research area
  CRITICAL: DO NOT include engineering, computer science, physics, chemistry, mathematics, or other STEM fields as negative keywords, as these may be relevant.
  IMPORTANT: If the research is in psychology/education (e.g., music therapy), DO include "clinical medicine", "medical sciences" as negative keywords if they are NOT the primary context. This prevents over-association with medical fields.
  Only include truly unrelated fields like: political science, economics (if not relevant), literature (if not arts-related research), etc.

- preferred_departments (3-8): likely department names matching the field category
  - For psychology/education: "Psychology", "Education", "Music Education", "Educational Psychology", "Counseling", "Human Development"
  - For medical/clinical: "Medicine", "Health Sciences", "Rehabilitation Medicine", "Clinical Medicine"
  
- query_templates (5-10): search templates, MUST include placeholder site:{domain}

CRITICAL: 
1. Focus ONLY on HIGH-LEVEL, GENERAL research fields
2. Accurately identify the PRIMARY field category (social sciences/education/psychology vs medical/clinical)
3. Do NOT over-associate therapy/intervention terms with medical sciences if the context is primarily social/educational/psychological
4. Think of terms that supervisors would use to broadly describe their research area in a department website or conference
5. Avoid any specific technical details, methodologies, or narrow topics

Output JSON only. No explanation.

If CV text is not provided, extract keywords based on the user-provided keywords only.
If keywords are not provided, extract keywords from the CV text.
If both are provided, use both to extract the most accurate research profile."""
        
        user_prompt = f"""CV:
{cv_text}

User-provided keywords:
{keywords}

Extract ONLY HIGH-LEVEL, GENERAL research field keywords. 

IMPORTANT: Carefully identify whether this research belongs to:
- SOCIAL SCIENCES/EDUCATION/PSYCHOLOGY domain (e.g., music therapy, music education, educational psychology, counseling)
- MEDICAL/CLINICAL domain (e.g., clinical medicine, medical treatment, hospital-based therapy)

Do NOT over-associate therapy/intervention terms with medical sciences if the primary context is social/educational/psychological.

Do NOT include specific technical terms, gene names, methodologies, or detailed techniques. Think broad research areas, not specific projects. Match adjacent keywords to the same field category as core keywords."""
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

