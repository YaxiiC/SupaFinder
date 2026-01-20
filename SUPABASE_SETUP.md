# Supabase 数据库设置指南

## 📋 当前状态

- ✅ PostgreSQL 驱动已安装 (`psycopg2-binary`)
- ✅ `.env` 文件已配置 PostgreSQL 连接信息
- ✅ 迁移脚本已准备就绪
- ⏳ 等待 Supabase 项目完全创建

## 🔍 检查项目状态

1. 访问 Supabase Dashboard：https://supabase.com/dashboard/project/llvvfsoycpfwomhoryga
2. 确认项目状态为 **Active**（不是 Pending）
3. 等待数据库完全初始化（通常需要 2-5 分钟）

## 🚀 设置步骤

### 步骤 1: 确认项目已准备好

在 Supabase 控制台检查：
- 项目状态为 **Active**
- Settings > Database 页面可以访问
- 可以看到连接字符串

### 步骤 2: 测试数据库连接

```bash
cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder
source .venv/bin/activate
python scripts/test_supabase_connection.py
```

如果看到 `✓ 数据库连接成功！`，继续下一步。

### 步骤 3: 初始化数据库表结构

```bash
python -c "from app.db_cloud import init_db; init_db(); print('✓ 数据库表创建成功！')"
```

### 步骤 4: 迁移数据（从 Dropbox SQLite 到 PostgreSQL）

```bash
python scripts/migrate_to_supabase.py
```

这个脚本会：
- 从 Dropbox SQLite 读取数据
- 迁移到 Supabase PostgreSQL
- 显示迁移进度和结果

### 步骤 5: 验证迁移

```bash
python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM supervisors'); print(f'✓ PostgreSQL 中有 {cursor.fetchone()[0]} 条记录'); conn.close()"
```

## 🔧 当前配置

`.env` 文件中的配置：
```env
DB_TYPE=postgresql
DB_HOST=db.llvvfsoycpfwomhoryga.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=Chenyaxi2015!
```

## ⚠️ 常见问题

### 问题 1: 主机名无法解析

**错误**：`could not translate host name`

**解决方法**：
1. 确认项目是否完全创建（状态为 Active）
2. 等待几分钟让 DNS 传播
3. 检查 Supabase 控制台中的实际主机名

### 问题 2: 连接超时

**解决方法**：
1. 检查网络连接
2. 确认防火墙没有阻止 PostgreSQL 端口（5432）
3. 在 Supabase 控制台检查数据库是否可用

### 问题 3: 认证失败

**解决方法**：
1. 确认密码正确
2. 检查数据库用户名是否为 `postgres`
3. 确认数据库名称为 `postgres`

## ✅ 完成后

一旦连接成功并完成迁移：
1. ✅ 所有数据已存储在 Supabase 云端
2. ✅ 可以安全地删除 Dropbox SQLite 文件（可选）
3. ✅ 应用已配置为使用 PostgreSQL
4. ✅ 可以部署到云平台

## 📝 回退方案

如果需要回退到 Dropbox SQLite：

编辑 `.env` 文件：
```env
DB_TYPE=cloud_sqlite
CLOUD_DB_PATH=/Users/chrissychen/Dropbox/SuperFinder/cache.sqlite
```

删除或注释掉 PostgreSQL 配置。

