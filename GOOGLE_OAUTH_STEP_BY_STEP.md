# Google OAuth 2.0 客户端创建详细步骤

## 前提条件

✅ 你已经启用了 Google+ API

## 详细步骤

### 步骤 1：配置 OAuth 同意屏幕

1. 打开 [Google Cloud Console](https://console.cloud.google.com/)
2. 确保你选择了正确的项目
3. 在左侧菜单中，点击 **"APIs & Services"** > **"OAuth consent screen"**

#### 如果是首次配置：

4. **选择用户类型**：
   - 选择 **"External"**（推荐用于测试和个人项目）
   - 点击 **"CREATE"**

5. **填写应用信息**：
   - **App name**: `SuperFinder`（或你喜欢的名称）
   - **User support email**: 选择你的邮箱（下拉菜单）
   - **App logo**: （可选）上传应用图标
   - **Application home page**: （可选）你的网站 URL
   - **Application privacy policy link**: （可选）
   - **Application terms of service link**: （可选）
   - **Authorized domains**: （可选）
   - **Developer contact information**: 输入你的邮箱
   - 点击 **"SAVE AND CONTINUE"**

6. **配置 Scopes**：
   - 点击 **"ADD OR REMOVE SCOPES"**
   - 在搜索框中输入 `userinfo`
   - 勾选以下 scope：
     - ✅ `.../auth/userinfo.email`
     - ✅ `.../auth/userinfo.profile`
     - ✅ `openid`
   - 点击 **"UPDATE"**
   - 点击 **"SAVE AND CONTINUE"**

7. **Test users**（如果选择了 External）：
   - 可以添加测试用户邮箱（可选）
   - 点击 **"SAVE AND CONTINUE"**

8. **Summary**：
   - 检查所有信息
   - 点击 **"BACK TO DASHBOARD"**

### 步骤 2：创建 OAuth 2.0 客户端

1. 在左侧菜单中，点击 **"APIs & Services"** > **"Credentials"**

2. 点击页面顶部的 **"+ CREATE CREDENTIALS"** 按钮

3. 在下拉菜单中选择 **"OAuth client ID"**

4. 如果提示 "OAuth consent screen is not configured"：
   - 点击 **"CONFIGURE CONSENT SCREEN"**
   - 按照上面的步骤 1 完成配置
   - 完成后返回 "Credentials" 页面

5. **选择应用类型**：
   - 在 "Application type" 中选择 **"Web application"**

6. **填写客户端信息**：
   - **Name**: `SuperFinder Web Client`（或你喜欢的名称）

7. **Authorized JavaScript origins**（可选，但推荐）：
   - 点击 **"+ ADD URI"**
   - 添加以下 URI（根据你的环境选择）：
     - 本地开发：`http://localhost:8501`
     - Streamlit Cloud：`https://your-app-name.streamlit.app`
   - **注意**：不要包含末尾的 `/`

8. **Authorized redirect URIs**（重要！必须添加）：
   - 点击 **"+ ADD URI"**
   - 添加以下 URI（根据你的环境选择）：
     - 本地开发：`http://localhost:8501/`
     - Streamlit Cloud：`https://your-app-name.streamlit.app/`
   - **重要**：
     - URI 必须以 `/` 结尾
     - 确保 URI 完全匹配你的应用 URL
     - 如果使用 Streamlit Cloud，替换 `your-app-name` 为你的实际应用名称

9. 点击 **"CREATE"** 按钮

10. **保存凭据**：
    - 系统会显示一个弹窗，包含：
      - **Your Client ID**（例如：`123456789-abcdefghijklmnop.apps.googleusercontent.com`）
      - **Your Client Secret**（例如：`GOCSPX-abcdefghijklmnopqrstuvwxyz`）
    - **立即复制这两个值！**
    - **重要**：Client Secret 只显示一次，如果丢失需要重新创建客户端
    - 点击 **"OK"** 关闭弹窗

### 步骤 3：配置环境变量

将获取的凭据添加到你的配置中：

#### 本地开发（`.env` 文件）：

```bash
GOOGLE_OAUTH_CLIENT_ID=你的Client_ID
GOOGLE_OAUTH_CLIENT_SECRET=你的Client_Secret
APP_URL=http://localhost:8501
```

#### Streamlit Cloud（Streamlit Secrets）：

1. 在 Streamlit Cloud 中打开你的应用
2. 点击 **"Settings"** > **"Secrets"**
3. 添加以下内容：

```toml
GOOGLE_OAUTH_CLIENT_ID = "你的Client_ID"
GOOGLE_OAUTH_CLIENT_SECRET = "你的Client_Secret"
APP_URL = "https://your-app-name.streamlit.app"
```

### 步骤 4：验证配置

1. 重启你的 Streamlit 应用
2. 在登录页面，你应该能看到 **"🔵 Login with Google"** 按钮
3. 点击按钮，应该会重定向到 Google 登录页面
4. 完成登录后，应该会重定向回你的应用并自动登录

## 常见问题

### Q: 找不到 "OAuth client ID" 选项？

A: 确保你已经：
- 启用了 Google+ API
- 配置了 OAuth 同意屏幕

### Q: 重定向 URI 不匹配错误？

A: 检查：
- 重定向 URI 必须以 `/` 结尾
- URI 必须完全匹配（包括协议 `http://` 或 `https://`）
- 在 Google Cloud Console 中添加的 URI 必须与 `APP_URL` 匹配

### Q: Client Secret 丢失了怎么办？

A: 需要删除现有客户端并重新创建：
1. 在 "Credentials" 页面找到你的 OAuth 客户端
2. 点击右侧的垃圾桶图标删除
3. 重新创建客户端

### Q: 本地开发和 Streamlit Cloud 需要不同的配置吗？

A: 可以：
- 在 Google Cloud Console 中添加多个重定向 URI（本地和云端）
- 使用不同的环境变量配置（本地用 `.env`，云端用 Streamlit Secrets）

## 安全提示

1. **不要**将 Client ID 和 Client Secret 提交到 Git
2. **不要**在公开的地方分享 Client Secret
3. 使用 `.gitignore` 确保 `.env` 文件不会被提交
4. 在 Streamlit Cloud 中使用 Secrets 而不是硬编码

## 下一步

配置完成后，参考 `AUTH_SETUP.md` 了解如何使用认证系统。

