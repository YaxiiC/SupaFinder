# Streamlit Cloud Secrets 配置指南

## 📋 概述

本指南将帮助你配置 Streamlit Cloud Secrets，使你的应用能够连接到 Supabase PostgreSQL 数据库。

## 🚀 快速设置步骤

### 步骤 1：访问 Streamlit Cloud Dashboard

1. 打开：https://share.streamlit.io/
2. 登录你的 Streamlit Cloud 账号
3. 找到你的应用（`supafinder` 或你的应用名称）
4. 点击应用进入详情页

### 步骤 2：打开 Secrets 编辑器

1. 在应用详情页，点击 **Settings**（设置）
2. 在左侧菜单中找到 **Secrets**（密钥）
3. 点击 **Secrets** 进入编辑器

### 步骤 3：复制配置内容

打开文件 `streamlit_secrets_config.toml`，复制**全部内容**。

或者直接复制以下配置：

```toml
# DeepSeek API 配置
DEEPSEEK_API_KEY = "sk-3fc21fc36478497dbeba2a32bcd0db92"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Google Custom Search Engine 配置
GOOGLE_CSE_KEY = "AIzaSyCxKnyNG3huXYeI0JHoshY58-KebNFVmO8"
GOOGLE_CSE_CX = "c08c809c24cc44f6e"

# 数据库配置 (Supabase Transaction Pooler)
DB_TYPE = "postgresql"
DB_HOST = "aws-1-eu-west-1.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.kcyfwlcatgtgzntiwmoo"
DB_PASSWORD = "8#PwbjKBhd!8Cek"
DB_SSLMODE = "require"

# 开发者邮箱配置
DEVELOPER_EMAILS = "chrissyinreallife2022@gmail.com"

# Google OAuth 配置
GOOGLE_OAUTH_CLIENT_ID = "your-google-oauth-client-id"
GOOGLE_OAUTH_CLIENT_SECRET = "your-google-oauth-client-secret"
APP_URL = "https://supafinder.streamlit.app"
```

### 步骤 4：粘贴到 Streamlit Secrets

1. 在 Streamlit Cloud Secrets 编辑器中
2. **删除**所有现有内容（如果有）
3. **粘贴**上面复制的配置
4. 点击 **Save**（保存）

### 步骤 5：验证配置

1. 保存后，Streamlit Cloud 会自动重新部署应用
2. 等待部署完成（通常 1-2 分钟）
3. 访问你的应用 URL
4. 测试数据库连接（运行一次搜索）

## ✅ 配置说明

### 数据库配置（重要）

```toml
DB_TYPE = "postgresql"
DB_HOST = "aws-1-eu-west-1.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.kcyfwlcatgtgzntiwmoo"
DB_PASSWORD = "8#PwbjKBhd!8Cek"
DB_SSLMODE = "require"
```

**关键点**：
- ✅ 使用 **Transaction Pooler**（`aws-1-eu-west-1.pooler.supabase.com`）
- ✅ Port 是 **6543**（不是 5432）
- ✅ User 包含项目 ID（`postgres.kcyfwlcatgtgzntiwmoo`）
- ✅ SSL 模式为 `require`

### API 配置

- **DeepSeek API**：用于 LLM 功能
- **Google CSE**：用于搜索功能

### OAuth 配置

- **Google OAuth**：用于用户登录（当前已禁用，但配置保留）

## 🔍 验证配置是否生效

### 方法 1：检查应用日志

1. 在 Streamlit Cloud Dashboard → 你的应用
2. 点击 **Logs**（日志）
3. 查看是否有数据库连接错误

### 方法 2：测试应用功能

1. 访问你的应用
2. 登录账号
3. 运行一次搜索
4. 如果搜索成功，说明数据库连接正常

### 方法 3：检查数据库连接

在应用代码中添加测试（临时）：

```python
try:
    from app.db_cloud import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM supervisors")
    count = cursor.fetchone()[0]
    st.success(f"✓ 数据库连接成功！找到 {count} 条记录")
    conn.close()
except Exception as e:
    st.error(f"✗ 数据库连接失败: {e}")
```

## ⚠️ 常见问题

### Q1: 保存后应用无法启动

**可能原因**：
- Secrets 格式错误（TOML 语法错误）
- 缺少必需的配置项

**解决方法**：
1. 检查 TOML 语法（确保引号匹配）
2. 确认所有必需的配置项都已设置
3. 查看应用日志获取详细错误信息

### Q2: 数据库连接失败

**可能原因**：
- `DB_PASSWORD` 不正确
- `DB_HOST` 或 `DB_USER` 错误
- 网络问题

**解决方法**：
1. 验证 Supabase Dashboard 中的连接信息
2. 确认密码正确
3. 检查 Streamlit Cloud 日志

### Q3: 应用可以启动但搜索失败

**可能原因**：
- 数据库表未初始化
- 数据未迁移

**解决方法**：
1. 确认数据已迁移到 Supabase（已完成 ✅）
2. 检查数据库表是否存在

## 📝 安全检查清单

- [ ] Secrets 文件已保存到本地（`streamlit_secrets_config.toml`）
- [ ] 配置已复制到 Streamlit Cloud
- [ ] 所有配置项都已正确设置
- [ ] 密码已正确输入（不是占位符）
- [ ] 应用已重新部署
- [ ] 数据库连接测试通过

## 🔒 安全提示

1. **不要将 Secrets 提交到 Git**：
   - `streamlit_secrets_config.toml` 已在 `.gitignore` 中
   - 不要将密码分享给他人

2. **定期更新密码**：
   - 如果密码泄露，立即在 Supabase Dashboard 重置
   - 更新 Streamlit Secrets 中的密码

3. **使用环境变量**：
   - 本地开发使用 `.env` 文件
   - 生产环境使用 Streamlit Secrets

## 📚 相关文档

- `CLOUD_DATABASE_SETUP.md` - 云端数据库设置指南
- `UPDATE_POOLER_CONFIG.md` - Transaction Pooler 配置说明
- `streamlit_secrets_config.toml` - Secrets 配置文件

---

**完成配置后，你的应用就可以使用云端数据库了！** 🎉

