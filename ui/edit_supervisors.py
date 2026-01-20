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

query += " ORDER BY last_seen_at DESC LIMIT 100"

conn, cursor = get_cursor()
cursor.execute(query, params)
rows = cursor.fetchall()

# Display supervisors
st.subheader(f"Supervisors ({len(rows)} shown)")

if rows:
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

