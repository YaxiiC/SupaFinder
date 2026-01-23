# 更新 Supabase Transaction Pooler 配置

## 📋 新的连接信息

你已切换到 **Transaction Pooler**，这是 Supabase 推荐的连接方式，特别适合：
- ✅ 高并发连接
- ✅ 更好的性能
- ✅ 连接池管理

### 新配置信息：

```
Host: aws-1-eu-west-1.pooler.supabase.com
Port: 6543
Database: postgres
User: postgres.kcyfwlcatgtgzntiwmoo
Pool Mode: transaction
```

## 🔧 更新步骤

### 步骤 1：更新 .env 文件

编辑 `.env` 文件，更新以下配置：

```env
DB_TYPE=postgresql
DB_HOST=aws-1-eu-west-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.kcyfwlcatgtgzntiwmoo
DB_PASSWORD=your-password-here
DB_SSLMODE=require
```

**重要**：
- Port 从 `5432` 改为 `6543`
- User 从 `postgres` 改为 `postgres.kcyfwlcatgtgzntiwmoo`
- Host 改为 pooler 地址

### 步骤 2：测试连接

运行测试脚本：

```bash
source .venv/bin/activate
python scripts/test_supabase_project.py
```

### 步骤 3：如果连接成功，运行迁移

```bash
python scripts/migrate_to_supabase.py
```

## ⚠️ 注意事项

### Transaction Pooler vs Direct Connection

**Transaction Pooler (推荐)**：
- ✅ 更好的并发性能
- ✅ 连接池管理
- ✅ 适合生产环境
- Port: `6543`
- User: `postgres.xxxxx` (包含项目 ID)

**Direct Connection**：
- 直接连接到数据库
- Port: `5432`
- User: `postgres`

### SSL 模式

Transaction Pooler 仍然需要 SSL：
- `DB_SSLMODE=require` ✅

## 🔍 故障排除

如果连接失败：

1. **检查 DNS 解析**：
   ```bash
   nslookup aws-1-eu-west-1.pooler.supabase.com
   ```

2. **验证密码**：
   - 确认 `.env` 文件中的 `DB_PASSWORD` 是正确的
   - 在 Supabase Dashboard → Settings → Database 可以重置密码

3. **检查端口**：
   - 确保 Port 是 `6543`（不是 `5432`）

4. **检查用户格式**：
   - User 应该是 `postgres.kcyfwlcatgtgzntiwmoo`（包含项目 ID）

## ✅ 验证清单

- [ ] `.env` 文件已更新
- [ ] `DB_HOST` 设置为 pooler 地址
- [ ] `DB_PORT` 设置为 `6543`
- [ ] `DB_USER` 设置为 `postgres.kcyfwlcatgtgzntiwmoo`
- [ ] `DB_PASSWORD` 已正确设置
- [ ] DNS 可以解析 pooler 地址
- [ ] 测试连接成功
- [ ] 迁移脚本可以运行

---

**下一步**：更新 `.env` 文件，然后运行测试脚本！

