#!/usr/bin/env python3
"""Fix Dropbox laptop access issue - diagnose and repair Dropbox connection."""

import subprocess
import json
import os
from pathlib import Path
import time

print("=" * 70)
print("Dropbox 设备访问问题诊断和修复工具")
print("=" * 70)

def check_dropbox_process():
    """Check if Dropbox is running."""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    return "Dropbox.app" in result.stdout

def check_dropbox_folder():
    """Check if Dropbox folder exists and is accessible."""
    dropbox_path = Path.home() / "Dropbox"
    return dropbox_path.exists() and dropbox_path.is_dir()

def check_dropbox_account():
    """Check Dropbox account status."""
    info_path = Path.home() / "Library" / "Application Support" / "Dropbox" / "info.json"
    if info_path.exists():
        try:
            with open(info_path) as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"   ⚠ 无法读取账号信息: {e}")
            return None
    return None

def check_dropbox_menu_bar():
    """Provide instructions to check menu bar."""
    print("\n" + "-" * 70)
    print("步骤 1: 检查菜单栏 Dropbox 图标")
    print("-" * 70)
    print("请检查右上角菜单栏是否有 Dropbox 图标")
    print("如果没有图标，说明 Dropbox 未完全启动")
    print("\n点击菜单栏 Dropbox 图标，查看：")
    print("  - 是否显示已登录状态")
    print("  - 是否有错误提示")
    print("  - 账号信息是否正确")

def restart_dropbox():
    """Restart Dropbox application."""
    print("\n" + "-" * 70)
    print("步骤 2: 重启 Dropbox 客户端")
    print("-" * 70)
    print("正在重启 Dropbox...")
    
    # Kill Dropbox
    subprocess.run(["killall", "Dropbox"], capture_output=True)
    print("   ✓ 已停止 Dropbox")
    
    # Wait a bit
    time.sleep(2)
    
    # Start Dropbox
    subprocess.run(["open", "-a", "Dropbox"])
    print("   ✓ 已启动 Dropbox")
    print("\n请等待 10-15 秒让 Dropbox 完全启动...")
    time.sleep(3)

def check_finder_extension():
    """Provide instructions to check Finder extension."""
    print("\n" + "-" * 70)
    print("步骤 3: 检查 Finder 扩展")
    print("-" * 70)
    print("Dropbox 需要在 Finder 中启用扩展才能正常工作：")
    print("\n1. 打开 '系统设置' (System Settings)")
    print("2. 搜索 '扩展' 或 'Extensions'")
    print("3. 选择 'Finder 扩展' 或 'Finder Extensions'")
    print("4. 确保 'Dropbox' 已勾选启用")
    print("\n或者通过命令行检查：")
    print("   defaults read com.apple.finder 'FXEnableExtensionChangeWarning'")

def verify_dropbox_connection():
    """Verify Dropbox folder connection."""
    print("\n" + "-" * 70)
    print("步骤 4: 验证 Dropbox 连接")
    print("-" * 70)
    dropbox_path = Path.home() / "Dropbox"
    
    if not dropbox_path.exists():
        print("   ✗ Dropbox 文件夹不存在")
        print("   这可能意味着 Dropbox 未正确安装或配置")
        return False
    
    print(f"   ✓ Dropbox 文件夹存在: {dropbox_path}")
    
    # Check if it's a symlink (might indicate issue)
    if dropbox_path.is_symlink():
        print(f"   ⚠ 这是符号链接，链接到: {dropbox_path.readlink()}")
    
    # Check contents
    try:
        items = list(dropbox_path.iterdir())
        print(f"   ✓ 文件夹包含 {len(items)} 个项目")
    except Exception as e:
        print(f"   ✗ 无法读取文件夹内容: {e}")
        return False
    
    return True

