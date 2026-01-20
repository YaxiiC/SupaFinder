# 订阅系统使用说明

## 概述

SuperFinder现在支持订阅系统，提供三种订阅计划：

1. **免费试用**：每个新用户自动获得1次免费搜索
2. **个人用户包月**：每月3次搜索，$25 USD
3. **企业用户包月**：每月10次搜索，$55 USD

## 功能特性

- ✅ 用户邮箱注册/登录（无需密码，使用邮箱作为唯一标识）
- ✅ 自动创建免费试用订阅
- ✅ 订阅状态和剩余次数实时显示
- ✅ 搜索前自动检查订阅和剩余次数
- ✅ 搜索后自动扣减次数并记录日志
- ✅ 月度订阅自动重置（每月同日期重置搜索次数）
- ✅ 搜索历史记录查看

## 数据库结构

订阅系统使用以下数据表：

### `users` 表
- `id`: 用户ID（主键）
- `email`: 用户邮箱（唯一）
- `created_at`: 注册时间
- `last_login_at`: 最后登录时间

### `subscriptions` 表
- `id`: 订阅ID（主键）
- `user_id`: 用户ID（外键）
- `subscription_type`: 订阅类型（'free', 'individual', 'enterprise'）
- `status`: 订阅状态（'active', 'expired', 'cancelled'）
- `searches_per_month`: 每月搜索次数
- `remaining_searches`: 剩余搜索次数
- `started_at`: 订阅开始时间
- `expires_at`: 订阅过期时间
- `created_at`: 创建时间
- `updated_at`: 更新时间

### `search_logs` 表
- `id`: 日志ID（主键）
- `user_id`: 用户ID（外键）
- `subscription_id`: 订阅ID（外键）
- `search_type`: 搜索类型（'free', 'individual', 'enterprise'）
- `keywords`: 搜索关键词
- `universities_count`: 搜索的大学数量
- `regions`: 地区筛选
- `countries`: 国家筛选
- `result_count`: 结果数量
- `created_at`: 搜索时间

## 使用方法

### 1. 通过Streamlit UI使用（推荐）

```bash
streamlit run ui/streamlit_app.py
```

1. **登录/注册**：
   - 在左侧边栏输入邮箱地址
   - 点击"Login / Register"
   - 新用户会自动创建账户并分配1次免费搜索

2. **查看订阅状态**：
   - 登录后，左侧边栏显示当前订阅信息和剩余搜索次数

3. **管理订阅**：
   - 点击"💳 Manage Subscription"按钮
   - 选择"Individual Plan"或"Enterprise Plan"
   - 点击订阅按钮（目前是创建订阅，实际支付集成需要额外开发）

4. **查看搜索历史**：
   - 点击"📜 Search History"按钮
   - 查看最近的搜索记录

### 2. 通过命令行使用（无需订阅）

命令行模式（`python -m app.main`）不需要订阅检查，可以直接使用。这是为了向后兼容和开发/测试目的。

## 订阅管理API

### 核心函数

```python
from app.modules.subscription import (
    get_or_create_user,
    get_user_subscription,
    can_perform_search,
    consume_search,
    create_subscription,
    get_user_search_history
)

# 获取或创建用户
user_id = get_or_create_user("user@example.com")

# 检查是否可以搜索
can_search, error_msg, subscription = can_perform_search(user_id)

# 执行搜索（在pipeline中自动调用）
consume_search(user_id, subscription_id, search_info)

# 创建订阅
subscription_id = create_subscription(user_id, "individual")  # 或 "enterprise"

# 获取搜索历史
history = get_user_search_history(user_id, limit=10)
```

## 月度重置逻辑

订阅的搜索次数会在以下情况下自动重置：

1. **每月同日期重置**：如果订阅的`started_at`日期已经超过一个月，系统会自动将`remaining_searches`重置为`searches_per_month`
2. **每次搜索前检查**：在`can_perform_search()`函数中会自动检查是否需要重置

例如：
- 订阅开始日期：2024-01-15
- 每月15日自动重置搜索次数
- 如果用户在2024-02-15之后搜索，次数会自动重置为满额

## 支付集成（待开发）

当前版本只实现了订阅管理的后端逻辑和UI界面。要完整实现支付功能，需要集成支付网关，例如：

- **Stripe**：推荐用于国际支付
- **支付宝/微信支付**：如果主要面向中国用户

集成支付后，需要：
1. 创建支付会话（Checkout Session）
2. 处理支付成功回调（Webhook）
3. 根据支付结果创建/更新订阅
4. 处理订阅续费

## 开发者模式

开发者可以配置无限制访问，无需订阅检查。

### 配置开发者邮箱

在 `.env` 文件中设置 `DEVELOPER_EMAILS` 环境变量：

```bash
# 单个开发者邮箱
DEVELOPER_EMAILS=dev@example.com

# 多个开发者邮箱（逗号分隔）
DEVELOPER_EMAILS=dev@example.com,admin@example.com,test@example.com
```

### 开发者特权

- ✅ **无限制搜索**：不扣减搜索次数
- ✅ **无需订阅**：自动跳过订阅检查
- ✅ **搜索记录**：仍然记录搜索日志（标记为"developer"类型）
- ✅ **UI显示**：侧边栏显示"Developer Mode - Unlimited access"

### 注意事项

1. 开发者模式基于邮箱地址，大小写不敏感
2. 修改 `.env` 后需要重启Streamlit应用才能生效
3. 开发者邮箱仍然会在数据库中创建用户记录，但不会创建订阅记录
4. 开发者的搜索会记录在 `search_logs` 表中，`search_type` 为 "developer"

## 配置

订阅系统会自动使用现有的数据库配置（`DB_TYPE`环境变量）。支持：
- SQLite（默认）
- PostgreSQL

数据库初始化时自动创建订阅相关的表。

## 注意事项

1. **邮箱作为唯一标识**：目前使用邮箱作为用户标识，不需要密码。如果需要在生产环境中使用，建议添加密码验证或OAuth登录。

2. **订阅过期**：订阅过期后会自动标记为'expired'状态，用户需要重新订阅。

3. **免费试用**：新用户注册时自动获得1次免费搜索，免费试用不会过期（设置为1年有效期）。

4. **搜索次数扣减**：每次成功运行pipeline后会自动扣减1次搜索次数。

5. **命令行模式**：CLI模式（`app/main.py`）不会检查订阅，保留向后兼容性。

## 故障排查

### 问题：提示"No active subscription"
- 检查用户是否已登录
- 检查订阅是否已过期
- 尝试重新订阅

### 问题：提示"No searches remaining"
- 等待下个月份重置
- 升级到更高套餐
- 检查订阅状态是否正确

### 问题：数据库错误
- 确保数据库已初始化：`from app.db_cloud import init_db; init_db()`
- 检查数据库连接配置
- 查看数据库日志

## 未来改进

- [ ] 集成Stripe支付网关
- [ ] 添加密码或OAuth登录
- [ ] 支持年度订阅计划
- [ ] 添加订阅到期提醒邮件
- [ ] 支持订阅升级/降级
- [ ] 添加管理后台查看所有订阅
- [ ] 支持发票/收据生成

