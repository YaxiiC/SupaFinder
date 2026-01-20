"""Extract key sections from CV for efficient LLM processing."""

import re
from typing import List, Tuple


class CVExtractor:
    """Extract relevant sections from CV text."""
    
    def __init__(self):
        # Section headers in multiple languages
        self.education_keywords = [
            r'education', r'educational background', r'academic background',
            r'qualification', r'degree', r'专业', r'教育背景', r'学历',
            r'major', r'field of study', r'研究方向'
        ]
        
        self.research_keywords = [
            r'research experience', r'research interests', r'research background',
            r'research', r'研究经历', r'研究兴趣', r'研究方向', r'科研经历',
            r'research projects', r'research work'
        ]
        
        self.publication_keywords = [
            r'publications', r'papers', r'publications and papers',
            r'journal articles', r'conference papers', r'patents',
            r'出版物', r'论文', r'发表', r'publication'
        ]
        
        self.skills_keywords = [
            r'skills', r'technical skills', r'competencies',
            r'programming', r'technologies', r'tools',
            r'技能', r'技术栈', r'编程'
        ]
        
        self.project_keywords = [
            r'projects', r'research projects', r'project experience',
            r'项目', r'项目经历', r'研究项目'
        ]
    
    def extract_key_sections(self, cv_text: str, max_length: int = 3000) -> str:
        """Extract key sections from CV text."""
        sections = []
        
        # Normalize text
        text = cv_text.replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')
        
        # Find section boundaries
        section_starts = self._find_section_starts(lines)
        
        # Extract each relevant section
        for section_name, start_idx in section_starts:
            if section_name in ['education', 'research', 'publication', 'skills', 'project']:
                end_idx = self._find_section_end(lines, start_idx, section_starts)
                section_text = '\n'.join(lines[start_idx:end_idx])
                if section_text.strip():
                    sections.append(f"[{section_name.upper()}]\n{section_text.strip()}")
        
        # If no sections found, try pattern-based extraction
        if not sections:
            sections = self._extract_by_patterns(text)
        
        # Combine and limit length
        combined = '\n\n'.join(sections)
        if len(combined) > max_length:
            combined = combined[:max_length] + "..."
        
        return combined if combined else cv_text[:max_length]  # Fallback to first N chars
    
    def _find_section_starts(self, lines: List[str]) -> List[Tuple[str, int]]:
        """Find where each section starts."""
        section_starts = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Skip empty lines
            if not line_lower:
                continue
            
            # Check for section headers (usually all caps, bold markers, or specific keywords)
            is_header = (
                line_lower.isupper() and len(line_lower) > 3 and len(line_lower) < 50
            ) or any(
                re.search(pattern, line_lower, re.IGNORECASE) 
                for pattern in self.education_keywords + self.research_keywords + 
                              self.publication_keywords + self.skills_keywords + 
                              self.project_keywords
            )
            
            if is_header:
                # Determine section type
                if any(re.search(p, line_lower, re.IGNORECASE) for p in self.education_keywords):
                    section_starts.append(('education', i))
                elif any(re.search(p, line_lower, re.IGNORECASE) for p in self.research_keywords):
                    section_starts.append(('research', i))
                elif any(re.search(p, line_lower, re.IGNORECASE) for p in self.publication_keywords):
                    section_starts.append(('publication', i))
                elif any(re.search(p, line_lower, re.IGNORECASE) for p in self.skills_keywords):
                    section_starts.append(('skills', i))
                elif any(re.search(p, line_lower, re.IGNORECASE) for p in self.project_keywords):
                    section_starts.append(('project', i))
        
        return section_starts
    
    def _find_section_end(self, lines: List[str], start_idx: int, all_starts: List[Tuple[str, int]]) -> int:
        """Find where a section ends (next section or end of text)."""
        # Find next section start after current one
        next_start = None
        for section_name, idx in all_starts:
            if idx > start_idx:
                next_start = idx
                break
        
        if next_start:
            return next_start
        
        # Otherwise, section ends at a reasonable distance or end of text
        max_section_length = 100  # lines
        return min(start_idx + max_section_length, len(lines))
    
    def _extract_by_patterns(self, text: str) -> List[str]:
        """Extract sections using pattern matching when structure is unclear."""
        sections = []
        
        # Extract education (look for degree patterns)
        education_pattern = re.compile(
            r'(?:education|degree|bachelor|master|phd|doctor|m\.?sc|b\.?sc|专业|学历).*?(?=\n\n|\n[A-Z][A-Z\s]{3,}:|$)',
            re.IGNORECASE | re.DOTALL
        )
        edu_match = education_pattern.search(text)
        if edu_match:
            sections.append(f"[EDUCATION]\n{edu_match.group(0).strip()[:500]}")
        
        # Extract research interests/experience
        research_pattern = re.compile(
            r'(?:research\s+(?:interests|experience|background|projects?)|研究(?:兴趣|经历|方向)).*?(?=\n\n|\n[A-Z][A-Z\s]{3,}:|$)',
            re.IGNORECASE | re.DOTALL
        )
        research_match = research_pattern.search(text)
        if research_match:
            sections.append(f"[RESEARCH]\n{research_match.group(0).strip()[:800]}")
        
        # Extract publications (look for citation patterns)
        pub_pattern = re.compile(
            r'(?:publications?|papers?|journal|conference|论文|发表).*?(?=\n\n|\n[A-Z][A-Z\s]{3,}:|$)',
            re.IGNORECASE | re.DOTALL
        )
        pub_match = pub_pattern.search(text)
        if pub_match:
            sections.append(f"[PUBLICATIONS]\n{pub_match.group(0).strip()[:800]}")
        
        # Extract skills
        skills_pattern = re.compile(
            r'(?:skills?|technical|programming|technologies|tools|技能|技术).*?(?=\n\n|\n[A-Z][A-Z\s]{3,}:|$)',
            re.IGNORECASE | re.DOTALL
        )
        skills_match = skills_pattern.search(text)
        if skills_match:
            sections.append(f"[SKILLS]\n{skills_match.group(0).strip()[:500]}")
        
        return sections


# Global extractor instance
cv_extractor = CVExtractor()

