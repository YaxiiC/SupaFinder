#!/usr/bin/env python3
"""Check Dropbox sync status."""

import os
from pathlib import Path

dropbox_path = Path.home() / "Dropbox" / "SuperFinder" / "cache.sqlite"

print("=" * 60)
print("Dropbox 同步状态检查")
print("=" * 60)

# Check if file exists
if not dropbox_path.exists():
    print(f"✗ 数据库文件不存在: {dropbox_path}")
    sys.exit(1)

# Get file info
file_size = dropbox_path.stat().st_size
file_size_gb = file_size / (1024 ** 3)

print(f"\n数据库文件:")
print(f"  路径: {dropbox_path}")
print(f"  大小: {file_size_gb:.2f} GB ({file_size:,} 字节)")
print(f"  修改时间: {dropbox_path.stat().st_mtime}")

# Check Dropbox process
print(f"\nDropbox 客户端状态:")
import subprocess
result = subprocess.run(
    ["ps", "aux"],
    capture_output=True,
    text=True
)
if "Dropbox.app" in result.stdout:
    print("  ✓ Dropbox 客户端正在运行")
else:
    print("  ✗ Dropbox 客户端未运行")

# Instructions
print(f"\n" + "=" * 60)
print("如何验证文件已同步到云端：")
print("=" * 60)
print("\n1. 访问 Dropbox 网站:")
print("   https://www.dropbox.com")
print("\n2. 登录你的 Dropbox 账号")
print("\n3. 在文件列表中查找 'SuperFinder' 文件夹")
print("\n4. 进入文件夹，应该能看到 'cache.sqlite' 文件")
print(f"   文件大小: {file_size_gb:.2f} GB")
print("\n5. 查看同步状态:")
print("   - 在 Finder 中，如果 Dropbox 文件夹图标上有云朵 ✅ = 已同步")
print("   - 如果显示同步中 ⏳ = 正在上传（2.8GB 可能需要一些时间）")
print("\n6. 在 Dropbox 客户端菜单栏图标中:")
print("   - 点击图标查看上传进度")
print("   - 绿色对勾 ✅ = 同步完成")
print("   - 同步图标 ⏳ = 正在同步")

print(f"\n" + "=" * 60)
print("当前配置：")
print("=" * 60)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if 'DB_TYPE' in line or 'CLOUD_DB_PATH' in line:
                print(f"  {line.strip()}")
else:
    print("  无法读取 .env 文件")

print("\n" + "=" * 60)

