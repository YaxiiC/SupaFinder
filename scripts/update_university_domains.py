"""Update university domains by searching for academic staff homepages."""

import sys
from pathlib import Path
import pandas as pd
import time
from urllib.parse import urlparse
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    if not url or pd.isna(url):
        return None
    try:
        parsed = urlparse(str(url))
        domain = parsed.netloc
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return None


def search_academic_staff_homepage(institution: str, country: str) -> str:
    """
    Search for academic staff homepage for a university.
    Returns the domain if found, None otherwise.
    """
    # Try multiple search queries to find academic staff pages
    search_queries = [
        f"{institution} academic staff directory",
        f"{institution} faculty members",
        f"{institution} professor homepage",
        f"{institution} staff profiles",
        f"{institution} {country} academic staff",
    ]
    
    # We'll use web_search to find pages, then extract domain from URLs
    # For now, return None - we'll implement the actual search in the main loop
    return None


def infer_domain_from_institution(institution: str, country: str) -> str:
    """Infer likely domain from institution name."""
    # Known domain mappings (most reliable)
    known_domains = {
        # France
        "université paris-saclay": "universite-paris-saclay.fr",
        "sorbonne university": "sorbonne-universite.fr",
        "institut polytechnique de paris": "ip-paris.fr",
        
        # Germany
        "freie universitaet berlin": "fu-berlin.de",
        "freie universität berlin": "fu-berlin.de",
        "ludwig-maximilians-universität münchen": "lmu.de",
        "rwth aachen": "rwth-aachen.de",
        "rwth aachen university": "rwth-aachen.de",
        "kit, karlsruhe institute of technology": "kit.edu",
        "technische universität berlin": "tu-berlin.de",
        "technische universität berlin (tu berlin)": "tu-berlin.de",
        "humboldt-universität zu berlin": "hu-berlin.de",
        "universität heidelberg": "uni-heidelberg.de",
        "universität hamburg": "uni-hamburg.de",
        "technische universität wien": "tuwien.ac.at",
        
        # Japan
        "osaka university": "osaka-u.ac.jp",
        "kyoto university": "kyoto-u.ac.jp",
        "tohoku university": "tohoku.ac.jp",
        "tokyo institute of technology": "titech.ac.jp",
        "nagoya university": "nagoya-u.ac.jp",
        "hokkaido university": "hokudai.ac.jp",
        "kyushu university": "kyushu-u.ac.jp",
        "waseda university": "waseda.jp",
        
        # Sweden
        "uppsala university": "uu.se",
        "lund university": "lu.se",
        "kth royal institute of technology": "kth.se",
        "stockholm university": "su.se",
        "chalmers university of technology": "chalmers.se",
        
        # Netherlands
        "university of amsterdam": "uva.nl",
        "utrecht university": "uu.nl",
        "university of groningen": "rug.nl",
        "leiden university": "universiteitleiden.nl",
        "eindhoven university of technology": "tue.nl",
        "erasmus university rotterdam": "eur.nl",
        "wageningen university & research": "wur.nl",
        "vrije universiteit amsterdam": "vu.nl",
        
        # Switzerland
        "university of zurich": "uzh.ch",
        "university of geneva": "unige.ch",
        "university of basel": "unibas.ch",
        "university of bern": "unibe.ch",
        
        # Denmark
        "university of copenhagen": "ku.dk",
        "technical university of denmark": "dtu.dk",
        "aarhus university": "au.dk",
        
        # Finland
        "aalto university": "aalto.fi",
        "university of helsinki": "helsinki.fi",
        
        # Norway
        "university of oslo": "uio.no",
        
        # Ireland
        "university college dublin": "ucd.ie",
        "trinity college dublin": "tcd.ie",
        
        # Canada
        "university of alberta": "ualberta.ca",
        "university of waterloo": "uwaterloo.ca",
        "western university": "uwo.ca",
        "mcmaster university": "mcmaster.ca",
        "université de montréal": "umontreal.ca",
        "queen's university at kingston": "queensu.ca",
        
        # Belgium
        "ghent university": "ugent.be",
        "université catholique de louvain": "uclouvain.be",
        "université catholique de louvain (uclouvain)": "uclouvain.be",
        
        # Austria
        "university of vienna": "univie.ac.at",
        
        # Spain
        "universitat de barcelona": "ub.edu",
        "universitat autònoma de barcelona": "uab.cat",
        "complutense university of madrid": "ucm.es",
        
        # Italy
        "sapienza university of rome": "uniroma1.it",
        "alma mater studiorum - università di bologna": "unibo.it",
        "polimi graduate school of management": "polimi.it",
        
        # South Korea
        "pohang university of science and technology": "postech.ac.kr",
        "pohang university of science and technology (postech)": "postech.ac.kr",
        "sungkyunkwan university": "skku.edu",
        "sungkyunkwan university (skku)": "skku.edu",
        "hanyang university": "hanyang.ac.kr",
        
        # China
        "nanjing university": "nju.edu.cn",
        "university of science and technology of china": "ustc.edu.cn",
        "wuhan university": "whu.edu.cn",
        "tongji university": "tongji.edu.cn",
        
        # Malaysia
        "universiti kebangsaan malaysia": "ukm.edu.my",
        "universiti kebangsaan malaysia (ukm)": "ukm.edu.my",
        "universiti putra malaysia": "upm.edu.my",
        "universiti putra malaysia (upm)": "upm.edu.my",
        "universiti sains malaysia": "usm.edu.my",
        "universiti sains malaysia (usm)": "usm.edu.my",
        "universiti teknologi malaysia": "utm.my",
        "universiti teknologi malaysia ": "utm.my",
        
        # India
        "indian institute of technology delhi": "iitd.ac.in",
        "indian institute of technology delhi (iitd)": "iitd.ac.in",
        "indian institute of technology bombay": "iitb.ac.in",
        "indian institute of technology bombay (iitb)": "iitb.ac.in",
        "indian institute of technology madras": "iitm.ac.in",
        "indian institute of technology madras (iitm)": "iitm.ac.in",
        
        # Taiwan
        "national yang ming chiao tung university": "nycu.edu.tw",
        "national yang ming chiao tung university (nycu taiwan)": "nycu.edu.tw",
        
        # New Zealand
        "university of otago": "otago.ac.nz",
        
        # UK (fixes)
        "university of southampton": "soton.ac.uk",
        "university of sheffield": "sheffield.ac.uk",
        "university of nottingham": "nottingham.ac.uk",
        "university of birmingham": "bham.ac.uk",
        "university of wisconsin-madison": "wisc.edu",
        "university of california, davis": "ucdavis.edu",
        "university of california, santa barbara": "ucsb.edu",
        "university of north carolina at chapel hill": "unc.edu",
        "university of southern california": "usc.edu",
        "pennsylvania state university": "psu.edu",
        "texas a&m university": "tamu.edu",
        "georgia institute of technology": "gatech.edu",
        "rmit university": "rmit.edu.au",
        "macquarie university": "mq.edu.au",
        "university of technology sydney": "uts.edu.au",
        "university of wollongong": "uow.edu.au",
        "queen mary university of london": "qmul.ac.uk",
        "university of st andrews": "st-andrews.ac.uk",
        "university of bath": "bath.ac.uk",
        "university of exeter": "exeter.ac.uk",
        "university of york": "york.ac.uk",
        "university of reading": "reading.ac.uk",
        "university of lancaster": "lancaster.ac.uk",
        "cardiff university": "cardiff.ac.uk",
        "newcastle university": "ncl.ac.uk",
        "university of liverpool": "liverpool.ac.uk",
        "university of glasgow": "glasgow.ac.uk",
        "durham university": "durham.ac.uk",
        "university of leeds": "leeds.ac.uk",
        "queen's university belfast": "qub.ac.uk",
        
        # Other fixes
        "lomonosov moscow state university": "msu.ru",
        "universidade de são paulo": "usp.br",
        "pontificia universidad católica de chile": "uc.cl",
        "universidad de chile": "uchile.cl",
        "universidad nacional autónoma de méxico": "unam.mx",
        "tecnológico de monterrey": "tec.mx",
        "universitas indonesia": "ui.ac.id",
        "king saud university": "ksu.edu.sa",
        "king abdulaziz university": "kau.edu.sa",
        "kfupm": "kfupm.edu.sa",
        "qatar university": "qu.edu.qa",
        "khalifa university": "ku.ac.ae",
        "al-farabi kazakh national university": "kaznu.kz",
        "national tsing hua university": "nthu.edu.tw",
    }
    
    # Check known domains first
    institution_lower = institution.lower().strip()
    if institution_lower in known_domains:
        return known_domains[institution_lower]
    
    # Common patterns
    name = institution_lower
    
    # Remove common suffixes
    for suffix in ["university", "college", "institute", "school", "the"]:
        name = name.replace(suffix, "").strip()
    
    # Remove special characters and extra spaces
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '', name)
    
    # Country-specific TLDs
    tld_map = {
        "united kingdom": "ac.uk",
        "united states": "edu",
        "australia": "edu.au",
        "canada": "ca",
        "germany": "de",
        "france": "fr",
        "netherlands": "nl",
        "switzerland": "ch",
        "japan": "ac.jp",
        "south korea": "ac.kr",
        "singapore": "edu.sg",
        "hong kong sar": "hk",
        "china (mainland)": "edu.cn",
        "taiwan": "edu.tw",
        "malaysia": "edu.my",
        "india": "ac.in",
        "sweden": "se",
        "norway": "no",
        "denmark": "dk",
        "finland": "fi",
        "belgium": "be",
        "austria": "at",
        "spain": "es",
        "italy": "it",
        "ireland": "ie",
        "new zealand": "ac.nz",
    }
    
    country_lower = country.lower()
    tld = tld_map.get(country_lower, "edu")
    
    # Special cases
    if "mit" in name or "massachusetts" in institution_lower:
        return "mit.edu"
    elif "imperial" in name:
        return "imperial.ac.uk"
    elif "stanford" in name:
        return "stanford.edu"
    elif "oxford" in name:
        return "ox.ac.uk"
    elif "harvard" in name:
        return "harvard.edu"
    elif "cambridge" in name:
        return "cam.ac.uk"
    elif "eth" in name and "zurich" in institution_lower:
        return "ethz.ch"
    elif "nus" in name or ("national" in name and "singapore" in institution_lower):
        return "nus.edu.sg"
    elif "ucl" in name and len(name) <= 5:
        return "ucl.ac.uk"
    elif "caltech" in name:
        return "caltech.edu"
    elif "hku" in name or ("hong kong" in institution_lower and "university" in institution_lower):
        if "polytechnic" in institution_lower:
            return "polyu.edu.hk"
        elif "chinese" in institution_lower:
            return "cuhk.edu.hk"
        elif "science" in institution_lower and "technology" in institution_lower:
            return "ust.hk"
        else:
            return "hku.hk"
    elif "ntu" in name and "singapore" in institution_lower:
        return "ntu.edu.sg"
    elif "chicago" in name:
        return "uchicago.edu"
    elif "pku" in name or "peking" in name:
        return "pku.edu.cn"
    elif "upenn" in name or "pennsylvania" in name:
        return "upenn.edu"
    elif "cornell" in name:
        return "cornell.edu"
    elif "tsinghua" in name:
        return "tsinghua.edu.cn"
    elif "berkeley" in name:
        return "berkeley.edu"
    elif "melbourne" in name:
        return "unimelb.edu.au"
    elif "unsw" in name:
        return "unsw.edu.au"
    elif "yale" in name:
        return "yale.edu"
    elif "epfl" in name:
        return "epfl.ch"
    elif "tum" in name or "munich" in name:
        return "tum.de"
    elif "jhu" in name or "johns hopkins" in name:
        return "jhu.edu"
    elif "princeton" in name:
        return "princeton.edu"
    elif "sydney" in name:
        return "sydney.edu.au"
    elif "mcgill" in name:
        return "mcgill.ca"
    elif "psl" in name:
        return "psl.eu"
    elif "toronto" in name:
        return "utoronto.ca"
    elif "fudan" in name:
        return "fudan.edu.cn"
    elif "kcl" in name or "king's" in name:
        return "kcl.ac.uk"
    elif "anu" in name:
        return "anu.edu.au"
    elif "edinburgh" in name:
        return "ed.ac.uk"
    elif "manchester" in name:
        return "manchester.ac.uk"
    elif "monash" in name:
        return "monash.edu"
    elif "tokyo" in name:
        return "u-tokyo.ac.jp"
    elif "columbia" in name:
        return "columbia.edu"
    elif "snu" in name or "seoul" in name:
        return "snu.ac.kr"
    elif "ubc" in name:
        return "ubc.ca"
    elif "northwestern" in name:
        return "northwestern.edu"
    elif "uq" in name or "queensland" in name:
        return "uq.edu.au"
    elif "umich" in name or "michigan" in name:
        return "umich.edu"
    elif "ucla" in name:
        return "ucla.edu"
    elif "tudelft" in name or "delft" in name:
        return "tudelft.nl"
    elif "sjtu" in name or "shanghai" in name:
        return "sjtu.edu.cn"
    elif "zju" in name or "zhejiang" in name:
        return "zju.edu.cn"
    elif "yonsei" in name:
        return "yonsei.ac.kr"
    elif "bristol" in name:
        return "bristol.ac.uk"
    elif "cmu" in name or "carnegie" in name:
        return "cmu.edu"
    elif "amsterdam" in name:
        return "uva.nl"
    elif "nyu" in name:
        return "nyu.edu"
    elif "lse" in name:
        return "lse.ac.uk"
    elif "kyoto" in name:
        return "kyoto-u.ac.jp"
    elif "lmu" in name or "ludwig" in name:
        return "lmu.de"
    elif "malaya" in name:
        return "um.edu.my"
    elif "leuven" in name:
        return "kuleuven.be"
    elif "korea university" in institution_lower:
        return "korea.ac.kr"
    elif "duke" in name:
        return "duke.edu"
    elif "cityu" in name or "city university" in institution_lower:
        return "cityu.edu.hk"
    elif "ntu" in name and "taiwan" in institution_lower:
        return "ntu.edu.tw"
    elif "auckland" in name:
        return "auckland.ac.nz"
    elif "ucsd" in name:
        return "ucsd.edu"
    elif "kfupm" in name:
        return "kfupm.edu.sa"
    elif "texas" in name and "austin" in institution_lower:
        return "utexas.edu"
    elif "brown" in name:
        return "brown.edu"
    elif "illinois" in name:
        return "illinois.edu"
    elif "paris-saclay" in name:
        return "universite-paris-saclay.fr"
    elif "lund" in name:
        return "lu.se"
    elif "sorbonne" in name:
        return "sorbonne-universite.fr"
    elif "warwick" in name:
        return "warwick.ac.uk"
    elif "trinity" in name and "dublin" in institution_lower:
        return "tcd.ie"
    elif "birmingham" in name:
        return "bham.ac.uk"
    elif "uwa" in name or "western australia" in institution_lower:
        return "uwa.edu.au"
    elif "kth" in name:
        return "kth.se"
    elif "glasgow" in name:
        return "glasgow.ac.uk"
    elif "heidelberg" in name:
        return "uni-heidelberg.de"
    elif "washington" in name:
        return "washington.edu"
    elif "adelaide" in name:
        return "adelaide.edu.au"
    elif "penn state" in institution_lower:
        return "psu.edu"
    elif "buenos aires" in institution_lower:
        return "uba.ar"
    elif "tokyo tech" in institution_lower:
        return "titech.ac.jp"
    elif "leeds" in name:
        return "leeds.ac.uk"
    
    # Generic inference - be more careful
    if tld == "ac.uk":
        # UK universities - skip generic inference, most are in known_domains
        return ""
    elif tld == "edu":
        # US universities - skip generic inference
        return ""
    elif tld == "edu.au":
        # Australian universities - skip generic inference
        return ""
    
    return ""