def check_sync_status():
    """Check file sync status."""
    print("\n" + "-" * 70)
    print("步骤 5: 检查同步状态")
    print("-" * 70)
    superfinder_path = Path.home() / "Dropbox" / "SuperFinder"
    
    if superfinder_path.exists():
        print(f"   ✓ SuperFinder 文件夹存在")
        files = list(superfinder_path.glob("*.sqlite*"))
        for file in files:
            size = file.stat().st_size / (1024*1024)
            print(f"     - {file.name}: {size:.2f} MB")
    else:
        print(f"   ⚠ SuperFinder 文件夹不存在")

def provide_solutions():
    """Provide solutions for common issues."""
    print("\n" + "=" * 70)
    print("常见问题解决方案")
    print("=" * 70)
    
    print("\n问题 1: 其他设备无法访问 Dropbox")
    print("  可能原因:")
    print("    - Dropbox 账号未在所有设备上登录")
    print("    - 网络连接问题")
    print("    - Dropbox 客户端未在设备上运行")
    print("  解决方法:")
    print("    1. 在其他设备上打开 Dropbox 客户端")
    print("    2. 确保已登录同一账号")
    print("    3. 检查网络连接")
    
    print("\n问题 2: 笔记本电脑无法打开 Dropbox 文件夹")
    print("  可能原因:")
    print("    - Dropbox 客户端未启动")
    print("    - Dropbox 文件夹路径不正确")
    print("    - 权限问题")
    print("  解决方法:")
    print("    1. 确保 Dropbox 客户端正在运行")
    print("    2. 检查菜单栏是否有 Dropbox 图标")
    print("    3. 点击 Dropbox 图标 → Preferences → Sync")
    print("    4. 确认文件夹位置正确")
    
    print("\n问题 3: 文件未同步到云端")
    print("  可能原因:")
    print("    - 文件正在同步中（需要时间）")
    print("    - 网络速度慢")
    print("    - Dropbox 存储空间不足")
    print("  解决方法:")
    print("    1. 等待同步完成（查看菜单栏图标状态）")
    print("    2. 检查网络连接")
    print("    3. 访问 dropbox.com 检查存储空间")

# Main diagnostic flow
print("\n开始诊断...\n")

# Check 1: Dropbox process
print("1. 检查 Dropbox 客户端进程...")
if check_dropbox_process():
    print("   ✓ Dropbox 正在运行")
else:
    print("   ✗ Dropbox 未运行")
    print("   正在启动 Dropbox...")
    subprocess.run(["open", "-a", "Dropbox"])
    time.sleep(3)

# Check 2: Dropbox folder
print("\n2. 检查 Dropbox 文件夹...")
if check_dropbox_folder():
    print("   ✓ Dropbox 文件夹存在")
else:
    print("   ✗ Dropbox 文件夹不存在")
    print("   这可能是主要问题 - Dropbox 可能未正确配置")

# Check 3: Account status
print("\n3. 检查 Dropbox 账号状态...")
account_info = check_dropbox_account()
if account_info:
    print("   ✓ 找到账号配置")
    if "personal" in account_info:
        print("   ✓ 个人账号已配置")
    if "business" in account_info:
        print("   ✓ 商业账号已配置")
else:
    print("   ⚠ 无法确认账号状态")
    print("   可能需要重新登录 Dropbox")

# Check 4: Connection
verify_dropbox_connection()

# Check 5: Sync status
check_sync_status()

# Provide instructions
check_dropbox_menu_bar()

# Restart to fix issues
print("\n" + "-" * 70)
print("步骤 6: 自动修复 - 重启 Dropbox")
print("-" * 70)
print("尝试重启 Dropbox 以修复连接问题...")
restart_dropbox()

# Additional checks
check_finder_extension()

# Solutions
provide_solutions()

print("\n" + "=" * 70)
print("下一步操作建议")
print("=" * 70)
print("\n1. 检查菜单栏 Dropbox 图标状态")
print("2. 点击图标查看是否有错误消息")
print("3. 访问 https://www.dropbox.com 检查账号状态")
print("4. 确保其他设备上的 Dropbox 客户端也正在运行")
print("5. 如果问题持续，尝试完全退出并重新登录 Dropbox")
print("\n" + "=" * 70)

