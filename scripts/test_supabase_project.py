#!/usr/bin/env python3
"""Test Supabase project connection and provide diagnostic information."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 70)
    print("Supabase 项目连接诊断")
    print("=" * 70)
    print()
    
    # Check environment variables
    print("1. 检查环境变量配置...")
    db_type = os.getenv("DB_TYPE", "")
    db_host = os.getenv("DB_HOST", "")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_sslmode = os.getenv("DB_SSLMODE", "require")
    
    print(f"   DB_TYPE: {db_type if db_type else '❌ 未设置'}")
    print(f"   DB_HOST: {db_host if db_host else '❌ 未设置'}")
    print(f"   DB_PORT: {db_port}")
    print(f"   DB_NAME: {db_name}")
    print(f"   DB_USER: {db_user}")
    print(f"   DB_PASSWORD: {'✓ 已设置' if db_password else '❌ 未设置'}")
    print(f"   DB_SSLMODE: {db_sslmode}")
    print()
    
    if db_type != "postgresql":
        print("❌ 错误: DB_TYPE 不是 'postgresql'")
        print("   请在 .env 文件中设置: DB_TYPE=postgresql")
        return
    
    if not db_host:
        print("❌ 错误: DB_HOST 未设置")
        print("   请在 .env 文件中设置: DB_HOST=db.xxxxx.supabase.co")
        return
    
    if not db_password:
        print("❌ 错误: DB_PASSWORD 未设置")
        print("   请在 .env 文件中设置: DB_PASSWORD=your-password")
        return
    
    # Test DNS resolution
    print("2. 测试 DNS 解析...")
    import socket
    try:
        ip = socket.gethostbyname(db_host)
        print(f"   ✓ DNS 解析成功: {db_host} -> {ip}")
    except socket.gaierror as e:
        print(f"   ❌ DNS 解析失败: {e}")
        print()
        print("   可能的原因:")
        print("   1. Supabase 项目不存在或已被删除")
        print("   2. 项目还在创建中（Pending 状态）")
        print("   3. 项目被暂停")
        print("   4. 主机名不正确")
        print()
        print("   解决方案:")
        print("   1. 访问 https://supabase.com/dashboard 检查项目状态")
        print("   2. 如果项目不存在，创建新项目")
        print("   3. 如果项目存在，等待几分钟让 DNS 传播")
        print("   4. 验证主机名是否正确（在 Supabase Dashboard → Settings → Database）")
        return
    
    # Test PostgreSQL connection
    print()
    print("3. 测试 PostgreSQL 连接...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            sslmode=db_sslmode,
            connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✓ 连接成功！")
        print(f"   PostgreSQL 版本: {version[:60]}...")
        cursor.close()
        conn.close()
        print()
        print("✅ 所有检查通过！可以运行迁移脚本了。")
    except ImportError:
        print("   ❌ psycopg2 未安装")
        print("   安装命令: pip install psycopg2-binary")
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        print()
        print("   可能的原因:")
        print("   1. 密码不正确")
        print("   2. 网络连接问题")
        print("   3. 防火墙阻止连接")
        print("   4. Supabase 项目配置问题")
        print()
        print("   解决方案:")
        print("   1. 在 Supabase Dashboard → Settings → Database 重置密码")
        print("   2. 检查网络连接")
        print("   3. 验证所有连接参数是否正确")

if __name__ == "__main__":
    main()

