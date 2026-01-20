#!/usr/bin/env python3
"""Wait for Supabase database to be ready and test connection."""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import psycopg2
import socket

load_dotenv()

hostname = os.getenv('DB_HOST')
max_attempts = 20  # 尝试20次
wait_seconds = 30  # 每次等待30秒

print("=" * 60)
print("等待 Supabase 数据库准备就绪...")
print("=" * 60)
print(f"主机名: {hostname}")
print(f"最大尝试次数: {max_attempts}")
print(f"每次等待时间: {wait_seconds} 秒")
print("=" * 60)

for attempt in range(1, max_attempts + 1):
    print(f"\n尝试 {attempt}/{max_attempts}...")
    
    # Step 1: Test DNS resolution
    try:
        ip = socket.gethostbyname(hostname)
        print(f"   ✓ DNS 解析成功: {hostname} -> {ip}")
    except socket.gaierror as e:
        print(f"   ✗ DNS 解析失败: {e}")
        print(f"   ⏳ 等待 {wait_seconds} 秒后重试...")
        time.sleep(wait_seconds)
        continue
    
    # Step 2: Test database connection
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            connect_timeout=10
        )
        print(f"   ✓ 数据库连接成功！")
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"   ✓ PostgreSQL 版本: {version[0][:50]}...")
        
        conn.close()
        print("\n" + "=" * 60)
        print("✓ 数据库已准备就绪！")
        print("=" * 60)
        sys.exit(0)
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "could not translate host name" in error_msg:
            print(f"   ✗ DNS 解析失败，等待 {wait_seconds} 秒后重试...")
        elif "timeout" in error_msg.lower():
            print(f"   ✗ 连接超时，等待 {wait_seconds} 秒后重试...")
        else:
            print(f"   ✗ 连接失败: {error_msg}")
            print(f"   ⏳ 等待 {wait_seconds} 秒后重试...")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
        print(f"   ⏳ 等待 {wait_seconds} 秒后重试...")
    
    if attempt < max_attempts:
        time.sleep(wait_seconds)

print("\n" + "=" * 60)
print("✗ 在 {max_attempts} 次尝试后仍然无法连接")
print("=" * 60)
print("\n建议：")
print("1. 在 Supabase 控制台确认项目状态为 'Active'")
print("2. 在 Settings > Database 中确认数据库已创建")
print("3. 检查数据库主机名是否正确")
print("4. 等待更长时间后手动重试")
print("=" * 60)
sys.exit(1)

