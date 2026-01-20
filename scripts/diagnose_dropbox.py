#!/usr/bin/env python3
"""Diagnose Dropbox setup and sync status."""

import subprocess
from pathlib import Path
import os

print("=" * 60)
print("Dropbox 诊断工具")
print("=" * 60)

# Check 1: Dropbox process
print("\n1. 检查 Dropbox 客户端进程...")
result = subprocess.run(
    ["ps", "aux"],
    capture_output=True,
    text=True
)
dropbox_running = "Dropbox.app" in result.stdout
if dropbox_running:
    print("   ✓ Dropbox 客户端正在运行")
else:
    print("   ✗ Dropbox 客户端未运行")

# Check 2: Dropbox folder
print("\n2. 检查 Dropbox 文件夹...")
dropbox_path = Path.home() / "Dropbox"
if dropbox_path.exists():
    print(f"   ✓ Dropbox 文件夹存在: {dropbox_path}")
    # Check if it's a symlink
    if dropbox_path.is_symlink():
        print(f"   - 这是符号链接")
        print(f"   - 链接目标: {dropbox_path.readlink()}")
    else:
        print(f"   - 这是普通文件夹")
else:
    print(f"   ✗ Dropbox 文件夹不存在")

# Check 3: Check Dropbox folder contents
print("\n3. 检查 Dropbox 文件夹内容...")
if dropbox_path.exists():
    try:
        items = list(dropbox_path.iterdir())
        print(f"   - 找到 {len(items)} 个项目")
        for item in items[:5]:
            print(f"     * {item.name}")
    except Exception as e:
        print(f"   ✗ 无法读取文件夹内容: {e}")

# Check 4: SuperFinder folder
print("\n4. 检查 SuperFinder 文件夹...")
superfinder_path = dropbox_path / "SuperFinder"
if superfinder_path.exists():
    print(f"   ✓ SuperFinder 文件夹存在")
    files = list(superfinder_path.glob("*.sqlite*"))
    print(f"   - 找到 {len(files)} 个 SQLite 文件")
    for file in files:
        size = file.stat().st_size / (1024*1024)
        print(f"     * {file.name}: {size:.2f} MB")
else:
    print(f"   ✗ SuperFinder 文件夹不存在")

# Check 5: Dropbox account status
print("\n5. 检查 Dropbox 账号状态...")
# Try to find Dropbox preferences
prefs_path = Path.home() / "Library" / "Application Support" / "Dropbox"
if prefs_path.exists():
    print(f"   ✓ Dropbox 应用数据文件夹存在")
    # Check for account info
    account_json = prefs_path / "info.json"
    if account_json.exists():
        print(f"   ✓ 找到账号配置文件")
        try:
            import json
            with open(account_json) as f:
                info = json.load(f)
                if "personal" in info:
                    print(f"   ✓ 个人账号已配置")
                if "business" in info:
                    print(f"   ✓ 商业账号已配置")
        except:
            print(f"   ⚠ 无法读取账号信息")
else:
    print(f"   ⚠ Dropbox 应用数据文件夹不存在")

# Check 6: Dropbox sync status indicators
print("\n6. 文件图标状态说明...")
print("   - 如果没有看到任何图标，可能的原因：")
print("     a) Dropbox 客户端未正确启动")
print("     b) Dropbox 文件夹未正确连接到账号")
print("     c) 需要重新登录 Dropbox")
print("     d) Dropbox 客户端需要重启")

print("\n" + "=" * 60)
print("建议操作：")
print("=" * 60)
print("\n1. 检查菜单栏是否有 Dropbox 图标")
print("   - 如果没有，Dropbox 可能未启动")
print("   - 启动方法：打开应用程序中的 Dropbox")

print("\n2. 如果菜单栏有 Dropbox 图标，点击查看：")
print("   - 账号是否已登录")
print("   - 是否有错误提示")
print("   - 同步状态如何")

print("\n3. 尝试重启 Dropbox：")
print("   killall Dropbox")
print("   open -a Dropbox")

print("\n4. 如果仍然没有图标，可能需要：")
print("   - 重新登录 Dropbox 账号")
print("   - 检查 Dropbox 偏好设置")
print("   - 确认文件夹位置正确")

print("\n" + "=" * 60)

