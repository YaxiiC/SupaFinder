# 数据库迁移到云端 - 详细步骤指南

## 📋 概述

本指南将帮助你一步一步把 SuperFinder 的数据库迁移到云端。我们支持两种方式：
1. **云文件同步**（推荐，最简单）- 使用 iCloud Drive、Dropbox 等
2. **PostgreSQL 云数据库**（更专业）- 使用 Supabase、Heroku 等

---

## 🎯 方式一：云文件同步（推荐）

这是最简单的方式，适合个人使用。数据库文件会自动同步到云端。

### 步骤 1: 选择云存储服务

选择一个你已经在使用的云存储服务：
- **iCloud Drive**（macOS 推荐）
- **Dropbox**
- **Google Drive**（需要安装同步客户端）
- **OneDrive**

### 步骤 2: 创建云存储文件夹

#### 选项 A: iCloud Drive（macOS）

```bash
# 创建 SuperFinder 文件夹
mkdir -p ~/Library/Mobile\ Documents/com~apple~CloudDocs/SuperFinder

# 查看路径（复制这个路径，稍后需要）
echo ~/Library/Mobile\ Documents/com~apple~CloudDocs/SuperFinder
```

#### 选项 B: Dropbox

```bash
# 创建 SuperFinder 文件夹
mkdir -p ~/Dropbox/SuperFinder

# 查看路径
echo ~/Dropbox/SuperFinder
```

#### 选项 C: Google Drive

```bash
# 通常路径是（根据你的设置可能不同）
mkdir -p ~/Google\ Drive/SuperFinder

# 查看路径
echo ~/Google\ Drive/SuperFinder
```

### 步骤 3: 备份当前数据库

**重要：在移动数据库之前，先备份！**

```bash
cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder

# 备份当前数据库
cp cache.sqlite cache.sqlite.backup

# 验证备份成功
ls -lh cache.sqlite*
```

### 步骤 4: 移动数据库到云端

#### 如果使用 iCloud Drive：

```bash
# 移动数据库文件
mv cache.sqlite ~/Library/Mobile\ Documents/com~apple~CloudDocs/SuperFinder/cache.sqlite

# 验证移动成功
ls -lh ~/Library/Mobile\ Documents/com~apple~CloudDocs/SuperFinder/cache.sqlite
```

#### 如果使用 Dropbox：

```bash
# 移动数据库文件
mv cache.sqlite ~/Dropbox/SuperFinder/cache.sqlite

# 验证移动成功
ls -lh ~/Dropbox/SuperFinder/cache.sqlite
```

### 步骤 5: 更新 .env 配置文件

编辑 `.env` 文件（如果不存在，从 `env.example` 复制）：

```bash
# 打开 .env 文件
nano .env
# 或使用你喜欢的编辑器
```

添加或修改以下配置：

#### iCloud Drive 配置：

```env
# Database configuration
DB_TYPE=cloud_sqlite
CLOUD_DB_PATH=/Users/chrissychen/Library/Mobile Documents/com~apple~CloudDocs/SuperFinder/cache.sqlite
```

#### Dropbox 配置：

```env
# Database configuration
DB_TYPE=cloud_sqlite
CLOUD_DB_PATH=/Users/chrissychen/Dropbox/SuperFinder/cache.sqlite
```

**注意**：请将 `/Users/chrissychen` 替换为你的实际用户名！

### 步骤 6: 验证配置

```bash
# 激活虚拟环境
source .venv/bin/activate

# 测试数据库连接
python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); print('✓ 数据库连接成功！'); conn.close()"

# 检查数据库中的记录数
python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM supervisors'); print(f'✓ 找到 {cursor.fetchone()[0]} 条记录'); conn.close()"
```

如果看到 "✓ 数据库连接成功！" 和记录数，说明配置正确！

### 步骤 7: 测试运行

```bash
# 运行一个简单的查询测试
python scripts/diagnose_local_db.py
```

如果一切正常，你应该能看到数据库中的记录。

---

## 🗄️ 方式二：PostgreSQL 云数据库（高级）

如果你需要多用户访问或更专业的数据库管理，可以使用 PostgreSQL。

### 步骤 1: 选择 PostgreSQL 服务提供商

