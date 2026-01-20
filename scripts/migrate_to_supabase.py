#!/usr/bin/env python3
"""Migrate data from Dropbox SQLite to Supabase PostgreSQL."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import json
from datetime import datetime
from app.db_cloud import get_db_connection, init_db
from app.config import CACHE_DB

# Dropbox database path
DROPBOX_DB_PATH = Path("/Users/chrissychen/Dropbox/SuperFinder/cache.sqlite")

def migrate_data():
    """Migrate data from SQLite to PostgreSQL."""
    
    print("=" * 60)
    print("迁移数据：从 Dropbox SQLite 到 Supabase PostgreSQL")
    print("=" * 60)
    
    # Step 1: Initialize PostgreSQL database
    print("\n1. 初始化 PostgreSQL 数据库表结构...")
    try:
        init_db()
        print("   ✓ 数据库表结构创建成功")
    except Exception as e:
        print(f"   ✗ 初始化失败: {e}")
        return False
    
    # Step 2: Connect to both databases
    print("\n2. 连接数据库...")
    try:
        if not DROPBOX_DB_PATH.exists():
            print(f"   ✗ SQLite 数据库不存在: {DROPBOX_DB_PATH}")
            return False
        
        sqlite_conn = sqlite3.connect(str(DROPBOX_DB_PATH))
        sqlite_cursor = sqlite_conn.cursor()
        print("   ✓ SQLite 数据库连接成功")
        
        pg_conn = get_db_connection()
        pg_cursor = pg_conn.cursor()
        print("   ✓ PostgreSQL 数据库连接成功")
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
        return False
    
    # Step 3: Migrate supervisors table
    print("\n3. 迁移 supervisors 表...")
    try:
        sqlite_cursor.execute("SELECT COUNT(*) FROM supervisors")
        count = sqlite_cursor.fetchone()[0]
        print(f"   找到 {count} 条 supervisors 记录")
        
        if count == 0:
            print("   ⚠ 没有数据需要迁移")
            sqlite_conn.close()
            pg_conn.close()
            return True
        
        sqlite_cursor.execute("SELECT * FROM supervisors")
        rows = sqlite_cursor.fetchall()
        
        # Get column names
        columns = [description[0] for description in sqlite_cursor.description]
        
        migrated = 0
        skipped = 0
        errors = 0
        
        for row in rows:
            try:
                # Create a dictionary from the row
                row_dict = dict(zip(columns, row))
                
                # Prepare INSERT statement with ON CONFLICT
                placeholders = ",".join([f"%s" for _ in columns])
                column_names = ",".join(columns)
                insert_sql = f"""
                    INSERT INTO supervisors ({column_names}) 
                    VALUES ({placeholders})
                    ON CONFLICT (canonical_id) DO NOTHING
                """
                
                pg_cursor.execute(insert_sql, row)
                
                if pg_cursor.rowcount > 0:
                    migrated += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"   ⚠ 迁移记录失败 (ID: {row_dict.get('id', 'unknown')}): {e}")
                errors += 1
        
        pg_conn.commit()
        print(f"   ✓ 迁移完成: {migrated} 条新记录, {skipped} 条已存在, {errors} 条错误")
        
    except Exception as e:
        print(f"   ✗ 迁移失败: {e}")
        sqlite_conn.close()
        pg_conn.close()
        return False
    
    # Step 4: Migrate users table (subscription system)
    print("\n4. 迁移 users 表...")
    try:
        sqlite_cursor.execute("SELECT COUNT(*) FROM users")
        count = sqlite_cursor.fetchone()[0]
        
        if count > 0:
            sqlite_cursor.execute("SELECT * FROM users")
            rows = sqlite_cursor.fetchall()
            columns = [description[0] for description in sqlite_cursor.description]
            
            migrated_users = 0
            for row in rows:
                try:
                    placeholders = ",".join([f"%s" for _ in columns])
                    column_names = ",".join(columns)
                    insert_sql = f"""
                        INSERT INTO users ({column_names}) 
                        VALUES ({placeholders})
                        ON CONFLICT (email) DO NOTHING
                    """
                    pg_cursor.execute(insert_sql, row)
                    if pg_cursor.rowcount > 0:
                        migrated_users += 1
                except:
                    pass
            
            pg_conn.commit()
            print(f"   ✓ 迁移了 {migrated_users} 条 users 记录")
        else:
            print("   ℹ 没有 users 数据需要迁移")
            
    except Exception as e:
        print(f"   ⚠ 迁移 users 表失败（可能是表不存在）: {e}")
    
    # Step 5: Migrate subscriptions table
    print("\n5. 迁移 subscriptions 表...")
    try:
        sqlite_cursor.execute("SELECT COUNT(*) FROM subscriptions")
        count = sqlite_cursor.fetchone()[0]
        
        if count > 0:
            sqlite_cursor.execute("SELECT * FROM subscriptions")
            rows = sqlite_cursor.fetchall()
            columns = [description[0] for description in sqlite_cursor.description]
            
            migrated_subs = 0
            for row in rows:
                try:
                    placeholders = ",".join([f"%s" for _ in columns])
                    column_names = ",".join(columns)
                    insert_sql = f"""
                        INSERT INTO subscriptions ({column_names}) 
                        VALUES ({placeholders})
                        ON CONFLICT (id) DO NOTHING
                    """
                    pg_cursor.execute(insert_sql, row)
                    if pg_cursor.rowcount > 0:
                        migrated_subs += 1
                except:
                    pass
            
            pg_conn.commit()
            print(f"   ✓ 迁移了 {migrated_subs} 条 subscriptions 记录")
        else:
            print("   ℹ 没有 subscriptions 数据需要迁移")
            
    except Exception as e:
        print(f"   ⚠ 迁移 subscriptions 表失败（可能是表不存在）: {e}")
    
    # Step 6: Verify migration
    print("\n6. 验证迁移结果...")
    try:
        pg_cursor.execute("SELECT COUNT(*) FROM supervisors")
        pg_count = pg_cursor.fetchone()[0]
        print(f"   PostgreSQL 中有 {pg_count} 条 supervisors 记录")
        
        sqlite_cursor.execute("SELECT COUNT(*) FROM supervisors")
        sqlite_count = sqlite_cursor.fetchone()[0]
        print(f"   SQLite 中有 {sqlite_count} 条 supervisors 记录")
        
        if pg_count > 0:
            print(f"   ✓ 数据已成功迁移到 PostgreSQL")
    except Exception as e:
        print(f"   ⚠ 验证失败: {e}")
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = migrate_data()
    sys.exit(0 if success else 1)

