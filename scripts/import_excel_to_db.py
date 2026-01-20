"""Import supervisors from Excel file to local database."""

import sys
from pathlib import Path
import pandas as pd
import re
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas import SupervisorProfile
from app.modules.local_repo import upsert_supervisor
from app.db import init_db


def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    if not url or pd.isna(url):
        return None
    try:
        parsed = urlparse(str(url))
        return parsed.netloc
    except Exception:
        return None


def parse_keywords(keywords_str) -> list[str]:
    """Parse keywords from string to list."""
    if pd.isna(keywords_str) or not keywords_str:
        return []
    if isinstance(keywords_str, str):
        # Split by comma and clean
        return [k.strip() for k in keywords_str.split(",") if k.strip()]
    return []


def parse_evidence_snippets(evidence_str) -> list[str]:
    """Parse evidence snippets from string to list."""
    if pd.isna(evidence_str) or not evidence_str:
        return []
    if isinstance(evidence_str, str):
        # Split by pipe or comma
        if " | " in evidence_str:
            return [e.strip() for e in evidence_str.split(" | ") if e.strip()]
        elif "," in evidence_str:
            return [e.strip() for e in evidence_str.split(",") if e.strip()]
        else:
            return [evidence_str.strip()] if evidence_str.strip() else []
    return []


def clean_name(name: str) -> str:
    """Clean name by removing titles and fixing 'essor' issue."""
    if not name or pd.isna(name):
        return ""
    
    name = str(name)
    
    # Remove extra whitespace
    name = " ".join(name.split())
    
    # Remove common prefixes (case-insensitive, anywhere in the string)
    prefixes = ["Dr.", "Dr", "Prof.", "Prof", "Professor", "Mr.", "Mr", "Mrs.", "Mrs", "Ms.", "Ms"]
    for prefix in prefixes:
        # Remove from start
        if name.lower().startswith(prefix.lower() + " "):
            name = name[len(prefix):].strip()
        elif name.lower().startswith(prefix.lower()):
            name = name[len(prefix):].strip()
        # Also remove if it appears anywhere (e.g., "Professor John Smith" -> "John Smith")
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(prefix) + r'\b'
        name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
    
    # Remove "essor" if it appears at the start (leftover from "Professor")
    if name.lower().startswith("essor "):
        name = name[6:].strip()
    elif name.lower().startswith("essor"):
        name = name[5:].strip()
    
    # Remove email addresses if accidentally included
    name = re.sub(r'\S+@\S+', '', name).strip()
    
    # Remove URLs if accidentally included
    name = re.sub(r'https?://[^\s]+', '', name)
    name = re.sub(r'www\.[^\s]+', '', name)
    
    # Clean up multiple spaces
    name = " ".join(name.split())
    
    return name.strip()


def import_excel_to_db(excel_path: Path, email_confidence_filter: str = "high") -> None:
    """Import supervisors from Excel file to database."""
    
    print(f"Importing supervisors from {excel_path}")
    
    # Initialize database
    init_db()
    print("✓ Database initialized")
    
    # Read Excel file
    df = pd.read_excel(excel_path)
    print(f"✓ Read {len(df)} rows from Excel")
    
    # Filter by email confidence
    if "Email Confidence" in df.columns:
        df_filtered = df[df["Email Confidence"] == email_confidence_filter].copy()
        print(f"✓ Filtered to {len(df_filtered)} rows with '{email_confidence_filter}' email confidence")
    else:
        print("Warning: 'Email Confidence' column not found, importing all rows")
        df_filtered = df.copy()
    
    if len(df_filtered) == 0:
        print("No rows to import!")
        return
    
    # Import each row
    imported_count = 0
    skipped_count = 0
    
    for idx, row in df_filtered.iterrows():
        try:
            # Extract domain from Profile URL or Homepage URL
            domain = None
            if "Profile URL" in row and pd.notna(row["Profile URL"]):
                domain = extract_domain_from_url(row["Profile URL"])
            elif "Homepage URL" in row and pd.notna(row["Homepage URL"]):
                domain = extract_domain_from_url(row["Homepage URL"])
            
            # Parse keywords
            keywords = parse_keywords(row.get("Keywords", ""))
            
            # Parse evidence snippets
            evidence_snippets = parse_evidence_snippets(row.get("Evidence Snippets", ""))
            
            # Clean the name to remove "Professor" and "essor"
            raw_name = str(row["Name"]) if pd.notna(row["Name"]) else ""
            cleaned_name = clean_name(raw_name)
            
            # Create SupervisorProfile
            profile = SupervisorProfile(
                name=cleaned_name,
                title=str(row["Title"]) if pd.notna(row["Title"]) and pd.notna(row["Title"]) else None,
                institution=str(row["Institution"]) if pd.notna(row["Institution"]) else "",
                country="",  # Not in Excel, will be empty
                region=str(row["Region"]) if pd.notna(row["Region"]) else "",
                qs_rank=int(row["QS Rank"]) if pd.notna(row["QS Rank"]) else None,
                email=str(row["Email"]) if pd.notna(row["Email"]) else None,
                email_confidence=str(row["Email Confidence"]) if pd.notna(row["Email Confidence"]) else "none",
                profile_url=str(row["Profile URL"]) if pd.notna(row["Profile URL"]) else None,
                homepage_url=str(row["Homepage URL"]) if pd.notna(row["Homepage URL"]) else None,
                keywords=keywords,
                publications_links=[],  # Not parsing this for now
                scholar_search_url=str(row["Scholar Search URL"]) if pd.notna(row.get("Scholar Search URL")) else None,
                fit_score=float(row["Fit Score"]) if pd.notna(row.get("Fit Score")) else 0.0,
                tier=str(row["Tier"]) if pd.notna(row.get("Tier")) else "Adjacent",
                source_url=str(row["Source URL"]) if pd.notna(row["Source URL"]) else "",
                evidence_snippets=evidence_snippets,
                notes=str(row["Notes"]) if pd.notna(row.get("Notes")) else None,
                from_local_db=False
            )
            
            # Upsert to database
            upsert_supervisor(profile, domain=domain)
            imported_count += 1
            
            if imported_count % 10 == 0:
                print(f"  Imported {imported_count} supervisors...")
                
        except Exception as e:
            print(f"  Error importing row {idx}: {e}")
            skipped_count += 1
            continue
    
    print()
    print(f"Import complete!")
    print(f"  ✓ Imported: {imported_count}")
    print(f"  ✗ Skipped: {skipped_count}")


if __name__ == "__main__":
    excel_path = Path(__file__).parent.parent / "outputs" / "supervisors.xlsx"
    import_excel_to_db(excel_path, email_confidence_filter="high")

