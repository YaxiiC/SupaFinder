# Editing Supervisors Database

The supervisor database is fully editable. You can edit records using either:

## Option 1: Streamlit Web UI (Recommended)

The easiest way to edit supervisors is using the web interface:

```bash
streamlit run ui/edit_supervisors.py
```

This will open a web browser where you can:
- Search and filter supervisors
- View all supervisor details
- Edit any field (name, email, institution, keywords, etc.)
- Delete supervisors
- See read-only metadata (ID, timestamps, canonical_id)

## Option 2: Command Line Interface

For quick edits from the terminal:

```bash
python scripts/edit_supervisors.py
```

This provides an interactive menu where you can:
1. List supervisors
2. View supervisor by ID
3. Edit supervisor field
4. Delete supervisor
5. Navigate through pages

## Database Location

The database is stored at: `cache.sqlite`

**Note**: This is a regular SQLite database file - it's fully editable and not a cache. You can also edit it directly using any SQLite tool like:
- DB Browser for SQLite (https://sqlitebrowser.org/)
- SQLite command line
- Any database management tool

## Important Notes

- When you edit name, email, institution, or profile_url, the `canonical_id` is automatically recalculated
- The `updated_at` timestamp is automatically set when you make changes
- Keywords and evidence snippets can be edited as comma-separated values
- All changes are saved immediately to the database

