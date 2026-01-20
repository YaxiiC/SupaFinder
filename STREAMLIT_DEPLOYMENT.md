# Streamlit Cloud 部署指南

## 📝 重要说明

**Streamlit Secrets 不能通过代码提交到 GitHub**，这是安全的设计！你需要**手动在 Streamlit Cloud 网页界面配置**。

## 🔐 配置 Streamlit Secrets

### 步骤 1：登录 Streamlit Cloud

1. 访问 https://share.streamlit.io/
2. 使用 GitHub 账号登录
3. 授权 Streamlit 访问你的仓库

### 步骤 2：部署应用

1. 点击 "New app" 或 "Deploy an app"
2. 配置应用：
   - **Repository**: `YaxiiC/SupaFinder`
   - **Branch**: `main`
   - **Main file path**: `ui/streamlit_app.py`
   - **App URL**: 自定义（例如 `supafinder`）

### 步骤 3：配置 Secrets（关键步骤！）

**在点击 "Deploy" 之前**，先点击 "Advanced settings" → "Secrets"。

在 Secrets 编辑器中，**复制并粘贴以下模板**，然后**替换**占位符为你的真实密钥：

```toml
# DeepSeek API 配置
DEEPSEEK_API_KEY = "sk-在这里填入你的真实DeepSeek_API_KEY"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Google Custom Search Engine 配置
GOOGLE_CSE_KEY = "在这里填入你的真实GOOGLE_CSE_KEY"
GOOGLE_CSE_CX = "在这里填入你的真实GOOGLE_CSE_CX"

# 数据库配置（如果使用 Supabase/PostgreSQL）
# 如果不使用云数据库，可以删除以下行
DB_TYPE = "postgresql"
DB_HOST = "你的数据库地址.supabase.co"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "你的数据库密码"
DB_SSLMODE = "require"
```

### 步骤 4：部署

配置完 Secrets 后，点击 "Deploy" 按钮。

### 步骤 5：验证

部署完成后，访问你的应用 URL，测试应用是否正常工作。

## 🔍 如何找到你的 API Keys

### DeepSeek API Key

1. 访问 https://platform.deepseek.com/api_keys
2. 登录你的账号
3. 创建新的 API Key 或使用现有的
4. 复制 API Key（格式：`sk-xxxxx`）

### Google CSE Key 和 CX

1. **Google CSE Key**:
   - 访问 https://console.cloud.google.com/apis/credentials
   - 创建或使用现有的 API Key
   - 复制 API Key

2. **Google CSE CX**:
   - 访问 https://programmablesearchengine.google.com/
   - 创建或使用现有的 Custom Search Engine
   - 在设置中找到 "Search engine ID"（就是 CX）

## ⚠️ 重要提示

1. **不要**在 GitHub 仓库中提交真实的 API Keys
2. **不要**在代码中硬编码 API Keys
3. Secrets 只能在 Streamlit Cloud 网页界面配置
4. Secrets 是加密存储的，只有你和应用可以访问
5. 如果 API Key 泄露，立即更换新的 Key

## 🔄 更新 Secrets

如果需要更新 Secrets：

1. 在 Streamlit Cloud 中打开你的应用
2. 点击右上角的 "⋮" (三个点) → "Settings"
3. 点击 "Secrets"
4. 编辑 Secrets 内容
5. 保存后，应用会自动重新部署

## 📊 Secrets 格式说明

- 使用 **TOML 格式**（不是 .env 格式）
- 字符串值需要用**双引号**包裹
- 每行一个配置项
- 可以用 `#` 添加注释

## ✅ 验证 Secrets 是否配置正确

如果 Secrets 配置正确，应用应该能够：
- ✅ 正常启动
- ✅ 调用 DeepSeek API（处理 CV 和关键词）
- ✅ 调用 Google CSE API（搜索导师信息）
- ✅ 连接数据库（如果配置了）

如果遇到错误，检查：
- Secrets 格式是否正确（TOML 格式）
- API Keys 是否有效
- 是否遗漏了必需的 Secrets

## 📚 更多信息

- [Streamlit Cloud 文档](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets 文档](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)

