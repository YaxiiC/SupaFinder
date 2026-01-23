#!/usr/bin/env python3
"""Test Supabase password connection with different password variations."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def test_connection(password):
    """Test connection with given password."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", ""),
            port=os.getenv("DB_PORT", "6543"),
            database=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", ""),
            password=password,
            sslmode=os.getenv("DB_SSLMODE", "require"),
            connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return True, version
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("测试 Supabase 密码连接")
    print("=" * 70)
    print()
    
    # Get current password from .env
    current_password = os.getenv("DB_PASSWORD", "")
    print(f"当前 .env 中的密码长度: {len(current_password)}")
    print(f"密码（repr）: {repr(current_password)}")
    print()
    
    # Test current password
    print("测试当前密码...")
    success, result = test_connection(current_password)
    if success:
        print(f"✅ 连接成功！")
        print(f"PostgreSQL 版本: {result[:60]}...")
    else:
        print(f"❌ 连接失败: {result}")
        print()
        print("可能的原因:")
        print("1. 密码不正确")
        print("2. 密码在 .env 文件中有多余字符（空格、换行符等）")
        print("3. Supabase Dashboard 中的密码已更改")
        print()
        print("解决方案:")
        print("1. 访问 Supabase Dashboard → Settings → Database")
        print("2. 查看或重置数据库密码")
        print("3. 更新 .env 文件中的 DB_PASSWORD")
        print("4. 确保密码没有多余的空格或换行符")
    
    # Test password variations (if current fails)
    if not success:
        print()
        print("尝试密码变体...")
        
        # Remove trailing whitespace
        password_variants = [
            current_password.strip(),
            current_password.rstrip(),
            current_password.lstrip(),
        ]
        
        # Remove trailing 's' if present (might be typo)
        if current_password.endswith('s'):
            password_variants.append(current_password[:-1])
        
        for i, variant in enumerate(set(password_variants), 1):
            if variant == current_password:
                continue
            print(f"\n测试变体 {i}: {repr(variant)}")
            success, result = test_connection(variant)
            if success:
                print(f"✅ 变体 {i} 连接成功！")
                print(f"请更新 .env 文件中的 DB_PASSWORD 为: {variant}")
                return
            else:
                print(f"❌ 变体 {i} 失败")

if __name__ == "__main__":
    main()

