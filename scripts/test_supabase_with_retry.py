#!/usr/bin/env python3
"""Test Supabase connection with retry and detailed diagnostics."""

import sys
import time
import socket
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

hostname = os.getenv('DB_HOST')
port = int(os.getenv('DB_PORT', '5432'))
database = os.getenv('DB_NAME', 'postgres')
user = os.getenv('DB_USER', 'postgres')
password = os.getenv('DB_PASSWORD')

print("=" * 60)
print("Supabase 连接测试（带重试）")
print("=" * 60)
print(f"主机名: {hostname}")
print(f"端口: {port}")
print(f"数据库: {database}")
print(f"用户: {user}")
print("=" * 60)

max_attempts = 5
wait_seconds = 30

for attempt in range(1, max_attempts + 1):
    print(f"\n尝试 {attempt}/{max_attempts}...")
    
    # Step 1: Test DNS resolution
    print(f"  [1/2] 测试 DNS 解析...")
    try:
        # Try different methods
        ip = None
        try:
            ip = socket.gethostbyname(hostname)
            print(f"        ✓ DNS 解析成功: {hostname} -> {ip}")
        except:
            # Try getaddrinfo
            try:
                addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
                if addr_info:
                    ip = addr_info[0][4][0]
                    print(f"        ✓ 使用 getaddrinfo 解析成功: {hostname} -> {ip}")
            except:
                pass
        
        if not ip:
            raise Exception("DNS 解析失败")
            
    except Exception as e:
        print(f"        ✗ DNS 解析失败: {e}")
        print(f"        ⚠ 这可能是暂时的，DNS 记录可能需要时间传播")
        
        if attempt < max_attempts:
            print(f"        ⏳ 等待 {wait_seconds} 秒后重试...")
            time.sleep(wait_seconds)
            continue
        else:
            print(f"\n{'=' * 60}")
            print("✗ 经过 {max_attempts} 次尝试，DNS 仍然无法解析")
            print(f"{'=' * 60}")
            print("\n建议：")
            print("1. 手动清理 DNS 缓存（需要管理员权限）：")
            print("   sudo dscacheutil -flushcache")
            print("   sudo killall -HUP mDNSResponder")
            print("\n2. 检查 Supabase 控制台中的实际主机名：")
            print("   Settings > Database > Connection string")
            print("   确认主机名是否与代码中的相同")
            print("\n3. 尝试使用不同的网络环境（比如手机热点）")
            print("\n4. 等待更长时间让 DNS 传播（可能需要几分钟到几小时）")
            sys.exit(1)
    
    # Step 2: Test database connection
    print(f"  [2/2] 测试数据库连接...")
    try:
        conn = psycopg2.connect(
            host=hostname,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode='require',
            connect_timeout=10
        )
        print(f"        ✓ 数据库连接成功！")
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"        ✓ PostgreSQL 版本: {version[0][:60]}...")
        
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        table_count = cursor.fetchone()[0]
        print(f"        ✓ 当前有 {table_count} 个表")
        
        conn.close()
        
        print(f"\n{'=' * 60}")
        print("✓ 数据库连接成功！")
        print(f"{'=' * 60}")
        print("\n下一步：")
        print("1. 初始化数据库表结构：")
        print("   python -c \"from app.db_cloud import init_db; init_db(); print('✓ 完成！')\"")
        print("\n2. 迁移数据（从 Dropbox SQLite 到 PostgreSQL）：")
        print("   python scripts/migrate_to_supabase.py")
        sys.exit(0)
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "could not translate host name" in error_msg:
            print(f"        ✗ DNS 解析失败")
        elif "timeout" in error_msg.lower():
            print(f"        ✗ 连接超时")
        elif "password authentication failed" in error_msg.lower():
            print(f"        ✗ 密码认证失败 - 请检查密码是否正确")
            sys.exit(1)
        else:
            print(f"        ✗ 连接失败: {error_msg[:100]}")
        
        if attempt < max_attempts:
            print(f"        ⏳ 等待 {wait_seconds} 秒后重试...")
            time.sleep(wait_seconds)
        else:
            print(f"\n{'=' * 60}")
            print("✗ 经过 {max_attempts} 次尝试，仍然无法连接")
            print(f"{'=' * 60}")
            sys.exit(1)
    except Exception as e:
        print(f"        ✗ 错误: {e}")
        if attempt < max_attempts:
            print(f"        ⏳ 等待 {wait_seconds} 秒后重试...")
            time.sleep(wait_seconds)
        else:
            sys.exit(1)

