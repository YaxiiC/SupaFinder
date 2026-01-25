"""Streamlit UI for editing supervisors in the database.
streamlit run ui/edit_supervisors.py

"""

import streamlit as st
import sqlite3
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import CACHE_DB
from app.modules.utils_identity import compute_canonical_id

st.set_page_config(
    page_title="Edit Supervisors Database",
    page_icon="✏️",
    layout="wide"
)

st.title("✏️ Edit Supervisors Database")
st.markdown("*View and edit supervisor records in the local database*")

# Initialize connection
@st.cache_resource
def get_db_connection():
    return sqlite3.connect(CACHE_DB, check_same_thread=False)

def get_cursor():
    """Get a fresh cursor from the cached connection."""
    conn = get_db_connection()
    return conn, conn.cursor()

# Sidebar for navigation
st.sidebar.header("Navigation")

# Add new supervisor section
with st.sidebar.expander("➕ Add New Supervisor", expanded=False):
    st.markdown("**Extract from URL**")
    new_profile_url = st.text_input(
        "Profile URL",
        placeholder="https://profiles.example.edu/person/john-smith",
        key="new_profile_url"
    )
    
    # Research area context (optional, for better keyword extraction)
    research_context = st.text_input(
        "Research Context (optional)",
        placeholder="e.g., music therapy, materials science",
        help="Optional: Provide research area context for better keyword extraction",
        key="research_context"
    )
    
    if st.button("🔍 Extract from URL", use_container_width=True, key="extract_btn"):
        if new_profile_url:
            with st.spinner("Extracting information from URL..."):
                try:
                    # Import necessary modules
                    from app.modules.crawl import crawler
                    from app.modules.profile import profile_extractor
                    from app.modules.llm_deepseek import llm_client
                    from app.schemas import ResearchProfile, SupervisorProfile, University
                    from urllib.parse import urlparse
                    
                    # Fetch the page
                    page = crawler.fetch(new_profile_url)
                    
                    if page["status_code"] != 200:
                        st.error(f"Failed to fetch URL: HTTP {page['status_code']}")
                    else:
                        # Extract domain and try to infer university
                        parsed_url = urlparse(new_profile_url)
                        domain = parsed_url.netloc
                        
                        # Create a dummy university for extraction
                        dummy_university = University(
                            institution="Unknown",  # Will be updated by user
                            country="",
                            region="",
                            domain=domain,
                            qs_rank=None
                        )
                        
                        # Create a research profile (use provided context or empty)
                        # For keyword extraction from profile page, we don't need user's research profile
                        # The LLM will extract keywords directly from the supervisor's page
                        research_profile = ResearchProfile()  # Empty - keywords extracted from page content
                        
                        # Extract profile information
                        html = page.get("html", "")
                        text_content = page.get("text_content", "")
                        
                        # Try extraction with allow_student_postdoc=True and allow_low_fit_score=True for manual addition
                        profile, failure_reason = profile_extractor.extract(
                            html=html,
                            text_content=text_content,
                            url=new_profile_url,
                            university=dummy_university,
                            research_profile=research_profile,
                            debug=True,
                            allow_student_postdoc=True,  # Allow student/postdoc for manual addition
                            allow_low_fit_score=True     # Allow low fit_score for manual addition
                        )
                        
                        if profile:
                            # Store extracted profile in session state for form
                            st.session_state['extracted_profile'] = {
                                'name': profile.name or '',
                                'title': profile.title or '',
                                'institution': profile.institution or '',
                                'domain': domain,
                                'country': profile.country or '',
                                'region': profile.region or '',
                                'email': profile.email or '',
                                'email_confidence': profile.email_confidence or 'none',
                                'profile_url': new_profile_url,
                                'homepage_url': profile.homepage_url or '',
                                'keywords': profile.keywords or [],
                                'evidence_snippets': profile.evidence_snippets or []
                            }
                            
                            # Show appropriate warnings/messages
                            warnings = []
                            if failure_reason == "student_postdoc":
                                warnings.append("detected as student/postdoc position")
                            if profile.fit_score is not None and profile.fit_score < 0.1:
                                warnings.append(f"low fit_score ({profile.fit_score:.2f})")
                            
                            if warnings:
                                st.warning(f"⚠️ Extracted profile, but {', '.join(warnings)}. You can still add it manually.")
                            else:
                                st.success("✓ Successfully extracted profile information!")
                            st.info("Please fill in any missing information below and click 'Add to Database'")
                        else:
                            # Even if extraction failed, try to extract basic info (name, email) for manual entry
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html, "html.parser")
                                
                                # Try to extract at least name and email
                                basic_name = profile_extractor._extract_name(soup, text_content, new_profile_url)
                                basic_email, _, _ = profile_extractor._extract_email(html, text_content)
                                
                                if basic_name or basic_email:
                                    # Extract keywords using LLM even if full extraction failed
                                    extraction = llm_client.extract_profile_keywords(text_content[:4000], research_profile)
                                    
                                    st.warning(f"⚠️ Full extraction failed: {failure_reason}")
                                    st.info("Extracted basic information. You can manually add the supervisor below.")
                                    
                                    # Store basic info for manual entry
                                    st.session_state['extracted_profile'] = {
                                        'name': basic_name or '',
                                        'title': '',
                                        'institution': '',
                                        'domain': domain,
                                        'country': '',
                                        'region': '',
                                        'email': basic_email or '',
                                        'email_confidence': 'high' if basic_email else 'none',
                                        'profile_url': new_profile_url,
                                        'homepage_url': '',
                                        'keywords': extraction.keywords if extraction else [],
                                        'evidence_snippets': []
                                    }
                                else:
                                    st.error(f"Failed to extract profile: {failure_reason}")
                                    st.info("You can still manually add the supervisor below.")
                            except Exception as e2:
                                st.error(f"Failed to extract profile: {failure_reason}")
                                st.info("You can still manually add the supervisor below.")
                except Exception as e:
                    st.error(f"Error extracting profile: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.warning("Please enter a profile URL")
    
    # Manual add form
    st.markdown("**Or Add Manually**")
    if st.button("📝 Add Manually", use_container_width=True, key="manual_add_btn"):
        st.session_state['show_add_form'] = True

# Get total count
conn, cursor = get_cursor()
cursor.execute("SELECT COUNT(*) FROM supervisors")
total_count = cursor.fetchone()[0]
st.sidebar.metric("Total Supervisors", total_count)

# Search and filter
search_query = st.sidebar.text_input("🔍 Search by name or institution")
filter_confidence = st.sidebar.selectbox(
    "Filter by Email Confidence",
    ["All", "high", "medium", "low", "none"]
)

# Build query
query = "SELECT id, name, institution, email, email_confidence, title, keywords_text, profile_url FROM supervisors WHERE 1=1"
params = []

if search_query:
    query += " AND (name LIKE ? OR institution LIKE ?)"
    params.extend([f"%{search_query}%", f"%{search_query}%"])

if filter_confidence != "All":
    query += " AND email_confidence = ?"
    params.append(filter_confidence)

query += " ORDER BY last_seen_at DESC"

conn, cursor = get_cursor()
cursor.execute(query, params)
rows = cursor.fetchall()

# Add new supervisor form (if requested)
if st.session_state.get('show_add_form') or st.session_state.get('extracted_profile'):
    st.subheader("➕ Add New Supervisor")
    with st.form("add_supervisor_form"):
        # Pre-fill with extracted data if available
        extracted = st.session_state.get('extracted_profile', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name *", value=extracted.get('name', ''), key="add_name")
            title = st.text_input("Title", value=extracted.get('title', ''), key="add_title")
            institution = st.text_input("Institution *", value=extracted.get('institution', ''), key="add_institution")
            domain = st.text_input("Domain", value=extracted.get('domain', ''), key="add_domain")
            country = st.text_input("Country", value=extracted.get('country', ''), key="add_country")
            region = st.text_input("Region", value=extracted.get('region', ''), key="add_region")
        
        with col2:
            email = st.text_input("Email", value=extracted.get('email', ''), key="add_email")
            email_confidence = st.selectbox(
                "Email Confidence",
                ["none", "low", "medium", "high"],
                index=["none", "low", "medium", "high"].index(extracted.get('email_confidence', 'none')),
                key="add_email_confidence"
            )
            profile_url = st.text_input("Profile URL *", value=extracted.get('profile_url', ''), key="add_profile_url")
            homepage = st.text_input("Homepage", value=extracted.get('homepage_url', ''), key="add_homepage")
            source_url = st.text_input("Source URL *", value=extracted.get('profile_url', ''), key="add_source_url")
        
        # Keywords
        extracted_keywords = extracted.get('keywords', [])
        keywords_text = st.text_area(
            "Keywords (comma-separated)",
            value=", ".join(extracted_keywords) if extracted_keywords else "",
            key="add_keywords",
            help="Comma-separated list of research keywords"
        )
        
        # Evidence snippets
        extracted_evidence = extracted.get('evidence_snippets', [])
        evidence_text = st.text_area(
            "Evidence Snippets (comma-separated)",
            value=", ".join(extracted_evidence) if extracted_evidence else "",
            key="add_evidence"
        )
        
        # Submit button
        col_submit1, col_submit2, col_submit3 = st.columns([1, 1, 2])
        with col_submit1:
            submitted = st.form_submit_button("✅ Add to Database", use_container_width=True)
        with col_submit2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if submitted:
            if not name or not institution or not profile_url:
                st.error("Name, Institution, and Profile URL are required!")
            else:
                try:
                    # Convert keywords and evidence to JSON
                    keywords_list = [k.strip() for k in keywords_text.split(",") if k.strip()]
                    evidence_list = [e.strip() for e in evidence_text.split(",") if e.strip()]
                    
                    # Import SupervisorProfile and upsert function
                    from app.schemas import SupervisorProfile
                    from app.modules.local_repo import upsert_supervisor
                    
                    # Create SupervisorProfile
                    new_profile = SupervisorProfile(
                        name=name,
                        title=title if title else None,
                        institution=institution,
                        country=country if country else "",
                        region=region if region else "",
                        email=email if email else None,
                        email_confidence=email_confidence,
                        profile_url=profile_url,
                        homepage_url=homepage if homepage else None,
                        keywords=keywords_list,
                        publications_links=[],
                        scholar_search_url=None,
                        fit_score=0.0,
                        tier="Adjacent",
                        source_url=source_url if source_url else profile_url,
                        evidence_snippets=evidence_list,
                        notes=None
                    )
                    
                    # Save to database
                    upsert_supervisor(new_profile, domain=domain if domain else None)
                    
                    # Clear session state
                    if 'extracted_profile' in st.session_state:
                        del st.session_state['extracted_profile']
                    if 'show_add_form' in st.session_state:
                        del st.session_state['show_add_form']
                    
                    st.success(f"✓ Successfully added supervisor: {name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding supervisor: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        if cancel:
            # Clear session state
            if 'extracted_profile' in st.session_state:
                del st.session_state['extracted_profile']
            if 'show_add_form' in st.session_state:
                del st.session_state['show_add_form']
            st.rerun()
    
    st.divider()

# Display supervisors
st.subheader(f"Supervisors ({len(rows)} shown)")

if rows:
    # Bulk deletion section
    with st.expander("🗑️ Bulk Delete Supervisors", expanded=False):
        st.markdown("**Select multiple supervisors to delete**")
        
        # Create options for multi-select
        supervisor_options_dict = {f"{row[0]}: {row[1]} ({row[2]})": row[0] for row in rows}
        supervisor_options_list = list(supervisor_options_dict.keys())
        
        selected_for_deletion = st.multiselect(
            "Select supervisors to delete:",
            options=supervisor_options_list,
            key="bulk_delete_select",
            help="Select one or more supervisors to delete. Use Ctrl/Cmd to select multiple."
        )
        
        if selected_for_deletion:
            st.warning(f"⚠️ {len(selected_for_deletion)} supervisor(s) selected for deletion")
            
            # Show selected supervisors
            with st.expander("View selected supervisors", expanded=False):
                for option in selected_for_deletion:
                    st.text(f"  • {option}")
            
            # Confirmation and delete button
            col_del1, col_del2 = st.columns([1, 1])
            with col_del1:
                if st.button("🗑️ Delete Selected", type="primary", use_container_width=True, key="bulk_delete_btn"):
                    if st.session_state.get('confirm_bulk_delete') != tuple(selected_for_deletion):
                        st.session_state['confirm_bulk_delete'] = tuple(selected_for_deletion)
                        st.warning("⚠️ Click again to confirm bulk deletion")
                    else:
                        try:
                            conn, cursor = get_cursor()
                            deleted_count = 0
                            deleted_names = []
                            
                            for option in selected_for_deletion:
                                supervisor_id = supervisor_options_dict[option]
                                # Get name before deleting for confirmation message
                                cursor.execute("SELECT name FROM supervisors WHERE id = ?", (supervisor_id,))
                                name_result = cursor.fetchone()
                                name = name_result[0] if name_result else f"ID {supervisor_id}"
                                
                                cursor.execute("DELETE FROM supervisors WHERE id = ?", (supervisor_id,))
                                deleted_count += 1
                                deleted_names.append(name)
                            
                            conn.commit()
                            
                            # Clear confirmation state
                            if 'confirm_bulk_delete' in st.session_state:
                                del st.session_state['confirm_bulk_delete']
                            
                            st.success(f"✓ Successfully deleted {deleted_count} supervisor(s): {', '.join(deleted_names[:5])}{'...' if len(deleted_names) > 5 else ''}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting supervisors: {e}")
                            import traceback
                            st.code(traceback.format_exc())
            
            with col_del2:
                if st.button("❌ Clear Selection", use_container_width=True, key="clear_bulk_delete_btn"):
                    if 'confirm_bulk_delete' in st.session_state:
                        del st.session_state['confirm_bulk_delete']
                    st.rerun()
    
    st.divider()
    
    # Create a selectbox for choosing supervisor
    supervisor_options = {f"{row[0]}: {row[1]} ({row[2]})": row[0] for row in rows}
    selected = st.selectbox("Select a supervisor to edit:", list(supervisor_options.keys()))
    selected_id = supervisor_options[selected]
    
    # Get full supervisor record
    conn, cursor = get_cursor()
    cursor.execute("SELECT * FROM supervisors WHERE id = ?", (selected_id,))
    row = cursor.fetchone()
    
    # Get column names
    cursor.execute("PRAGMA table_info(supervisors)")
    columns = [col[1] for col in cursor.fetchall()]
    supervisor = dict(zip(columns, row))
    
    # Display and edit form
    st.divider()
    st.subheader(f"Editing: {supervisor['name']}")
    
    with st.form("edit_supervisor_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name", value=supervisor.get('name', ''))
            title = st.text_input("Title", value=supervisor.get('title', ''))
            institution = st.text_input("Institution", value=supervisor.get('institution', ''))
            domain = st.text_input("Domain", value=supervisor.get('domain', ''))
            country = st.text_input("Country", value=supervisor.get('country', ''))
            region = st.text_input("Region", value=supervisor.get('region', ''))
        
        with col2:
            email = st.text_input("Email", value=supervisor.get('email', ''))
            email_confidence = st.selectbox(
                "Email Confidence",
                ["high", "medium", "low", "none"],
                index=["high", "medium", "low", "none"].index(supervisor.get('email_confidence', 'none')) if supervisor.get('email_confidence') in ["high", "medium", "low", "none"] else 3
            )
            profile_url = st.text_input("Profile URL", value=supervisor.get('profile_url', ''))
            homepage = st.text_input("Homepage", value=supervisor.get('homepage', ''))
            source_url = st.text_input("Source URL", value=supervisor.get('source_url', ''))
        
        # Keywords
        keywords_json = supervisor.get('keywords_json', '[]')
        try:
            keywords_list = json.loads(keywords_json)
        except:
            keywords_list = []
        keywords_text = st.text_area(
            "Keywords (comma-separated)",
            value=", ".join(keywords_list) if keywords_list else ""
        )
        
        # Evidence snippets
        evidence_json = supervisor.get('evidence_snippets_json', '[]')
        try:
            evidence_list = json.loads(evidence_json)
        except:
            evidence_list = []
        evidence_text = st.text_area(
            "Evidence Snippets (comma-separated)",
            value=", ".join(evidence_list) if evidence_list else ""
        )
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)
        
        if submitted:
            try:
                # Convert keywords and evidence to JSON
                keywords_list = [k.strip() for k in keywords_text.split(",") if k.strip()]
                evidence_list = [e.strip() for e in evidence_text.split(",") if e.strip()]
                
                # Recompute canonical_id if key fields changed
                new_canonical_id = compute_canonical_id(
                    email=email,
                    name=name,
                    institution=institution,
                    domain=domain,
                    profile_url=profile_url
                )
                
                # Update database
                conn, cursor = get_cursor()
                cursor.execute("""
                    UPDATE supervisors SET
                        name = ?, title = ?, institution = ?, domain = ?,
                        country = ?, region = ?, email = ?, email_confidence = ?,
                        profile_url = ?, homepage = ?, source_url = ?,
                        keywords_json = ?, keywords_text = ?,
                        evidence_snippets_json = ?, canonical_id = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (
                    name, title, institution, domain,
                    country, region, email, email_confidence,
                    profile_url, homepage, source_url,
                    json.dumps(keywords_list), ", ".join(keywords_list),
                    json.dumps(evidence_list), new_canonical_id,
                    selected_id
                ))
                
                conn.commit()
                st.success(f"✓ Successfully updated supervisor {selected_id}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating supervisor: {e}")
    
    # Delete button
    st.divider()
    if st.button("🗑️ Delete This Supervisor", type="secondary", use_container_width=True):
        if st.session_state.get('confirm_delete') != selected_id:
            st.session_state['confirm_delete'] = selected_id
            st.warning("Click again to confirm deletion")
        else:
            try:
                conn, cursor = get_cursor()
                cursor.execute("DELETE FROM supervisors WHERE id = ?", (selected_id,))
                conn.commit()
                st.success(f"✓ Successfully deleted supervisor {selected_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting supervisor: {e}")
    
    # Display read-only fields
    st.divider()
    st.subheader("Read-only Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text(f"ID: {supervisor.get('id')}")
        st.text(f"Canonical ID: {supervisor.get('canonical_id', 'N/A')[:30]}...")
    with col2:
        st.text(f"Created: {supervisor.get('created_at', 'N/A')}")
        st.text(f"Last Seen: {supervisor.get('last_seen_at', 'N/A')}")
    with col3:
        st.text(f"Last Verified: {supervisor.get('last_verified_at', 'N/A') or 'Never'}")
        st.text(f"Updated: {supervisor.get('updated_at', 'N/A')}")

else:
    st.info("No supervisors found matching your criteria.")

# Don't close connection - let Streamlit cache handle it

