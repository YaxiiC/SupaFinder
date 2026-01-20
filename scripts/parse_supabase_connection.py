#!/usr/bin/env python3
"""Parse Supabase connection string and update .env file."""

import sys
import re
from pathlib import Path

def parse_connection_string(conn_string):
    """Parse PostgreSQL connection string."""
    # Format: postgresql://user:password@host:port/database
    pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
    match = re.match(pattern, conn_string)
    
    if match:
        user, password, host, port, database = match.groups()
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'database': database
        }
    return None

if __name__ == "__main__":
    print("=" * 60)
    print("Supabase 连接字符串解析工具")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        conn_string = sys.argv[1]
    else:
        print("\n请提供 Supabase 连接字符串：")
        print("格式: postgresql://postgres:password@host:port/database")
        print("\n或者在 Supabase 控制台：")
        print("Settings > Database > Connection string > URI")
        print("\n输入连接字符串（或按 Ctrl+C 取消）:")
        conn_string = input().strip()
    
    # Parse connection string
    parsed = parse_connection_string(conn_string)
    
    if not parsed:
        print("\n✗ 无法解析连接字符串")
        print("请确保格式正确: postgresql://user:password@host:port/database")
        sys.exit(1)
    
    print("\n解析结果:")
    print(f"  主机名 (DB_HOST): {parsed['host']}")
    print(f"  端口 (DB_PORT): {parsed['port']}")
    print(f"  数据库名 (DB_NAME): {parsed['database']}")
    print(f"  用户名 (DB_USER): {parsed['user']}")
    print(f"  密码 (DB_PASSWORD): {'*' * len(parsed['password'])}")
    
    # Test DNS resolution
    print("\n测试 DNS 解析...")
    import socket
    try:
        ip = socket.gethostbyname(parsed['host'])
        print(f"   ✓ DNS 解析成功: {parsed['host']} -> {ip}")
    except Exception as e:
        print(f"   ✗ DNS 解析失败: {e}")
        print("   ⚠ 即使 DNS 解析失败，也请尝试连接（可能是 DNS 缓存问题）")
    
    # Generate .env configuration
    print("\n生成的 .env 配置:")
    print("-" * 60)
    print(f"DB_TYPE=postgresql")
    print(f"DB_HOST={parsed['host']}")
    print(f"DB_PORT={parsed['port']}")
    print(f"DB_NAME={parsed['database']}")
    print(f"DB_USER={parsed['user']}")
    print(f"DB_PASSWORD={parsed['password']}")
    print("-" * 60)
    
    # Ask if user wants to update .env
    response = input("\n是否更新 .env 文件？(y/n): ").strip().lower()
    if response == 'y':
        env_path = Path(__file__).parent.parent / ".env"
        
        # Read existing .env
        lines = []
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
        
        # Update database configuration
        updated = False
        new_lines = []
        skip_until_db_section = False
        
        for i, line in enumerate(lines):
            if line.startswith('DB_TYPE='):
                new_lines.append(f"DB_TYPE=postgresql\n")
                skip_until_db_section = True
            elif skip_until_db_section and line.startswith('DB_'):
                if line.startswith('DB_HOST='):
                    new_lines.append(f"DB_HOST={parsed['host']}\n")
                elif line.startswith('DB_PORT='):
                    new_lines.append(f"DB_PORT={parsed['port']}\n")
                elif line.startswith('DB_NAME='):
                    new_lines.append(f"DB_NAME={parsed['database']}\n")
                elif line.startswith('DB_USER='):
                    new_lines.append(f"DB_USER={parsed['user']}\n")
                elif line.startswith('DB_PASSWORD='):
                    new_lines.append(f"DB_PASSWORD={parsed['password']}\n")
                elif not any(line.startswith(f'DB_{key}=') for key in ['TYPE', 'HOST', 'PORT', 'NAME', 'USER', 'PASSWORD']):
                    skip_until_db_section = False
                    new_lines.append(line)
            else:
                if not skip_until_db_section:
                    new_lines.append(line)
                elif not line.startswith('DB_'):
                    skip_until_db_section = False
                    new_lines.append(line)
        
        # Write updated .env
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        
        print("\n✓ .env 文件已更新！")
    else:
        print("\n跳过更新 .env 文件")
    
    print("\n" + "=" * 60)
    print("下一步:")
    print("1. 手动清理 DNS 缓存（如果需要）:")
    print("   sudo dscacheutil -flushcache")
    print("   sudo killall -HUP mDNSResponder")
    print("\n2. 测试连接:")
    print("   python scripts/test_supabase_connection.py")
    print("=" * 60)