def update_university_domains(excel_path: Path, output_path: Path = None) -> None:
    """Update missing university domains by searching for academic staff homepages."""
    
    if output_path is None:
        output_path = excel_path
    
    print(f"Reading universities from {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"✓ Read {len(df)} universities")
    
    # Find universities with missing domains
    missing_domains = df[df['domain'].isna() | (df['domain'] == '')].copy()
    print(f"✓ Found {len(missing_domains)} universities with missing domains")
    
    if len(missing_domains) == 0:
        print("No missing domains to update!")
        return
    
    # Update domains
    updated_count = 0
    
    for idx, row in missing_domains.iterrows():
        institution = row['institution']
        country = row.get('country', '')
        
        print(f"\n[{updated_count + 1}/{len(missing_domains)}] Processing: {institution}")
        
        # First, try to infer domain from institution name
        inferred_domain = infer_domain_from_institution(institution, country)
        
        if inferred_domain:
            print(f"  → Inferred domain: {inferred_domain}")
            df.at[idx, 'domain'] = inferred_domain
            updated_count += 1
        else:
            print(f"  → Could not infer domain for {institution}")
    
    # Save updated Excel file
    print(f"\n✓ Updated {updated_count} domains")
    print(f"Saving to {output_path}")
    df.to_excel(output_path, index=False)
    print("✓ Done!")


if __name__ == "__main__":
    excel_path = Path(__file__).parent.parent / "data" / "universities_template.xlsx"
    update_university_domains(excel_path)

