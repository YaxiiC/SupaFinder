# 修复 PostgreSQL 密码认证失败问题

## 🔍 当前错误

```
FATAL: password authentication failed for user "postgres"
```

## ✅ 解决方案

### 步骤 1：检查 Supabase Dashboard 中的密码

1. **访问 Supabase Dashboard**：
   - 打开：https://supabase.com/dashboard
   - 登录你的账号
   - 进入项目 `kcyfwlcatgtgzntiwmoo`

2. **查看数据库密码**：
   - 进入 **Settings** → **Database**
   - 找到 **Database password** 部分
   - 点击 **Reset database password**（如果需要）
   - 或查看当前密码（如果 Supabase 显示）

### 步骤 2：更新 .env 文件

1. **编辑 .env 文件**：
   ```bash
   nano .env
   # 或使用你喜欢的编辑器
   ```

2. **更新 DB_PASSWORD**：
   ```env
   DB_PASSWORD=your-actual-password-from-supabase
   ```

   **重要**：
   - 确保密码与 Supabase Dashboard 中的完全一致
   - 如果密码包含特殊字符，确保正确转义
   - 不要有多余的空格或换行符

3. **保存文件**

### 步骤 3：验证连接

```bash
source .venv/bin/activate
python scripts/test_supabase_project.py
```

如果看到 "✅ 所有检查通过！"，说明密码正确。

## ⚠️ 常见问题

### Q1: 密码包含特殊字符

如果密码包含特殊字符（如 `#`, `!`, `$` 等），在 .env 文件中：
- 通常不需要引号
- 但如果遇到问题，可以尝试用单引号或双引号包裹

### Q2: 密码末尾有多余字符

检查 .env 文件中的密码是否有：
- 多余的空格
- 换行符
- 隐藏字符

### Q3: 密码已更改但 .env 未更新

如果之前在 Supabase Dashboard 中重置了密码，需要更新 .env 文件。

## 🔧 快速修复

1. **在 Supabase Dashboard 重置密码**：
   - Settings → Database → Reset database password
   - 设置新密码（**保存好！**）

2. **更新 .env 文件**：
   ```bash
   # 编辑 .env 文件，更新 DB_PASSWORD
   DB_PASSWORD=your-new-password
   ```

3. **测试连接**：
   ```bash
   python scripts/test_supabase_project.py
   ```

## 📝 当前配置检查

你的当前配置：
- DB_HOST: `aws-1-eu-west-1.pooler.supabase.com` ✅
- DB_PORT: `6543` ✅
- DB_NAME: `postgres` ✅
- DB_USER: `postgres.kcyfwlcatgtgzntiwmoo` ✅
- DB_PASSWORD: 需要验证 ⚠️

**下一步**：检查 Supabase Dashboard 中的密码，确保与 .env 文件中的完全一致。

