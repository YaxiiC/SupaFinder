# 认证系统设置指南

## 概述

SuperFinder 现在支持两种登录方式：
1. **Google OAuth 登录**（推荐）- 一键登录，无需密码
2. **邮箱+密码登录** - 传统登录方式

## 功能特性

- ✅ Google OAuth 一键登录
- ✅ 邮箱+密码注册和登录
- ✅ 密码强度验证（至少8位，包含字母和数字）
- ✅ 向后兼容：现有用户（无密码）仍可登录
- ✅ 开发者模式：开发者账号无限制访问

## 设置步骤

### 1. Google OAuth 配置（可选）

如果你想要支持 Google 登录，需要配置 Google OAuth：

#### 步骤 1：创建 Google OAuth 客户端

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 Google+ API：
   - 导航到 "APIs & Services" > "Library"
   - 搜索 "Google+ API" 并启用 ✅（你已经完成）

4. **配置 OAuth 同意屏幕**（首次创建 OAuth 客户端时需要）：
   - 导航到 "APIs & Services" > "OAuth consent screen"
   - 选择用户类型：
     - **External**（推荐用于测试）- 任何 Google 账号都可以使用
     - **Internal**（仅限 Google Workspace 组织）
   - 填写应用信息：
     - **App name**: SuperFinder（或你喜欢的名称）
     - **User support email**: 你的邮箱
     - **Developer contact information**: 你的邮箱
   - 点击 "Save and Continue"
   - 在 "Scopes" 页面，点击 "Add or Remove Scopes"
     - 选择以下 scope：
       - `.../auth/userinfo.email`
       - `.../auth/userinfo.profile`
       - `openid`
   - 点击 "Save and Continue"
   - 在 "Test users" 页面（如果选择了 External），可以添加测试用户（可选）
   - 点击 "Save and Continue"
   - 在 "Summary" 页面，点击 "Back to Dashboard"

5. **创建 OAuth 2.0 客户端**：
   - 导航到 "APIs & Services" > "Credentials"
   - 点击页面顶部的 **"+ CREATE CREDENTIALS"** 按钮
   - 选择 **"OAuth client ID"**
   - 如果提示配置 OAuth 同意屏幕，按照上面的步骤 4 完成配置
   - 在 "Application type" 中选择 **"Web application"**
   - 填写信息：
     - **Name**: SuperFinder Web Client（或你喜欢的名称）
     - **Authorized JavaScript origins**（可选，但推荐）：
       - 本地开发：`http://localhost:8501`
       - Streamlit Cloud：`https://your-app.streamlit.app`
     - **Authorized redirect URIs**（重要！必须添加）：
       - 本地开发：`http://localhost:8501/`
       - Streamlit Cloud：`https://your-app.streamlit.app/`
       - **注意**：URI 必须以 `/` 结尾
   - 点击 **"CREATE"** 按钮
   - **重要**：系统会显示一个弹窗，包含：
     - **Your Client ID**（例如：`123456789-abcdefghijklmnop.apps.googleusercontent.com`）
     - **Your Client Secret**（例如：`GOCSPX-abcdefghijklmnopqrstuvwxyz`）
   - **立即复制并保存这两个值**（Client Secret 只显示一次！）
   - 如果丢失了 Client Secret，需要删除客户端并重新创建

#### 步骤 2：配置环境变量

在 `.env` 文件或 Streamlit Secrets 中添加：

```bash
GOOGLE_OAUTH_CLIENT_ID=your_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret_here
APP_URL=https://your-app.streamlit.app  # 你的 Streamlit 应用 URL
```

**注意**：如果不配置 Google OAuth，用户只能使用邮箱+密码登录。

### 2. 开发者模式配置

在 `.env` 文件或 Streamlit Secrets 中添加开发者邮箱：

```bash
DEVELOPER_EMAILS=chrissyinreallife2022@gmail.com
```

开发者账号将获得：
- ✅ 无限制搜索
- ✅ 无需订阅
- ✅ 自动跳过订阅检查

### 3. 数据库迁移

系统会自动在 `users` 表中添加 `password_hash` 字段。首次运行时，数据库会自动更新。

## 用户登录流程

### Google OAuth 登录

1. 用户点击 "Login with Google" 按钮
2. 重定向到 Google 登录页面
3. 用户授权后，自动返回应用并登录
4. 系统自动创建账号（如果不存在）

### 邮箱+密码登录

#### 新用户注册

1. 切换到 "Register" 标签
2. 输入邮箱和密码（至少8位，包含字母和数字）
3. 确认密码
4. 点击 "Register"
5. 系统自动创建账号并登录

#### 现有用户登录

1. 切换到 "Login" 标签
2. 输入邮箱和密码
3. 点击 "Login"

#### 现有用户（无密码）

- 如果用户之前没有设置密码，可以直接登录（无需密码）
- 系统会提示用户注册以设置密码

## 密码要求

- 至少 8 个字符
- 最多 128 个字符
- 至少包含一个字母
- 至少包含一个数字

## 安全说明

1. **密码加密**：使用 bcrypt 加密存储密码
2. **向后兼容**：现有用户（无密码）仍可登录
3. **开发者模式**：开发者账号不受密码限制

## 故障排查

### Google OAuth 不工作

1. 检查 `GOOGLE_OAUTH_CLIENT_ID` 和 `GOOGLE_OAUTH_CLIENT_SECRET` 是否正确配置
2. 检查 `APP_URL` 是否与 Streamlit 应用 URL 匹配
3. 检查 Google Cloud Console 中的重定向 URI 是否正确配置
4. 确保已启用 Google+ API

### 密码登录失败

1. 检查密码是否符合要求（至少8位，包含字母和数字）
2. 确保邮箱格式正确
3. 如果用户之前没有密码，可以尝试不输入密码直接登录

### 开发者模式不工作

1. 检查 `DEVELOPER_EMAILS` 环境变量是否正确配置
2. 确保邮箱地址完全匹配（大小写不敏感）
3. 重启 Streamlit 应用使配置生效

## 技术细节

### 密码加密

- 使用 `bcrypt` 库进行密码哈希
- 自动生成随机 salt
- 密码哈希存储在 `users.password_hash` 字段

### Google OAuth 流程

1. 用户点击登录按钮
2. 重定向到 Google 授权页面
3. Google 返回授权码
4. 应用使用授权码换取访问令牌
5. 使用访问令牌获取用户信息（邮箱、姓名等）
6. 使用邮箱创建/登录账号

### 数据库结构

```sql
ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT NULL;
```

## 更新日志

- **v1.0** (2024): 初始版本
  - 支持 Google OAuth 登录
  - 支持邮箱+密码登录
  - 向后兼容现有用户

