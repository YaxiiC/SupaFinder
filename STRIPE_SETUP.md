# Stripe 支付集成设置指南

## 📋 概述

本应用已集成 Stripe 支付网关，支持用户通过信用卡/借记卡订阅服务。

## 🔧 设置步骤

### 步骤 1: 创建 Stripe 账号

1. 访问 https://stripe.com
2. 注册账号（免费）
3. 完成账号验证

### 步骤 2: 获取 API Keys

1. 登录 Stripe Dashboard: https://dashboard.stripe.com
2. 进入 **Developers** → **API keys**
3. 复制以下密钥：
   - **Publishable key** (pk_test_... 或 pk_live_...)
   - **Secret key** (sk_test_... 或 sk_live_...)

**注意**：
- `test` 开头的密钥用于测试环境（不会产生真实扣款）
- `live` 开头的密钥用于生产环境（会产生真实扣款）

### 步骤 3: 创建产品和价格

1. 在 Stripe Dashboard 中，进入 **Products**
2. 点击 **Add product**
3. 创建两个产品：

#### Individual Plan
- **Name**: Individual Plan
- **Description**: 3 searches per month
- **Pricing**: 
  - **Recurring**: Monthly
  - **Price**: $25.00 USD
- 复制生成的 **Price ID** (例如: `price_1ABC123...`)

#### Enterprise Plan
- **Name**: Enterprise Plan
- **Description**: 10 searches per month
- **Pricing**:
  - **Recurring**: Monthly
  - **Price**: $55.00 USD
- 复制生成的 **Price ID** (例如: `price_1XYZ789...`)

### 步骤 4: 配置 Streamlit Secrets

在 Streamlit Cloud 上配置支付密钥：

1. 登录 https://share.streamlit.io/
2. 进入你的应用 → **Settings** → **Secrets**
3. 添加以下配置：

```toml
# App URL (必需 - 用于支付成功后的重定向)
APP_URL = "https://supafinder.streamlit.app"

# Stripe API Keys
STRIPE_SECRET_KEY = "sk_test_你的Secret_Key"
STRIPE_PUBLISHABLE_KEY = "pk_test_你的Publishable_Key"

# Stripe Price IDs (从步骤3中获取)
STRIPE_PRICE_ID_INDIVIDUAL = "price_1ABC123..."
STRIPE_PRICE_ID_ENTERPRISE = "price_1XYZ789..."

# Webhook Secret (可选，用于处理支付回调)
STRIPE_WEBHOOK_SECRET = "whsec_你的Webhook_Secret"
```

**重要**：`APP_URL` 必须是你的 Streamlit Cloud 应用的完整 URL（例如：`https://supafinder.streamlit.app`）。这个 URL 用于支付成功后重定向回应用。

### 步骤 5: 本地开发配置（可选）

如果你在本地开发，在 `.env` 文件中添加：

```env
STRIPE_SECRET_KEY=sk_test_你的Secret_Key
STRIPE_PUBLISHABLE_KEY=pk_test_你的Publishable_Key
STRIPE_PRICE_ID_INDIVIDUAL=price_1ABC123...
STRIPE_PRICE_ID_ENTERPRISE=price_1XYZ789...
```

## 🧪 测试支付

### 使用测试卡号

Stripe 提供测试卡号，不会产生真实扣款：

- **成功支付**: `4242 4242 4242 4242`
- **需要3D验证**: `4000 0025 0000 3155`
- **支付失败**: `4000 0000 0000 0002`

其他测试信息：
- **过期日期**: 任何未来日期（例如: 12/25）
- **CVC**: 任意3位数字（例如: 123）
- **邮编**: 任意5位数字（例如: 12345）

### 测试流程

1. 使用测试密钥配置应用
2. 点击订阅按钮
3. 使用测试卡号完成支付
4. 检查订阅是否成功创建

## 🔄 支付流程

1. **用户点击订阅** → 创建 Stripe Checkout Session
2. **重定向到 Stripe** → 用户输入支付信息
3. **支付成功** → Stripe 重定向回应用
4. **应用验证支付** → 创建订阅记录
5. **用户可以使用服务** → 订阅激活

## 📝 注意事项

1. **测试环境 vs 生产环境**:
   - 开发/测试时使用 `test` 密钥
   - 上线前切换到 `live` 密钥

2. **Webhook 配置** (可选但推荐):
   - 用于处理支付成功/失败的回调
   - 更可靠的支付状态同步
   - 需要在 Stripe Dashboard 中配置 Webhook endpoint

3. **安全性**:
   - **永远不要**将 Secret Key 提交到 Git
   - 使用 Streamlit Secrets 或环境变量
   - 定期轮换密钥

4. **费用**:
   - Stripe 收取每笔交易的 2.9% + $0.30
   - 例如: $25 订阅 → Stripe 费用 $1.03 → 你收到 $23.97

## 🚀 上线前检查清单

- [ ] 切换到 `live` API keys
- [ ] 更新 Price IDs 为生产环境的
- [ ] 配置 Webhook endpoint（可选）
- [ ] 测试完整支付流程
- [ ] 验证订阅创建逻辑
- [ ] 检查错误处理

## 📚 更多资源

- [Stripe 文档](https://stripe.com/docs)
- [Stripe Checkout 指南](https://stripe.com/docs/payments/checkout)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)

