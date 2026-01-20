#!/usr/bin/env python3
"""帮助脚本：生成 Streamlit Secrets 配置模板。

这个脚本会读取你的 .env 文件，生成一个 Streamlit Secrets 配置模板，
方便你在 Streamlit Cloud 上配置 Secrets。

注意：这个脚本不会提交任何真实的 API keys 到 GitHub！
它只是帮你准备配置模板。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def main():
    print("=" * 70)
    print("Streamlit Secrets 配置模板生成器")
    print("=" * 70)
    print()
    
    # 加载 .env 文件
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print("❌ 未找到 .env 文件")
        print(f"   预期位置: {env_path}")
        print()
        print("请先创建 .env 文件，或复制 env.example:")
        print("   cp env.example .env")
        return
    
    print(f"✓ 找到 .env 文件: {env_path}")
    load_dotenv(env_path)
    
    # 检查必要的环境变量
    required_keys = {
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
        "GOOGLE_CSE_KEY": os.getenv("GOOGLE_CSE_KEY"),
        "GOOGLE_CSE_CX": os.getenv("GOOGLE_CSE_CX"),
    }
    
    print("\n检查环境变量:")
    print("-" * 70)
    
    missing_keys = []
    for key, value in required_keys.items():
        if value:
            # 只显示前几个字符，隐藏完整内容
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"  ✓ {key}: {display_value}")
        else:
            print(f"  ✗ {key}: 未设置")
            missing_keys.append(key)
    
    if missing_keys:
        print(f"\n⚠️  警告：以下必要的环境变量未设置: {', '.join(missing_keys)}")
        print("   请在 .env 文件中设置这些变量")
        return
    
    # 生成 Streamlit Secrets 配置模板
    print("\n" + "=" * 70)
    print("Streamlit Secrets 配置模板")
    print("=" * 70)
    print()
    print("请复制以下内容到 Streamlit Cloud 的 Secrets 编辑器:")
    print()
    print("-" * 70)
    print()
    
    # 基础 API 配置
    secrets_template = f"""# DeepSeek API 配置
DEEPSEEK_API_KEY = "{os.getenv('DEEPSEEK_API_KEY', '')}"
DEEPSEEK_BASE_URL = "{os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')}"
DEEPSEEK_MODEL = "{os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')}"

# Google Custom Search Engine 配置
GOOGLE_CSE_KEY = "{os.getenv('GOOGLE_CSE_KEY', '')}"
GOOGLE_CSE_CX = "{os.getenv('GOOGLE_CSE_CX', '')}"
"""
    
    # 可选的数据库配置
    db_type = os.getenv("DB_TYPE")
    if db_type == "postgresql":
        secrets_template += f"""
# 数据库配置（PostgreSQL/Supabase）
DB_TYPE = "postgresql"
DB_HOST = "{os.getenv('DB_HOST', '')}"
DB_PORT = "{os.getenv('DB_PORT', '5432')}"
DB_NAME = "{os.getenv('DB_NAME', 'postgres')}"
DB_USER = "{os.getenv('DB_USER', 'postgres')}"
DB_PASSWORD = "{os.getenv('DB_PASSWORD', '')}"
DB_SSLMODE = "{os.getenv('DB_SSLMODE', 'require')}"
"""
    
    print(secrets_template)
    print("-" * 70)
    print()
    
    # 保存到文件（可选）
    output_file = Path(__file__).parent.parent / "streamlit_secrets.toml.template"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(secrets_template)
    
    print(f"✓ 配置模板已保存到: {output_file}")
    print()
    print("⚠️  重要提示:")
    print("   1. 这个文件包含真实的 API keys，不要提交到 GitHub！")
    print("   2. 这个文件已经在 .gitignore 中，不会被意外提交")
    print("   3. 只用于帮助你准备 Streamlit Cloud 的 Secrets 配置")
    print("   4. 配置完成后，可以删除这个文件")
    print()
    print("下一步:")
    print("   1. 复制上面的配置内容")
    print("   2. 登录 Streamlit Cloud")
    print("   3. 部署应用时，在 'Advanced settings' → 'Secrets' 中粘贴")
    print("   4. 点击 'Deploy' 部署应用")

if __name__ == "__main__":
    main()

