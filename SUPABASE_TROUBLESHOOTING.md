# Supabase 连接问题排查指南

## 🔍 当前问题

虽然 Supabase 项目状态显示为 **healthy**，但数据库主机名 `db.llvvfsoycpfwomhoryga.supabase.co` 无法解析。

## ✅ 解决步骤

### 步骤 1: 从 Supabase 控制台获取实际连接字符串

1. 访问 Supabase Dashboard：
   https://supabase.com/dashboard/project/llvvfsoycpfwomhoryga/settings/database

2. 在 **Connection string** 部分：
   - 选择 **URI** 标签
   - 复制**完整的连接字符串**（格式类似）：
     ```
     postgresql://postgres:[PASSWORD]@[ACTUAL-HOST]:5432/postgres
     ```

3. **重要**：检查实际的数据库主机名是否与 `db.llvvfsoycpfwomhoryga.supabase.co` 相同
   - 如果不同，使用控制台中显示的实际主机名

### 步骤 2: 使用连接字符串解析工具

运行以下命令，并提供完整的连接字符串：

```bash
cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder
source .venv/bin/activate
python scripts/parse_supabase_connection.py
```

然后粘贴完整的连接字符串。工具会：
- 解析连接参数
- 测试 DNS 解析
- 更新 `.env` 文件配置

### 步骤 3: 手动清理 DNS 缓存（可选）

如果 DNS 解析仍然失败，尝试清理本地 DNS 缓存：

```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

注意：需要输入管理员密码。

### 步骤 4: 尝试不同的网络环境

如果 DNS 仍然无法解析，尝试：
1. 使用手机热点
2. 更换网络环境
3. 等待几分钟让 DNS 传播

### 步骤 5: 测试连接

```bash
python scripts/test_supabase_connection.py
```

或使用自动等待脚本（每 30 秒重试一次）：

```bash
python scripts/wait_for_supabase.py
```

## 🔧 如果仍然无法连接

### 选项 A: 检查 Supabase 项目设置

1. 确认项目状态为 **Active**
2. 检查数据库是否已创建：
   - 在 Supabase Dashboard 查看 **Database** 部分
   - 确认可以看到数据库统计信息

### 选项 B: 联系 Supabase 支持

如果项目状态是 healthy 但 DNS 仍然无法解析：
1. 访问 Supabase 支持页面
2. 提供项目引用 ID：`llvvfsoycpfwomhoryga`
3. 说明数据库主机名无法解析的问题

### 选项 C: 暂时使用 Dropbox SQLite（备用方案）

如果需要立即使用，可以暂时切换回 Dropbox SQLite：

编辑 `.env` 文件：
```env
DB_TYPE=cloud_sqlite
CLOUD_DB_PATH=/Users/chrissychen/Dropbox/SuperFinder/cache.sqlite
```

## 📝 常见问题

### Q: 为什么项目状态是 healthy 但 DNS 无法解析？

A: 可能的原因：
- DNS 记录创建和传播需要时间（几分钟到几小时）
- 本地 DNS 缓存问题
- 网络环境限制

### Q: 如何确认实际的数据库主机名？

A: 在 Supabase 控制台的 Settings > Database > Connection string 中查看，那里显示的是实际的主机名。

### Q: 连接字符串中的密码是什么？

A: 这是创建项目时设置的数据库密码。如果你忘记了，可以在 Supabase 控制台的 Settings > Database 中重置密码。

## ✅ 成功连接后的步骤

一旦连接成功，运行：

1. **初始化数据库表结构**：
   ```bash
   python -c "from app.db_cloud import init_db; init_db(); print('✓ 完成！')"
   ```

2. **迁移数据**（从 Dropbox SQLite 到 PostgreSQL）：
   ```bash
   python scripts/migrate_to_supabase.py
   ```

3. **验证迁移**：
   ```bash
   python -c "from app.db_cloud import get_db_connection; conn = get_db_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM supervisors'); print(f'✓ PostgreSQL 中有 {cursor.fetchone()[0]} 条记录'); conn.close()"
   ```

## 📞 需要帮助？

如果问题仍然存在，请：
1. 运行 `python scripts/diagnose_supabase.py` 并查看完整诊断信息
2. 提供 Supabase 控制台中显示的实际连接字符串
3. 确认项目状态和数据库是否已创建