推荐免费/低成本的选项：
- **[Supabase](https://supabase.com)** - 免费 500MB，推荐 ⭐
- **[Heroku Postgres](https://www.heroku.com/postgres)** - 免费 10,000 行
- **[Neon](https://neon.tech)** - 免费 512MB
- **[AWS RDS](https://aws.amazon.com/rds/)** - 付费但功能强大

### 步骤 2: 创建 PostgreSQL 数据库

以 **Supabase** 为例：

1. 访问 https://supabase.com
2. 注册/登录账号
3. 创建新项目
4. 等待项目创建完成（约 2 分钟）
5. 进入项目 → Settings → Database
6. 找到 "Connection string" → 选择 "URI"
7. 复制连接字符串，格式类似：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

### 步骤 3: 安装 PostgreSQL 驱动

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装 PostgreSQL 驱动
pip install psycopg2-binary
```

### 步骤 4: 更新 .env 配置文件

编辑 `.env` 文件，添加 PostgreSQL 配置：

```env
# Database configuration
DB_TYPE=postgresql
DB_HOST=db.xxxxx.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password_here
```

**注意**：
- `DB_HOST`: 从 Supabase 连接字符串中提取（`db.xxxxx.supabase.co`）
- `DB_PASSWORD`: 从 Supabase 连接字符串中提取（`[YOUR-PASSWORD]`）
- 其他字段通常使用默认值

### 步骤 5: 初始化数据库表

```bash
# 激活虚拟环境
source .venv/bin/activate

# 初始化数据库（创建表结构）
python -c "from app.db_cloud import init_db; init_db(); print('✓ 数据库表创建成功！')"
```

### 步骤 6: 迁移数据（从本地 SQLite 到 PostgreSQL）

创建一个迁移脚本：

```bash
# 创建迁移脚本
cat > scripts/migrate_to_postgresql.py << 'EOF'
#!/usr/bin/env python3
"""迁移数据从 SQLite 到 PostgreSQL"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from app.db_cloud import get_db_connection, init_db
from app.config import CACHE_DB

# 初始化 PostgreSQL 数据库
print("初始化 PostgreSQL 数据库...")
init_db()

# 连接两个数据库
print("连接数据库...")
sqlite_conn = sqlite3.connect(CACHE_DB)
pg_conn = get_db_connection()

sqlite_cursor = sqlite_conn.cursor()
pg_cursor = pg_conn.cursor()

# 迁移 supervisors 表
print("迁移 supervisors 表...")
sqlite_cursor.execute("SELECT * FROM supervisors")
rows = sqlite_cursor.fetchall()

# 获取列名
columns = [description[0] for description in sqlite_cursor.description]

for row in rows:
    # 构建插入语句
    placeholders = ",".join(["?" for _ in columns])
    insert_sql = f"INSERT INTO supervisors ({','.join(columns)}) VALUES ({placeholders}) ON CONFLICT (canonical_id) DO NOTHING"
    pg_cursor.execute(insert_sql, row)

pg_conn.commit()
print(f"✓ 迁移了 {len(rows)} 条 supervisors 记录")

# 关闭连接
sqlite_conn.close()
pg_conn.close()
print("✓ 迁移完成！")
EOF

chmod +x scripts/migrate_to_postgresql.py

# 运行迁移
python scripts/migrate_to_postgresql.py
```

### 步骤 7: 验证迁移

```bash
# 检查 PostgreSQL 中的记录数
python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM supervisors'); print(f'✓ PostgreSQL 中有 {cursor.fetchone()[0]} 条记录'); conn.close()"
```

---

## 🔍 验证和测试

无论使用哪种方式，都应该验证：

### 1. 检查数据库连接

```bash
python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); print('✓ 连接成功'); conn.close()"
```

### 2. 检查记录数

```bash
python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM supervisors'); print(f'✓ 记录数: {cursor.fetchone()[0]}'); conn.close()"
```

### 3. 运行诊断脚本

```bash
python scripts/diagnose_local_db.py
```

### 4. 测试完整流程

运行一次 pipeline，确保一切正常：

```bash
python -m app.main \
  --cv data/your_cv.pdf \
  --keywords "test keywords" \
  --universities data/universities_template.xlsx \
  --target 10
```

---

## ⚠️ 常见问题

### 问题 1: 找不到数据库文件

**错误信息**：`FileNotFoundError` 或 `no such file or directory`

**解决方法**：
1. 检查 `.env` 中的 `CLOUD_DB_PATH` 路径是否正确
2. 确保路径使用绝对路径（以 `/` 开头）
3. 检查文件是否真的存在于该路径

```bash
# 检查文件是否存在
ls -lh "$CLOUD_DB_PATH"
```

### 问题 2: 权限错误

**错误信息**：`Permission denied`

**解决方法**：
```bash
# 给数据库文件添加写权限
chmod 644 /path/to/cache.sqlite

# 给文件夹添加写权限
chmod 755 /path/to/SuperFinder
```

### 问题 3: PostgreSQL 连接失败

**错误信息**：`Failed to connect to PostgreSQL`

**解决方法**：
1. 检查 `.env` 中的连接信息是否正确
2. 检查 PostgreSQL 服务是否运行
3. 检查防火墙设置（某些云服务需要添加 IP 白名单）
4. 验证密码是否正确

### 问题 4: 数据不同步

**问题**：在多个设备上使用，数据不一致

**解决方法**：
- 对于云文件同步：确保文件完全同步后再在另一台设备上使用
- 对于 PostgreSQL：这是正常的，多设备可以同时访问

---

## 🔄 切换回本地数据库

如果想切换回本地数据库：

1. 编辑 `.env` 文件：
   ```env
   DB_TYPE=sqlite
   # 注释掉或删除 CLOUD_DB_PATH
   ```

2. 或者直接删除 `.env` 中的数据库配置，使用默认值

---

## 📊 数据库大小监控

定期检查数据库大小：

```bash
# 云文件同步方式
ls -lh ~/Dropbox/SuperFinder/cache.sqlite
# 或
ls -lh ~/Library/Mobile\ Documents/com~apple~CloudDocs/SuperFinder/cache.sqlite

# PostgreSQL 方式（在 Supabase 控制台查看）
```

如果数据库太大，可以运行清理脚本：

```bash
# 清理 30 天前的页面缓存
python scripts/cleanup_old_cache.py --page-cache-days 30
```

---

## ✅ 完成检查清单

- [ ] 选择了云存储方式（文件同步 或 PostgreSQL）
- [ ] 备份了当前数据库
- [ ] 移动/配置了云数据库
- [ ] 更新了 `.env` 配置文件
- [ ] 验证了数据库连接
- [ ] 测试了完整流程
- [ ] 确认数据可以正常访问

---

## 🆘 需要帮助？

如果遇到问题：
1. 检查 `.env` 文件配置
2. 查看错误日志
3. 运行诊断脚本：`python scripts/diagnose_local_db.py`
4. 检查数据库文件权限和路径

祝你迁移顺利！🎉

