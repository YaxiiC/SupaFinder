# 云端数据库设置指南 / Cloud Database Setup Guide

## 📋 概述 / Overview

本指南将帮助你：
1. 将数据库迁移到云端（推荐 Supabase PostgreSQL）
2. 配置自动清理功能在云端数据库上工作
3. 确保 Streamlit Cloud 可以访问数据库

This guide will help you:
1. Migrate database to cloud (recommended: Supabase PostgreSQL)
2. Configure automatic cleanup to work with cloud database
3. Ensure Streamlit Cloud can access the database

---

## ✅ 自动清理支持云端数据库

**好消息！** 自动清理功能已经支持 PostgreSQL（云端数据库）。

**Good news!** Automatic cleanup already supports PostgreSQL (cloud databases).

- ✅ 自动清理在 SQLite 和 PostgreSQL 上都能工作
- ✅ 每次批量更新（>= 10 个 profiles）时自动清理
- ✅ 删除 `page_cache` 条目以保持数据库轻量级
- ✅ 无需手动操作

---

## 🎯 方案选择 / Solution Options

### 方案 1：Supabase PostgreSQL（强烈推荐）⭐⭐⭐

**优点：**
- ✅ 专为在线应用设计
- ✅ Streamlit Cloud 可以直接连接
- ✅ 免费额度：500MB 数据库存储
- ✅ 自动备份
- ✅ 支持多用户同时访问
- ✅ 自动清理功能完全支持

**缺点：**
- ⚠️ 需要迁移数据（一次性操作）

### 方案 2：Dropbox/iCloud 同步（不推荐用于生产）

**优点：**
- ✅ 设置简单
- ✅ 自动同步

**缺点：**
- ❌ Streamlit Cloud 无法访问本地 Dropbox 路径
- ❌ 不适合多用户访问
- ❌ 文件冲突风险

---

## 🚀 Supabase PostgreSQL 设置步骤

### 步骤 1：创建 Supabase 项目

1. **访问 Supabase**：
   - 打开：https://supabase.com
   - 点击 "Sign Up" 注册账号（或 "Sign In" 登录）

2. **创建新项目**：
   - 点击 "New Project"
   - 填写项目信息：
     - **Name**: `supafinder`（或任何名称）
     - **Database Password**: 设置一个强密码（**保存好！**）
     - **Region**: 选择离你最近的区域（如 `Southeast Asia (Singapore)`）
   - 点击 "Create new project"
   - 等待项目创建完成（约 2-5 分钟）

### 步骤 2：获取数据库连接信息

1. **在 Supabase Dashboard 中**：
   - 进入 **Settings** → **Database**
   - 找到 **Connection string** 部分
   - 选择 **URI** 格式

2. **复制以下信息**：
   - **Host**: `db.xxxxx.supabase.co`
   - **Port**: `5432`
   - **Database**: `postgres`
   - **User**: `postgres`
   - **Password**: 你设置的密码

### 步骤 3：配置 Streamlit Secrets

1. **在 Streamlit Cloud Dashboard**：
   - 进入你的应用
   - 点击 **Settings** → **Secrets**
   - 添加以下配置：

```toml
# Database Configuration
DB_TYPE = "postgresql"
DB_HOST = "db.xxxxx.supabase.co"  # 替换为你的 Supabase Host
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "your-password-here"  # 替换为你的密码
DB_SSLMODE = "require"
```

2. **保存 Secrets**

### 步骤 4：本地测试连接（可选但推荐）

1. **安装 PostgreSQL 驱动**（如果还没有）：
   ```bash
   cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder
   source .venv/bin/activate
   pip install psycopg2-binary
   ```

2. **创建本地 `.env` 文件**（用于测试）：
   ```bash
   # 在项目根目录创建 .env 文件
   cat > .env << EOF
   DB_TYPE=postgresql
   DB_HOST=db.xxxxx.supabase.co
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=your-password-here
   DB_SSLMODE=require
   EOF
   ```

3. **测试连接**：
   ```bash
   python -c "from app.db_cloud import get_db_connection, init_db; init_db(); conn = get_db_connection(); print('✓ 连接成功！'); conn.close()"
   ```

   如果看到 `✓ 连接成功！`，继续下一步。

### 步骤 5：初始化数据库表结构

```bash
python -c "from app.db_cloud import init_db; init_db(); print('✓ 数据库表创建成功！')"
```

### 步骤 6：迁移数据（从本地 SQLite 到 Supabase）

1. **检查迁移脚本**：
   ```bash
   ls -la scripts/migrate_to_supabase.py
   ```

2. **运行迁移**：
   ```bash
   python scripts/migrate_to_supabase.py
   ```

   这个脚本会：
   - 从本地 SQLite 读取所有数据
   - 迁移到 Supabase PostgreSQL
   - 显示迁移进度和结果

3. **验证迁移**：
   ```bash
   python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM supervisors'); print(f'✓ PostgreSQL 中有 {cursor.fetchone()[0]} 条记录'); conn.close()"
   ```

### 步骤 7：验证自动清理功能

1. **测试自动清理**：
   ```bash
   python -c "from app.modules.db_cleanup import auto_cleanup_page_cache; stats = auto_cleanup_page_cache(); print(f'清理统计: {stats}')"
   ```

2. **检查清理是否工作**：
   - 清理应该成功执行
   - 不会报错

---

## 🔄 自动清理在云端的工作方式

### 工作原理

