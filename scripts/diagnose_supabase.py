#!/usr/bin/env python3
"""Diagnose Supabase connection issues."""

import socket
import subprocess
import sys

hostname = "db.llvvfsoycpfwomhoryga.supabase.co"
project_ref = "llvvfsoycpfwomhoryga"

print("=" * 60)
print("Supabase 连接诊断")
print("=" * 60)

# Test 1: DNS lookup
print("\n1. DNS 解析测试...")
try:
    import socket
    ip = socket.gethostbyname(hostname)
    print(f"   ✓ 主机名解析成功: {hostname} -> {ip}")
except socket.gaierror as e:
    print(f"   ✗ DNS 解析失败: {e}")
    print(f"   ⚠ 可能原因：")
    print(f"      - Supabase 项目还在初始化中")
    print(f"      - DNS 记录还没有创建")
    print(f"      - 主机名格式不正确")

# Test 2: Try alternative hostname formats
print("\n2. 尝试不同的主机名格式...")
alternative_hostnames = [
    f"db.{project_ref}.supabase.co",
    f"db-{project_ref}.supabase.co",
    f"{project_ref}.supabase.co",
]

for alt_host in alternative_hostnames:
    try:
        ip = socket.gethostbyname(alt_host)
        print(f"   ✓ {alt_host} -> {ip}")
    except:
        print(f"   ✗ {alt_host} - 无法解析")

# Test 3: Network connectivity
print("\n3. 网络连接测试...")
try:
    result = subprocess.run(
        ["ping", "-c", "2", "supabase.com"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print("   ✓ 可以访问 supabase.com")
    else:
        print("   ⚠ 无法访问 supabase.com")
except:
    print("   ⚠ ping 命令失败")

# Test 4: Check if project URL is accessible
print("\n4. 检查项目 URL...")
try:
    import urllib.request
    url = f"https://{project_ref}.supabase.co"
    response = urllib.request.urlopen(url, timeout=5)
    print(f"   ✓ 项目 URL 可访问: {url}")
except Exception as e:
    print(f"   ✗ 项目 URL 不可访问: {e}")
    print(f"   ⚠ 项目可能还在初始化中")

# Test 5: Direct connection test (if DNS works)
print("\n5. 直接连接测试...")
if 'ip' in locals() and 'socket' in sys.modules:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, 5432))
        sock.close()
        if result == 0:
            print(f"   ✓ 端口 5432 可访问")
        else:
            print(f"   ✗ 端口 5432 不可访问 (错误代码: {result})")
    except Exception as e:
        print(f"   ✗ 连接测试失败: {e}")

print("\n" + "=" * 60)
print("建议：")
print("1. 确认 Supabase 项目状态为 'Active'（不是 'Pending'）")
print("2. 等待几分钟让 DNS 记录创建和传播")
print("3. 在 Supabase 控制台的 Settings > Database 中确认主机名")
print("4. 如果仍然无法解析，尝试使用不同的网络环境")
print("=" * 60)

