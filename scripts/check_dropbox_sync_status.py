#!/usr/bin/env python3
"""Check Dropbox sync status."""

import subprocess
from pathlib import Path

print("=" * 60)
print("Dropbox 同步状态检查")
print("=" * 60)

# Check Dropbox process
result = subprocess.run(
    ["ps", "aux"],
    capture_output=True,
    text=True
)
dropbox_running = "Dropbox.app" in result.stdout
print(f"\n1. Dropbox 客户端状态:")
if dropbox_running:
    print(f"   ✓ Dropbox 客户端正在运行")
else:
    print(f"   ✗ Dropbox 客户端未运行")

# Check files
dropbox_path = Path.home() / "Dropbox" / "SuperFinder"
if dropbox_path.exists():
    print(f"\n2. Dropbox 文件夹中的文件:")
    files = list(dropbox_path.glob("*.sqlite*"))
    for file in files:
        size = file.stat().st_size / (1024*1024)
        if size > 1000:
            size_str = f"{size/1024:.2f} GB"
        else:
            size_str = f"{size:.2f} MB"
        print(f"   - {file.name}: {size_str}")
else:
    print(f"\n2. Dropbox SuperFinder 文件夹不存在")

print(f"\n3. 同步说明:")
print(f"   - 496 KB 的文件通常需要几秒到几分钟同步")
print(f"   - 2.8 GB 的文件可能需要几小时同步")
print(f"   - 检查菜单栏的 Dropbox 图标查看同步进度")

print(f"\n4. 如何查看同步状态:")
print(f"   a) 在 Finder 中查看文件图标:")
print(f"      - 云朵图标 ✅ = 已同步到云端")
print(f"      - 同步图标 ⏳ = 正在上传")
print(f"      - 无图标 = 等待同步")
print(f"   b) 点击菜单栏 Dropbox 图标查看上传进度")
print(f"   c) 在 dropbox.com 网页版查看文件是否出现")

print(f"\n" + "=" * 60)
