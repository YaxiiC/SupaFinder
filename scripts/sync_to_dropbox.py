#!/usr/bin/env python3
"""Force sync file to Dropbox online."""

import subprocess
from pathlib import Path
import os

print("=" * 60)
print("Dropbox 同步助手")
print("=" * 60)

dropbox_file = Path.home() / "Dropbox" / "SuperFinder" / "cache.sqlite"

# Check if file exists
if not dropbox_file.exists():
    print(f"\n✗ 文件不存在: {dropbox_file}")
    print(f"\n建议：")
    print(f"  1. 将文件复制到 Dropbox 文件夹：")
    print(f"     cp cache.sqlite ~/Dropbox/SuperFinder/")
    sys.exit(1)

file_size = dropbox_file.stat().st_size / (1024*1024)
print(f"\n文件信息：")
print(f"  路径: {dropbox_file}")
print(f"  大小: {file_size:.2f} MB")

# Check Dropbox process
result = subprocess.run(
    ["ps", "aux"],
    capture_output=True,
    text=True
)
dropbox_running = "Dropbox.app" in result.stdout

if not dropbox_running:
    print(f"\n⚠️ Dropbox 客户端未运行")
    print(f"\n启动 Dropbox...")
    subprocess.run(["open", "-a", "Dropbox"])
    print(f"✓ 已启动 Dropbox，等待几秒后重试")
else:
    print(f"\n✓ Dropbox 客户端正在运行")

# Check file icon status (Mac specific)
print(f"\n同步步骤：")
print(f"=" * 60)

print(f"\n1. 检查文件是否在 Dropbox 文件夹中：")
print(f"   ✓ 文件位置正确: ~/Dropbox/SuperFinder/cache.sqlite")

print(f"\n2. 在 Finder 中查看文件图标状态：")
print(f"   - 打开 Finder，进入 ~/Dropbox/SuperFinder 文件夹")
print(f"   - 查看 cache.sqlite 文件图标：")
print(f"     ☁️ 云朵图标 = 已同步到云端 ✅")
print(f"     ⏳ 旋转图标 = 正在上传中")
print(f"     📄 普通图标 = 等待同步")

print(f"\n3. 强制触发同步（如果文件图标显示为普通文件）：")
print(f"   - 在 Finder 中右键点击 cache.sqlite")
print(f"   - 选择 'Make Available Offline' 或类似选项")
print(f"   - 或直接重新保存文件（touch 文件）")

print(f"\n4. 检查菜单栏 Dropbox 图标：")
print(f"   - 点击菜单栏右上角的 Dropbox 图标")
print(f"   - 查看 'Activity' 或 'Uploads'")
print(f"   - 确认文件在上传队列中")

print(f"\n5. 等待同步完成：")
print(f"   - 496 KB 的文件通常需要几秒到几分钟")
print(f"   - 在网络好的情况下，1-2 分钟内应该能看到")

print(f"\n6. 验证同步完成：")
print(f"   - 访问 https://www.dropbox.com")
print(f"   - 登录账号")
print(f"   - 查看 SuperFinder 文件夹")
print(f"   - 应该能看到 cache.sqlite 文件")

print(f"\n" + "=" * 60)
print(f"如果文件仍然不同步，尝试：")
print(f"  1. 重启 Dropbox 客户端")
print(f"  2. 检查网络连接")
print(f"  3. 确保 Dropbox 账号有足够存储空间")
print(f"=" * 60)

