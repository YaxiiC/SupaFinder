# Supabase 连接问题排查指南

## 🔍 当前错误

```
could not translate host name "db.llvvfsoycpfwomhoryga.supabase.co" to address: 
nodename nor servname provided, or not known
```

这个错误表示 DNS 无法解析 Supabase 主机名。

## ✅ 解决方案

### 方案 1：检查 Supabase 项目状态（最重要）

1. **访问 Supabase Dashboard**：
   - 打开：https://supabase.com/dashboard
   - 登录你的账号

2. **检查项目状态**：
   - 找到项目 `llvvfsoycpfwomhoryga`（或你的项目名称）
   - 检查项目状态：
     - ✅ **Active** - 项目正常运行
     - ⏳ **Pending** - 项目还在创建中（等待 2-5 分钟）
     - ❌ **Paused** - 项目已暂停（需要恢复）
     - ❌ **Deleted** - 项目已删除（需要重新创建）

3. **如果项目不存在或已删除**：
   - 需要创建新项目
   - 参考 `CLOUD_DATABASE_SETUP.md` 中的步骤 1

### 方案 2：验证主机名是否正确

1. **在 Supabase Dashboard 中**：
   - 进入 **Settings** → **Database**
   - 找到 **Connection string** 部分
   - 查看实际的 **Host** 地址

2. **检查主机名格式**：
   - 正确格式：`db.xxxxx.supabase.co`
   - 你的主机名：`db.llvvfsoycpfwomhoryga.supabase.co`
   - 确认这个主机名与 Dashboard 中显示的一致

3. **如果主机名不同**：
   - 更新 `.env` 文件中的 `DB_HOST`
   - 或创建新的 `.env` 文件

### 方案 3：创建/更新 .env 文件

1. **检查 .env 文件是否存在**：
   ```bash
   ls -la .env
   ```

2. **如果不存在，创建 .env 文件**：
   ```bash
   cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder
   cat > .env << 'EOF'
   # Database Configuration
   DB_TYPE=postgresql
   DB_HOST=db.llvvfsoycpfwomhoryga.supabase.co
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=your-password-here
   DB_SSLMODE=require
   EOF
   ```

   **重要**：将 `your-password-here` 替换为你的实际 Supabase 数据库密码！

3. **如果已存在，检查配置**：
   ```bash
   cat .env | grep DB_
   ```

### 方案 4：测试网络连接

1. **测试 DNS 解析**：
   ```bash
   nslookup db.llvvfsoycpfwomhoryga.supabase.co
   ```

2. **如果 DNS 解析失败**：
   - 等待几分钟让 DNS 传播（新创建的项目可能需要时间）
   - 检查网络连接
   - 尝试使用不同的 DNS 服务器（如 8.8.8.8）

3. **测试网络连接**：
   ```bash
   ping -c 3 db.llvvfsoycpfwomhoryga.supabase.co
   ```

### 方案 5：验证 Supabase 项目配置

1. **在 Supabase Dashboard 中**：
   - 进入 **Settings** → **Database**
   - 找到 **Connection string** 部分
   - 复制 **URI** 格式的连接字符串

2. **验证连接字符串格式**：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.llvvfsoycpfwomhoryga.supabase.co:5432/postgres
   ```

3. **测试直接连接**（使用 psql，如果已安装）：
   ```bash
   psql "postgresql://postgres:YOUR-PASSWORD@db.llvvfsoycpfwomhoryga.supabase.co:5432/postgres?sslmode=require"
   ```

## 🔧 快速修复步骤

### 步骤 1：确认 Supabase 项目存在且为 Active

1. 访问：https://supabase.com/dashboard
2. 检查项目状态
3. 如果项目不存在，创建新项目

### 步骤 2：获取正确的连接信息

1. 在 Supabase Dashboard → Settings → Database
2. 复制以下信息：
   - Host
   - Port (通常是 5432)
   - Database (通常是 postgres)
   - User (通常是 postgres)
   - Password (你设置的密码)

### 步骤 3：创建/更新 .env 文件

```bash
cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder

# 创建 .env 文件（如果不存在）
cat > .env << 'EOF'
DB_TYPE=postgresql
DB_HOST=db.llvvfsoycpfwomhoryga.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=YOUR_ACTUAL_PASSWORD_HERE
DB_SSLMODE=require
EOF
```

**重要**：将 `YOUR_ACTUAL_PASSWORD_HERE` 替换为你的实际密码！

### 步骤 4：测试连接

```bash
source .venv/bin/activate
python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); print('✓ 连接成功！'); conn.close()"
```

### 步骤 5：如果连接成功，运行迁移

```bash
python scripts/migrate_to_supabase.py
```

## ⚠️ 常见问题

### Q1: 项目状态显示 "Pending"

**解决方法**：
- 等待 2-5 分钟让项目完全创建
- 刷新 Supabase Dashboard
- 等待状态变为 "Active"

### Q2: 项目状态显示 "Paused"

**解决方法**：
- 在 Supabase Dashboard 中恢复项目
- 或创建新项目

### Q3: 忘记密码

**解决方法**：
1. 在 Supabase Dashboard → Settings → Database
2. 点击 "Reset database password"
3. 设置新密码
4. 更新 `.env` 文件中的 `DB_PASSWORD`

### Q4: 主机名无法解析

**可能原因**：
1. 项目还未完全创建（等待几分钟）
2. 项目已被删除（需要重新创建）
3. 网络问题（检查网络连接）

**解决方法**：
1. 确认项目状态为 "Active"
2. 等待几分钟让 DNS 传播
3. 检查网络连接
4. 验证主机名是否正确

## 📝 验证清单

在运行迁移之前，确认：

- [ ] Supabase 项目状态为 **Active**
- [ ] 已获取正确的连接信息（Host, Port, Database, User, Password）
- [ ] `.env` 文件已创建并包含正确的配置
- [ ] 密码已正确设置（不是占位符）
- [ ] 可以成功连接到数据库（测试连接通过）
- [ ] `psycopg2-binary` 已安装

## 🆘 如果所有方法都失败

1. **创建新的 Supabase 项目**：
   - 访问：https://supabase.com
   - 创建新项目
   - 获取新的连接信息
   - 更新 `.env` 文件

2. **联系 Supabase 支持**：
   - 如果项目存在但无法连接
   - 检查 Supabase 状态页面：https://status.supabase.com

3. **使用临时解决方案**：
   - 暂时继续使用本地 SQLite
   - 稍后再迁移到云端

---

**最后更新**：2024

