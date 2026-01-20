"""Fix incorrectly inferred domains in universities_template.xlsx."""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Domain corrections - only fix obviously wrong domains (like "ofsouthampton")
wrong_domain_patterns = {
    "ofsouthampton.ac.uk": "soton.ac.uk",
    "ofsheffield.ac.uk": "sheffield.ac.uk",
    "ofnottingham.ac.uk": "nottingham.ac.uk",
    "ofbath.ac.uk": "bath.ac.uk",
    "ofexeter.ac.uk": "exeter.ac.uk",
    "ofyork.ac.uk": "york.ac.uk",
    "ofreading.ac.uk": "reading.ac.uk",
    "ofliverpool.ac.uk": "liverpool.ac.uk",
    "ofcapetown.edu": "uct.ac.za",
    "ofwollongong.edu.au": "uow.edu.au",
    "ofcaliforniadavis.edu": "ucdavis.edu",
    "ofcaliforniasantabarbaraucsb.edu": "ucsb.edu",
    "ofnorthcarolinaatchapelhill.edu": "unc.edu",
    "ofsourncalifornia.edu": "usc.edu",
    "ofwisconsinmadison.edu": "wisc.edu",
    "queenmaryoflondon.ac.uk": "qmul.ac.uk",
    "ofstandrews.ac.uk": "st-andrews.ac.uk",
    "lomonosovmoscowstate.edu": "msu.ru",
    "universidadedesãopaulo.edu": "usp.br",
    "pontificiauniversidadcatólicadechileuc.edu": "uc.cl",
    "universidadnacionalautónomademéxicounam.edu": "unam.mx",
    "universidaddechile.edu": "uchile.cl",
    "tecnológicodemonterrey.edu": "tec.mx",
    "universitasindonesia.edu": "ui.ac.id",
    "kingabdulazizkau.edu": "kau.edu.sa",
    "alfarabikazakhnational.edu": "kaznu.kz",
    "khalifa.edu": "ku.ac.ae",
    "georgiaoftechnology.edu": "gatech.edu",
    "texasam.edu": "tamu.edu",
    "ohiostate.edu": "osu.edu",
    "arizonastate.edu": "asu.edu",
    "newcastle.ac.uk": "ncl.ac.uk",
    "queensbelfast.ac.uk": "qub.ac.uk",
    "qatar.edu": "qu.edu.qa",
}

def fix_wrong_domains(excel_path: Path) -> None:
    """Fix incorrectly inferred domains."""
    print(f"Reading universities from {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"✓ Read {len(df)} universities")
    
    fixed_count = 0
    
    for idx, row in df.iterrows():
        domain = row.get('domain', '')
        institution = row.get('institution', '')
        
        if pd.notna(domain) and str(domain) in wrong_domain_patterns:
            old_domain = str(domain)
            new_domain = wrong_domain_patterns[old_domain]
            print(f"Fixing {institution}: {old_domain} → {new_domain}")
            df.at[idx, 'domain'] = new_domain
            fixed_count += 1
    
    # Also fix specific institutions by name (only if domain is wrong or missing)
    institution_fixes = {
        "University of Southampton": "soton.ac.uk",
        "The University of Sheffield": "sheffield.ac.uk",
        "University of Nottingham": "nottingham.ac.uk",
        "University of Bath": "bath.ac.uk",
        "University of Exeter": "exeter.ac.uk",
        "University of York": "york.ac.uk",
        "University of Reading": "reading.ac.uk",
        "University of Liverpool": "liverpool.ac.uk",
        "University of Cape Town": "uct.ac.za",
        "University of Wollongong": "uow.edu.au",
        "University of California, Davis": "ucdavis.edu",
        "University of California, Santa Barbara (UCSB)": "ucsb.edu",
        "University of North Carolina at Chapel Hill": "unc.edu",
        "University of Southern California": "usc.edu",
        "University of Wisconsin-Madison": "wisc.edu",
        "Queen Mary University of London": "qmul.ac.uk",
        "University of St Andrews": "st-andrews.ac.uk",
        "Lomonosov Moscow State University": "msu.ru",
        "Universidade de São Paulo": "usp.br",
        "Pontificia Universidad Católica de Chile (UC)": "uc.cl",
        "Universidad Nacional Autónoma de México  (UNAM)": "unam.mx",
        "Universidad de Chile": "uchile.cl",
        "Tecnológico de Monterrey": "tec.mx",
        "Universitas Indonesia": "ui.ac.id",
        "King Abdulaziz University (KAU)": "kau.edu.sa",
        "Al-Farabi Kazakh National University": "kaznu.kz",
        "National Tsing Hua University - NTHU": "nthu.edu.tw",
        "Khalifa University": "ku.ac.ae",
        "Georgia Institute of Technology": "gatech.edu",
        "RMIT University": "rmit.edu.au",
        "University of Technology Sydney": "uts.edu.au",
        "Macquarie University (Sydney, Australia)": "mq.edu.au",
        "Michigan State University": "msu.edu",
        "Washington University in St. Louis": "wustl.edu",
        "Pennsylvania State University": "psu.edu",
        "Texas A&M University": "tamu.edu",
        "The Ohio State University": "osu.edu",
        "Arizona State University": "asu.edu",
        "Newcastle University": "ncl.ac.uk",
    }
    
    for idx, row in df.iterrows():
        institution = str(row.get('institution', ''))
        if institution in institution_fixes:
            current_domain = row.get('domain', '')
            new_domain = institution_fixes[institution]
            # Only fix if domain is missing or clearly wrong
            if pd.isna(current_domain) or str(current_domain) in wrong_domain_patterns or str(current_domain) != new_domain:
                if str(current_domain) != new_domain:  # Only print if actually changing
                    print(f"Fixing {institution}: {current_domain} → {new_domain}")
                df.at[idx, 'domain'] = new_domain
                if pd.isna(current_domain) or str(current_domain) not in wrong_domain_patterns:
                    fixed_count += 1
    
    print(f"\n✓ Fixed {fixed_count} domains")
    print(f"Saving to {excel_path}")
    df.to_excel(excel_path, index=False)
    print("✓ Done!")


if __name__ == "__main__":
    excel_path = Path(__file__).parent.parent / "data" / "universities_template.xlsx"
    fix_wrong_domains(excel_path)

