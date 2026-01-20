#!/usr/bin/env python3
"""Test different connection methods for Supabase."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

host = os.getenv('DB_HOST')
port = os.getenv('DB_PORT', '5432')
database = os.getenv('DB_NAME', 'postgres')
user = os.getenv('DB_USER', 'postgres')
password = os.getenv('DB_PASSWORD')

print("尝试不同的连接方式...")
print("=" * 60)

# Method 1: 使用连接字符串
print("\n方法 1: 使用完整的连接字符串...")
try:
    conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    conn = psycopg2.connect(conn_string)
    print("✓ 连接字符串方式成功！")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(f"  PostgreSQL 版本: {cursor.fetchone()[0][:50]}...")
    conn.close()
except Exception as e:
    print(f"✗ 连接字符串方式失败: {str(e)[:100]}")

# Method 2: 添加 SSL 参数
print("\n方法 2: 使用 SSL 连接 (sslmode=require)...")
try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        sslmode='require'
    )
    print("✓ SSL 连接成功！")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(f"  PostgreSQL 版本: {cursor.fetchone()[0][:50]}...")
    conn.close()
except Exception as e:
    print(f"✗ SSL 连接失败: {str(e)[:100]}")

# Method 3: 使用连接字符串 + SSL
print("\n方法 3: 连接字符串 + SSL...")
try:
    conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"
    conn = psycopg2.connect(conn_string)
    print("✓ 连接字符串 + SSL 成功！")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(f"  PostgreSQL 版本: {cursor.fetchone()[0][:50]}...")
    conn.close()
except Exception as e:
    print(f"✗ 连接字符串 + SSL 失败: {str(e)[:100]}")

# Method 4: 使用 prefer SSL
print("\n方法 4: 使用 SSL 连接 (sslmode=prefer)...")
try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        sslmode='prefer'
    )
    print("✓ SSL (prefer) 连接成功！")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(f"  PostgreSQL 版本: {cursor.fetchone()[0][:50]}...")
    conn.close()
except Exception as e:
    print(f"✗ SSL (prefer) 连接失败: {str(e)[:100]}")

print("\n" + "=" * 60)
print("如果所有方法都失败，请确认：")
print("1. Supabase 项目状态为 Active")
print("2. 数据库主机名正确")
print("3. DNS 记录已创建（可能需要等待更长时间）")
print("=" * 60)

