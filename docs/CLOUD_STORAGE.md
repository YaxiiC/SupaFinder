# Cloud Storage Options for Database

As your database grows, here are several options to store it in the cloud:

## Option 1: Cloud File Sync (Easiest) ⭐ Recommended

Store the SQLite file in a cloud-synced folder (iCloud Drive, Dropbox, Google Drive, etc.)

### Setup:

1. **iCloud Drive** (macOS):
   ```bash
   # Move database to iCloud Drive
   mkdir -p ~/Library/Mobile\ Documents/com~apple~CloudDocs/SuperFinder
   mv cache.sqlite ~/Library/Mobile\ Documents/com~apple~CloudDocs/SuperFinder/
   ```

2. **Dropbox**:
   ```bash
   # Move database to Dropbox
   mkdir -p ~/Dropbox/SuperFinder
   mv cache.sqlite ~/Dropbox/SuperFinder/
   ```

3. **Update .env file**:
   ```env
   DB_TYPE=cloud_sqlite
   CLOUD_DB_PATH=/Users/yourname/Dropbox/SuperFinder/cache.sqlite
   # or
   CLOUD_DB_PATH=/Users/yourname/Library/Mobile Documents/com~apple~CloudDocs/SuperFinder/cache.sqlite
   ```

**Pros:**
- ✅ Easy setup
- ✅ Automatic sync
- ✅ Works with existing code
- ✅ Free (up to storage limits)

**Cons:**
- ⚠️ File conflicts if accessed from multiple devices simultaneously
- ⚠️ Sync delays

---

## Option 2: Remote PostgreSQL Database

Use a cloud PostgreSQL service (AWS RDS, Google Cloud SQL, Heroku Postgres, Supabase, etc.)

### Setup:

1. **Create a PostgreSQL database** on your preferred cloud provider:
   - [Supabase](https://supabase.com) - Free tier available
   - [Heroku Postgres](https://www.heroku.com/postgres) - Free tier available
   - [AWS RDS](https://aws.amazon.com/rds/)
   - [Google Cloud SQL](https://cloud.google.com/sql)

2. **Install PostgreSQL driver**:
   ```bash
   pip install psycopg2-binary
   ```

3. **Update .env file**:
   ```env
   DB_TYPE=postgresql
   DB_HOST=your-db-host.com
   DB_PORT=5432
   DB_NAME=superfinder
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

4. **Initialize database**:
   ```bash
   python -c "from app.db_cloud import init_db; init_db()"
   ```

**Pros:**
- ✅ Proper database with transactions
- ✅ Multiple users can access simultaneously
- ✅ Better for large datasets
- ✅ Automatic backups (on most providers)

**Cons:**
- ⚠️ Requires setup and configuration
- ⚠️ May have costs (though free tiers available)

---

## Option 3: Database Cleanup (Reduce Size)

Keep database local but regularly clean old cache data:

### Setup:

1. **Run cleanup script**:
   ```bash
   # Clean page cache older than 30 days, keep all supervisors
   python scripts/cleanup_old_cache.py --page-cache-days 30
   
   # More aggressive cleanup
   python scripts/cleanup_old_cache.py --page-cache-days 7 --extracted-days 30
   ```

2. **Schedule automatic cleanup** (cron job):
   ```bash
   # Add to crontab (runs weekly)
   0 2 * * 0 cd /path/to/SuperFinder && python scripts/cleanup_old_cache.py
   ```

**Pros:**
- ✅ Keeps database small
- ✅ No cloud setup needed
- ✅ Free

**Cons:**
- ⚠️ Loses old cache data (but supervisors are preserved)

---

## Option 4: Hybrid Approach

- Keep `supervisors` table in cloud (PostgreSQL)
- Keep `page_cache` and `extracted_profiles` local (SQLite)

This requires code modifications but gives you the best of both worlds.

---

## Recommended Setup

For most users, **Option 1 (Cloud File Sync)** is the easiest:

1. Move database to iCloud Drive or Dropbox
2. Update `.env` with `CLOUD_DB_PATH`
3. Run cleanup script monthly to keep size manageable

```bash
# Monthly cleanup (keep last 30 days of cache)
python scripts/cleanup_old_cache.py --page-cache-days 30
```

---

## Database Size Monitoring

Check database size:
```bash
ls -lh cache.sqlite
# or
python -c "from app.config import CACHE_DB; print(f'Size: {CACHE_DB.stat().st_size / (1024*1024):.2f} MB')"
```

Monitor growth over time to decide when to implement cloud storage.

