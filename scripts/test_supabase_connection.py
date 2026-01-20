#!/usr/bin/env python3
"""Test Supabase PostgreSQL connection."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

print("测试 Supabase 数据库连接...")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_PORT: {os.getenv('DB_PORT')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_PASSWORD: {'*' * len(os.getenv('DB_PASSWORD', ''))}")

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'postgres'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )
    print("\n✓ 数据库连接成功！")
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL 版本: {version[0]}")
    
    conn.close()
    print("✓ 连接已关闭")
    
except psycopg2.OperationalError as e:
    print(f"\n✗ 连接失败: {e}")
    print("\n请检查：")
    print("1. Supabase 项目是否已完全创建（可能需要几分钟）")
    print("2. 数据库主机名是否正确（在 Supabase 控制台的 Settings > Database 中查看）")
    print("3. 数据库密码是否正确")
    print("4. 网络连接是否正常")
except Exception as e:
    print(f"\n✗ 错误: {e}")

