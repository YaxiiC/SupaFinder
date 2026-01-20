#!/usr/bin/env python3
"""Try alternative DNS resolution methods."""

import socket
import sys

hostname = "db.llvvfsoycpfwomhoryga.supabase.co"

print("尝试不同的 DNS 解析方法...")
print("=" * 60)

# Method 1: Direct hostname lookup
print("\n方法 1: 标准 DNS 查询...")
try:
    ip = socket.gethostbyname(hostname)
    print(f"   ✓ 解析成功: {hostname} -> {ip}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# Method 2: Using getaddrinfo (more robust)
print("\n方法 2: 使用 getaddrinfo...")
try:
    addr_info = socket.getaddrinfo(hostname, 5432, socket.AF_UNSPEC, socket.SOCK_STREAM)
    print(f"   ✓ 找到 {len(addr_info)} 个地址:")
    for addr in addr_info:
        print(f"      - {addr[4]}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# Method 3: Try with Google DNS (8.8.8.8)
print("\n方法 3: 使用 Google DNS 查询...")
try:
    import subprocess
    result = subprocess.run(
        ["dig", "@8.8.8.8", hostname, "+short"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.stdout.strip():
        ips = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        print(f"   ✓ 解析成功: {hostname} -> {', '.join(ips)}")
    else:
        print(f"   ✗ DNS 记录不存在")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# Method 4: Try with Cloudflare DNS (1.1.1.1)
print("\n方法 4: 使用 Cloudflare DNS 查询...")
try:
    import subprocess
    result = subprocess.run(
        ["dig", "@1.1.1.1", hostname, "+short"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.stdout.strip():
        ips = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        print(f"   ✓ 解析成功: {hostname} -> {', '.join(ips)}")
    else:
        print(f"   ✗ DNS 记录不存在")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# Method 5: Try nslookup
print("\n方法 5: 使用 nslookup...")
try:
    import subprocess
    result = subprocess.run(
        ["nslookup", hostname],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(result.stdout)
except Exception as e:
    print(f"   ✗ 失败: {e}")

print("\n" + "=" * 60)
print("建议：")
print("1. 如果所有方法都失败，可能是 DNS 记录还没有创建")
print("2. 尝试使用不同的网络环境（比如手机热点）")
print("3. 等待几分钟后重试")
print("4. 检查 Supabase 控制台中的实际主机名是否不同")
print("=" * 60)