```
用户搜索
  ↓
发现新的 supervisors
  ↓
批量保存到 Supabase PostgreSQL (>= 10个)
  ↓
自动清理 page_cache（轻量级，< 1秒）
  ↓
数据库保持轻量级 ✅
```

### 清理内容

- ✅ **删除所有 `page_cache` 条目**
  - 这些条目可以重新生成
  - 是数据库大小的主要来源

- ✅ **限制缓存大小**
  - 最多保留 500 条缓存条目
  - 自动删除最旧的条目

- ❌ **不运行 VACUUM**
  - PostgreSQL 不需要 VACUUM（SQLite 需要）
  - PostgreSQL 自动管理空间

### 清理频率

- **自动触发**：每次批量更新 >= 10 个 profiles 时
- **无需手动操作**：完全自动化
- **不影响性能**：清理操作非常快（< 1 秒）

---

## 📝 配置选项

### 调整清理阈值

如果需要调整自动清理的触发条件，编辑 `app/modules/local_repo.py`：

```python
# 修改批量更新阈值（默认：10）
if len(profiles) >= 10:  # 改为其他数字，如 5 或 20

# 修改缓存保留数量（默认：500）
auto_cleanup_page_cache(
    keep_days=0,
    max_cache_entries=500  # 改为其他数字，如 1000 或 2000
)
```

### 禁用自动清理（不推荐）

如果需要禁用自动清理，编辑 `app/modules/local_repo.py`：

```python
# 注释掉自动清理代码
# try:
#     from app.modules.db_cleanup import auto_cleanup_page_cache
#     if len(profiles) >= 10:
#         auto_cleanup_page_cache(keep_days=0, max_cache_entries=500)
# except Exception:
#     pass
```

---

## ⚠️ 注意事项

### 1. 密码安全

- ✅ **不要在代码中硬编码密码**
- ✅ **使用 Streamlit Secrets 存储密码**
- ✅ **不要将 `.env` 文件提交到 Git**

### 2. 数据库连接

- ✅ **Supabase 要求 SSL 连接**（`DB_SSLMODE=require`）
- ✅ **确保网络可以访问 Supabase**（某些网络可能阻止）

### 3. 数据迁移

- ✅ **迁移是一次性操作**
- ✅ **迁移后可以保留本地 SQLite 作为备份**
- ✅ **建议先测试连接再迁移数据**

### 4. 自动清理

- ✅ **清理不会影响核心数据**（supervisors 信息完全保留）
- ✅ **清理失败不会中断主流程**（使用 try-except 包装）
- ✅ **PostgreSQL 不需要 VACUUM**（SQLite 需要）

---

## 🔍 故障排除

### 问题 1：连接失败

**错误**：`could not translate host name` 或 `connection timeout`

**解决方法**：
1. 检查 Supabase 项目状态是否为 **Active**
2. 确认 `DB_HOST` 正确（应该是 `db.xxxxx.supabase.co`）
3. 检查网络连接
4. 等待几分钟让 DNS 传播

### 问题 2：认证失败

**错误**：`password authentication failed`

**解决方法**：
1. 确认密码正确（在 Supabase Dashboard 中重置密码）
2. 检查 `DB_USER` 是否为 `postgres`
3. 检查 `DB_NAME` 是否为 `postgres`

### 问题 3：自动清理不工作

**检查**：
1. 确认批量更新 >= 10 个 profiles
2. 检查是否有错误日志
3. 手动测试清理函数：
   ```bash
   python -c "from app.modules.db_cleanup import auto_cleanup_page_cache; stats = auto_cleanup_page_cache(); print(stats)"
   ```

---

## 📊 监控和维护

### 检查数据库大小

在 Supabase Dashboard：
1. 进入 **Database** → **Database Size**
2. 查看当前数据库大小
3. 监控增长趋势

### 检查缓存条目数

```bash
python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM page_cache'); print(f'Cache entries: {cursor.fetchone()[0]}'); conn.close()"
```

### 手动运行完整清理（如果需要）

虽然自动清理已经足够，但如果需要手动清理：

```bash
# 对于 PostgreSQL，只需要删除 page_cache
python -c "from app.modules.db_cleanup import auto_cleanup_page_cache; auto_cleanup_page_cache(keep_days=0)"
```

---

## ✅ 完成检查清单

- [ ] Supabase 项目已创建
- [ ] 数据库连接信息已获取
- [ ] Streamlit Secrets 已配置
- [ ] 本地连接测试成功
- [ ] 数据库表结构已初始化
- [ ] 数据已迁移到 Supabase
- [ ] 自动清理功能已验证
- [ ] Streamlit Cloud 应用可以访问数据库

---

## 📚 相关文档

- `SUPABASE_SETUP.md` - Supabase 详细设置指南
- `AUTO_CLEANUP.md` - 自动清理功能说明
- `MIGRATE_TO_CLOUD.md` - 迁移到云数据库指南
- `scripts/migrate_to_supabase.py` - 迁移脚本

---

## 🎉 完成！

一旦完成所有步骤：

1. ✅ 数据库已存储在云端
2. ✅ Streamlit Cloud 可以访问数据库
3. ✅ 自动清理功能正常工作
4. ✅ 数据库大小保持合理
5. ✅ 可以安全地删除本地 SQLite 文件（可选）

**恭喜！你的数据库现在在云端，并且会自动清理！** 🎊

---

**最后更新 / Last Updated:** 2024

