# PhD Supervisor Finder 代码结构说明

## 项目概述

这是一个 **AI 辅助的博士导师发现工具**，通过你的 **简历 + 研究兴趣 + 筛选条件（地区/大学排名/关键词）** 生成一份 **Excel 导师列表（约100位）**，包含可验证的信息来源。

核心理念：**"通过官方大学页面找人；用证据提取事实；导出为 Excel。"**

---

## 目录结构

```
SuperFinder/
├── app/                          # 主应用代码
│   ├── __init__.py
│   ├── config.py                 # 配置文件（API密钥、阈值、并发设置）
│   ├── schemas.py                # Pydantic 数据模型定义
│   ├── db.py                     # SQLite 缓存（页面缓存、提取结果缓存）
│   ├── db_cloud.py               # 云同步数据库支持（可选）
│   ├── pipeline.py               # 主流程编排器
│   ├── main.py                   # CLI 命令行入口
│   └── modules/                  # 功能模块
│       ├── llm_deepseek.py       # DeepSeek LLM 客户端（JSON模式）
│       ├── search.py             # 搜索适配器（Google CSE）
│       ├── crawl.py              # HTTP 抓取 + 速率限制 + 缓存
│       ├── directory.py          # 目录页面解析 → 个人主页URL
│       ├── profile.py            # 导师信息提取（规则 + LLM 兜底）
│       ├── scoring.py            # 相关性评分 & 分层（Core/Adjacent）
│       ├── validators.py         # 邮箱/URL验证、去重
│       ├── text_clean.py         # HTML 文本清理
│       ├── export_excel.py       # Excel 导出（可点击链接）
│       ├── cv_extractor.py       # CV 关键部分提取
│       ├── local_repo.py         # 本地数据库仓库（导师信息持久化）
│       ├── subscription.py       # 订阅管理模块（用户、订阅、搜索日志）
│       └── utils_identity.py     # 身份识别工具（canonical_id 计算）
├── ui/                           # 用户界面
│   ├── streamlit_app.py          # Streamlit 主界面（运行pipeline）
│   └── edit_supervisors.py      # Streamlit 编辑界面（编辑数据库）
├── scripts/                      # 工具脚本
│   ├── edit_supervisors.py       # 命令行编辑工具
│   ├── import_excel_to_db.py     # Excel导入到数据库
│   ├── fix_wrong_domains.py      # 修复错误域名
│   ├── fix_names_in_db.py       # 修复数据库中的姓名
│   ├── update_university_domains.py  # 更新大学域名
│   ├── cleanup_old_cache.py      # 清理旧缓存
│   └── README_EDITING.md         # 编辑功能说明
├── data/                         # 输入数据
│   ├── universities_template.xlsx # 大学列表模板
│   └── *.pdf                     # CV文件示例
├── outputs/                      # 输出结果
│   └── supervisors.xlsx          # 导师列表结果
├── docs/                         # 文档
│   └── CLOUD_STORAGE.md          # 云存储配置说明
├── SUBSCRIPTION_SYSTEM.md        # 订阅系统使用说明
├── tests/                        # 测试代码
│   └── test_local_db_flow.py     # 本地数据库流程测试
├── requirements.txt              # Python 依赖
├── env.example                   # 环境变量模板
├── code_structure.md             # 本文档
└── cache.sqlite                  # 缓存数据库（包含页面缓存和导师信息）
```

---

## 核心流程 (Pipeline)

```
1. 用户认证与订阅检查（仅Streamlit UI）
   ├── 用户邮箱登录/注册
   ├── 检查订阅状态和剩余搜索次数
   ├── 开发者模式验证（如果配置）
   └── 拒绝无有效订阅的用户

2. 解析输入
   ├── 加载简历 (PDF/TXT)
   ├── 加载大学列表（内置模板：data/universities_template.xlsx）
   ├── 解析筛选条件（地区、QS排名范围）
   └── 自动推断缺失的域名

3. 提取CV关键部分 → LLM分析 → 研究画像 (JSON)
   ├── 提取关键部分（专业/研究经历/出版物/技能，最多3000字符）
   ├── core_keywords (核心关键词 10-20个)
   ├── adjacent_keywords (相邻关键词 10-20个)
   ├── negative_keywords (排除关键词 5-10个)
   ├── preferred_departments (偏好院系 3-8个)
   └── query_templates (搜索模板 5-10个)

4. 本地数据库优先检索（如果启用 local_first=True）
   ├── 根据研究画像和筛选条件查询本地数据库
   ├── 使用关键词匹配和相关性评分
   ├── 返回匹配的导师记录（无需重新抓取）
   └── 如果数量不足，继续在线搜索

5. 在线搜索（如果需要更多导师）
   ├── 搜索大学官网
   │   ├── 查找教职工目录页面
   │   └── 查找研究人员个人主页
   ├── 抓取页面
   │   ├── HTTP 请求 (带速率限制，默认1请求/秒/域名)
   │   ├── 缓存到 SQLite（7天有效期）
   │   └── 提取纯文本
   └── 提取导师信息
       ├── 规则提取：姓名、邮箱、链接、职称
       └── LLM 提取：研究关键词、匹配度评分

6. 验证 & 去重
   ├── 邮箱格式验证
   ├── URL 有效性检查
   ├── 按 canonical_id 去重（基于邮箱/姓名+机构/URL）
   └── 过滤低相关性结果（fit_score < 0.15 或无匹配关键词）

7. 评分 & 筛选
   ├── fit_score >= 0.35 → Core (核心匹配)
   ├── fit_score >= 0.20 → Adjacent (相邻匹配)
   ├── 按分数排序，Core 优先
   └── 选取 Top N 位导师

8. 保存到本地数据库
   ├── 使用 canonical_id 进行 upsert（更新或插入）
   ├── 合并字段（不覆盖非空值为空值）
   └── 更新 last_seen_at 和 last_verified_at 时间戳

9. 记录搜索日志并扣减订阅次数（仅Streamlit UI）
   ├── 记录搜索详情到 search_logs 表
   ├── 扣减用户剩余搜索次数（开发者除外）
   └── 更新订阅状态

10. 导出 Excel
   ├── 可点击的链接（profile_url, homepage_url, scholar_search_url）
   ├── source_url 来源链接
   ├── evidence_snippets 证据片段
   └── 包含所有字段（姓名、邮箱、机构、关键词、匹配度等）
```

---

## 关键模块说明

### `cv_extractor.py` - CV 关键部分提取
- 智能提取CV的关键部分（专业/研究经历/出版物/技能）
- 支持中英文CV格式
- 使用模式匹配识别章节标题
- 限制提取长度（默认3000字符）以减少token消耗
- 提取关键部分而非完整CV，提高LLM处理效率

### `llm_deepseek.py` - DeepSeek 客户端
- 使用 OpenAI 兼容接口调用 DeepSeek API
- 支持 JSON 模式输出
- 自动重试机制（3次）
- 三个主要方法：
  - `cv_to_research_profile()` - CV关键部分 → 研究画像（仅处理提取的关键部分）
  - `extract_profile_keywords()` - 页面文本 → 关键词 + 匹配度
  - `select_directory_urls()` - 候选URL → 目录页面筛选

### `search.py` - 搜索模块
- 使用 Google Custom Search Engine (CSE) API 进行搜索
- `search_site()` - 站内搜索 `site:domain`
- `find_directory_pages()` - 查找教职工目录
- `find_researcher_profiles()` - 根据关键词查找研究人员

### `crawl.py` - 网页抓取
- 每域名速率限制（默认 1请求/秒，可配置）
- SQLite 缓存（7天有效期）
- 使用 trafilatura 提取正文
- BeautifulSoup 作为备用解析器
- 支持并发请求（默认最多5个并发）

### `directory.py` - 目录页面解析
- 从目录页面提取个人主页URL
- 识别多种URL模式（/people/, /profiles/, /staff/ 等）
- 排除目录页面、新闻页面、文章页面
- 支持UCL等特殊格式（profiles.ucl.ac.uk/XXXXX-name）
- 过滤非个人页面（alumni, discover, giving 等）

### `profile.py` - 信息提取
- **规则提取**（不使用LLM）：
  - 邮箱：从 `mailto:` 或页面文本正则匹配，过滤通用邮箱
  - 姓名：从 `<h1>`、`<title>`、`og:title`、schema.org 提取
  - 职称：匹配 Professor、Lecturer 等关键词（支持UK大学特殊职称）
  - URL验证：确保URL域名匹配大学域名
- **LLM 提取**：
  - 研究关键词
  - 匹配度评分 (0-1)
- **智能过滤**：
  - 拒绝非人名（Alumni, Discovery等）
  - 验证是否为个人页面（非目录页）
  - 过滤学生/博士后职位

### `scoring.py` - 评分分层
- `fit_score >= 0.35` → **Core**（核心匹配）
- `fit_score >= 0.20` → **Adjacent**（相邻匹配）
- 按分数排序，Core 优先
- `score_supervisor()` - 计算单个导师的匹配度和分层
- `select_top_n()` - 选择Top N个导师

### `local_repo.py` - 本地数据库仓库
- `upsert_supervisor()` - 单个导师的更新或插入
- `upsert_many()` - 批量更新或插入
- `query_candidates()` - 根据研究画像和筛选条件查询候选导师
- 使用 `canonical_id` 进行去重和合并
- 智能合并字段（不覆盖非空值为空值）
- 更新 `last_seen_at` 和 `last_verified_at` 时间戳

### `subscription.py` - 订阅管理模块
- 用户管理：`get_or_create_user()` - 通过邮箱创建/获取用户
- 订阅检查：`can_perform_search()` - 验证用户订阅和剩余次数
- 搜索扣减：`consume_search()` - 扣减搜索次数并记录日志
- 订阅管理：`create_subscription()` - 创建新订阅
- 历史记录：`get_user_search_history()` - 获取用户搜索历史
- 开发者模式：`is_developer()` - 验证开发者邮箱（无限制访问）
- 月度重置：自动重置每月搜索次数

### `utils_identity.py` - 身份识别工具
- `compute_canonical_id()` - 计算导师的唯一标识符
- 基于邮箱、姓名+机构、profile_url 的组合
- 用于去重和数据库记录合并

### `validators.py` - 验证工具
- `validate_email()` - 邮箱格式验证
- `validate_url()` - URL有效性检查
- `validate_profile()` - 导师信息完整性验证
- `deduplicate_profiles()` - 基于 canonical_id 去重

### `text_clean.py` - 文本清理
- `clean_html_to_text()` - HTML转纯文本
- `extract_relevant_sections()` - 提取相关章节
- `extract_contact_section()` - 提取联系方式部分

### `export_excel.py` - Excel导出
- 导出为Excel格式，包含所有字段
- 可点击的链接（profile_url, homepage_url, scholar_search_url）
- 格式化输出，便于阅读和筛选

---

## 数据模型 (schemas.py)

### `ResearchProfile` - 研究画像
```python
core_keywords: list[str]      # 核心关键词
adjacent_keywords: list[str]  # 相邻关键词
negative_keywords: list[str]  # 排除关键词
preferred_departments: list[str]  # 偏好院系
query_templates: list[str]    # 搜索模板
```

### `SupervisorProfile` - 导师信息
```python
name: str                     # 姓名
first_name: Optional[str]     # 名
last_name: Optional[str]      # 姓
title: Optional[str]           # 职称
institution: str              # 机构
country: str                   # 国家
region: str                    # 地区
qs_rank: Optional[int]         # QS排名
email: Optional[str]           # 邮箱（必须在页面上存在）
email_confidence: str          # 邮箱置信度 (high/medium/low/none)
profile_url: Optional[str]     # 个人主页URL
homepage_url: Optional[str]    # 个人网站URL
keywords: list[str]            # 研究关键词
publications_links: list[str]  # 出版物链接
scholar_search_url: Optional[str]  # Google Scholar搜索URL
fit_score: float               # 匹配度 (0-1)
tier: str                      # 分层 (Core/Adjacent)
source_url: str                # 信息来源URL
evidence_snippets: list[str]   # 证据片段
notes: Optional[str]           # 备注
# 数据库相关字段
canonical_id: Optional[str]    # 唯一标识符（用于去重）
keywords_text: Optional[str]    # 关键词文本（逗号分隔）
last_seen_at: Optional[str]    # 最后出现时间
last_verified_at: Optional[str] # 最后验证时间
from_local_db: bool            # 是否来自本地数据库
matched_terms: list[str]       # 匹配的关键词
```

### `SupervisorRecordDB` - 数据库记录
- 用于持久化存储导师信息
- 包含所有 `SupervisorProfile` 字段
- 使用JSON存储列表字段（keywords, evidence_snippets）
- 包含时间戳字段（created_at, updated_at, last_seen_at, last_verified_at）

### `User` - 用户模型
```python
id: Optional[int]          # 用户ID
email: str                 # 用户邮箱（唯一）
created_at: Optional[str]  # 注册时间
last_login_at: Optional[str]  # 最后登录时间
```

### `Subscription` - 订阅模型
```python
id: Optional[int]          # 订阅ID
user_id: int               # 用户ID
subscription_type: str     # 订阅类型（'free', 'individual', 'enterprise'）
status: str                # 订阅状态（'active', 'expired', 'cancelled'）
searches_per_month: int    # 每月搜索次数
remaining_searches: int    # 剩余搜索次数
started_at: str            # 订阅开始时间
expires_at: str            # 订阅过期时间
created_at: Optional[str]  # 创建时间
updated_at: Optional[str]  # 更新时间
```

---

## 使用方法

### 命令行
```bash
# 基本用法
python -m app.main \
  --cv data/cv.pdf \
  --keywords "medical imaging, deep learning" \
  --universities data/universities_template.xlsx

# 按地区筛选
python -m app.main \
  --cv data/cv.pdf \
  --keywords "AI" \
  --universities data/universities_template.xlsx \
  --regions "Europe,North America"

# 按QS排名范围筛选（Top 50）
python -m app.main \
  --cv data/cv.pdf \
  --keywords "AI" \
  --universities data/universities_template.xlsx \
  --qs_min 1 \
  --qs_max 50

# 组合筛选（欧洲Top 30）
python -m app.main \
  --cv data/cv.pdf \
  --keywords "AI" \
  --universities data/universities_template.xlsx \
  --regions "Europe" \
  --qs_min 1 \
  --qs_max 30 \
  --target 100
```

### Streamlit 界面

#### 主界面（运行Pipeline）
```bash
streamlit run ui/streamlit_app.py
```
- **用户认证**：使用邮箱登录/注册（首次注册自动获得1次免费搜索）
- 上传CV文件（PDF或TXT）
- 输入研究关键词
- **内置大学列表**：自动使用 `data/universities_template.xlsx`（Top 200+ 大学）
- 设置筛选条件（地区、QS排名、目标数量）
- 选择是否优先使用本地数据库
- **订阅状态显示**：侧边栏显示当前订阅和剩余搜索次数
- 运行pipeline并下载结果（自动检查订阅并扣减次数）
- **订阅管理**：管理订阅、查看搜索历史

#### 编辑界面（编辑数据库）
```bash
streamlit run ui/edit_supervisors.py
```
- 搜索和筛选导师
- 查看所有导师详情
- 编辑任何字段（姓名、邮箱、机构、关键词等）
- 删除导师记录
- 查看只读元数据（ID、时间戳、canonical_id）

### 命令行编辑工具
```bash
python scripts/edit_supervisors.py
```
- 交互式菜单
- 列出导师
- 按ID查看导师
- 编辑导师字段
- 删除导师
- 分页浏览

### 其他工具脚本
```bash
# 从Excel导入到数据库
python scripts/import_excel_to_db.py

# 修复错误域名
python scripts/fix_wrong_domains.py

# 修复数据库中的姓名
python scripts/fix_names_in_db.py

# 更新大学域名
python scripts/update_university_domains.py

# 清理旧缓存
python scripts/cleanup_old_cache.py
```

---

## 环境变量 (.env)

```bash
# DeepSeek API
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Google Custom Search Engine (CSE)
GOOGLE_CSE_KEY=xxxxx          # Google CSE API 密钥
GOOGLE_CSE_CX=xxxxx           # Google CSE Engine ID

# 运行时设置
TARGET_SUPERVISORS=100        # 目标导师数量
MAX_SCHOOLS=60                # 最大处理学校数
REQUESTS_PER_DOMAIN_PER_SEC=1.0  # 每域名请求频率（秒）
CRAWL_MAX_DEPTH=2             # 爬取最大深度
MAX_PAGES_PER_SCHOOL=30       # 每学校最大页面数

# 订阅系统配置
# DEVELOPER_EMAILS=dev@example.com,admin@example.com  # 开发者邮箱（无限制访问）

# 数据库配置（可选）
# DB_TYPE=sqlite               # 默认使用SQLite
# CLOUD_DB_PATH=/path/to/cache.sqlite  # 云同步数据库路径
```

---

## 防止幻觉的规则

1. **邮箱必须在页面上存在**（`mailto:` 或可见文本），否则为空
2. **出版物链接必须是页面上的真实URL**，否则为空
3. **每条记录必须包含 `source_url`**
4. **提供 `evidence_snippets`** 作为邮箱/出版物的证据
5. **推测内容只放在 `notes` 字段**，不放入硬字段
6. **URL域名验证**：确保profile URL的域名匹配大学域名
7. **姓名验证**：过滤非人名（Alumni, Discovery等导航词）
8. **页面类型验证**：确保是个人页面而非目录/新闻页面

## 订阅系统

SuperFinder 现在支持订阅系统，提供三种订阅计划：

1. **免费试用**：每个新用户自动获得1次免费搜索
2. **个人用户包月**：每月3次搜索，$25 USD
3. **企业用户包月**：每月10次搜索，$55 USD

### 订阅功能特性

- ✅ 用户邮箱注册/登录（无需密码）
- ✅ 自动创建免费试用订阅
- ✅ 订阅状态和剩余次数实时显示
- ✅ 搜索前自动检查订阅和剩余次数
- ✅ 搜索后自动扣减次数并记录日志
- ✅ 月度订阅自动重置（每月同日期重置）
- ✅ 搜索历史记录查看
- ✅ 开发者模式（无限制访问，通过环境变量配置）

### 订阅API

```python
from app.modules.subscription import (
    get_or_create_user,      # 创建/获取用户
    get_user_subscription,   # 获取订阅信息
    can_perform_search,      # 检查是否可以搜索
    consume_search,          # 扣减搜索次数
    create_subscription,     # 创建订阅
    get_user_search_history, # 获取搜索历史
    is_developer            # 检查是否为开发者
)
```

详细说明请参考 `SUBSCRIPTION_SYSTEM.md`。

---

## 数据库设计

### 表结构

#### `users` - 用户表
- `id` (INTEGER/SERIAL PRIMARY KEY) - 用户ID
- `email` (TEXT UNIQUE) - 用户邮箱（唯一）
- `created_at` (TIMESTAMP/TEXT) - 注册时间
- `last_login_at` (TIMESTAMP/TEXT) - 最后登录时间

#### `subscriptions` - 订阅表
- `id` (INTEGER/SERIAL PRIMARY KEY) - 订阅ID
- `user_id` (INTEGER REFERENCES users(id)) - 用户ID（外键）
- `subscription_type` (TEXT) - 订阅类型（'free', 'individual', 'enterprise'）
- `status` (TEXT) - 订阅状态（'active', 'expired', 'cancelled'）
- `searches_per_month` (INTEGER) - 每月搜索次数
- `remaining_searches` (INTEGER) - 剩余搜索次数
- `started_at` (TIMESTAMP/TEXT) - 订阅开始时间
- `expires_at` (TIMESTAMP/TEXT) - 订阅过期时间
- `created_at` (TIMESTAMP/TEXT) - 创建时间
- `updated_at` (TIMESTAMP/TEXT) - 更新时间

#### `search_logs` - 搜索日志表
- `id` (INTEGER/SERIAL PRIMARY KEY) - 日志ID
- `user_id` (INTEGER REFERENCES users(id)) - 用户ID（外键）
- `subscription_id` (INTEGER REFERENCES subscriptions(id)) - 订阅ID（外键，可为空）
- `search_type` (TEXT) - 搜索类型（'free', 'individual', 'enterprise', 'developer'）
- `keywords` (TEXT) - 搜索关键词
- `universities_count` (INTEGER) - 搜索的大学数量
- `regions` (TEXT) - 地区筛选
- `countries` (TEXT) - 国家筛选
- `result_count` (INTEGER) - 结果数量
- `created_at` (TIMESTAMP/TEXT) - 搜索时间

#### `page_cache` - 页面缓存
- `url` (TEXT PRIMARY KEY) - 页面URL
- `html` (TEXT) - HTML内容
- `text_content` (TEXT) - 提取的文本内容
- `fetched_at` (TIMESTAMP) - 抓取时间
- `status_code` (INTEGER) - HTTP状态码
- 缓存有效期：7天

#### `supervisors` - 导师信息表
- `id` (INTEGER PRIMARY KEY) - 自增ID
- `canonical_id` (TEXT UNIQUE) - 唯一标识符（用于去重）
- `name` (TEXT) - 姓名
- `title` (TEXT) - 职称
- `institution` (TEXT) - 机构
- `domain` (TEXT) - 域名
- `country` (TEXT) - 国家
- `region` (TEXT) - 地区
- `email` (TEXT) - 邮箱
- `email_confidence` (TEXT) - 邮箱置信度
- `homepage` (TEXT) - 个人网站
- `profile_url` (TEXT) - 个人主页URL
- `source_url` (TEXT) - 来源URL
- `evidence_email` (TEXT) - 邮箱证据
- `evidence_snippets_json` (TEXT) - 证据片段（JSON）
- `keywords_json` (TEXT) - 关键词（JSON）
- `keywords_text` (TEXT) - 关键词文本（逗号分隔）
- `last_seen_at` (TEXT) - 最后出现时间
- `last_verified_at` (TEXT) - 最后验证时间
- `created_at` (TEXT) - 创建时间
- `updated_at` (TEXT) - 更新时间

### 去重逻辑

使用 `canonical_id` 进行去重，计算方式：
1. 优先使用邮箱（如果存在）
2. 其次使用 `name + institution + domain`
3. 最后使用 `profile_url`

### 合并策略

当更新已存在的记录时：
- 不覆盖非空值为空值
- 更新 `last_seen_at` 时间戳
- 如果邮箱置信度为 high/medium，更新 `last_verified_at`
- 合并关键词和证据片段

## 特性说明

### 本地数据库优先（Local-First）

- 默认启用 `local_first=True`
- 优先从本地数据库检索匹配的导师
- 如果数量不足，再在线搜索补充
- 显著提高运行速度，减少API调用和网络请求
- 支持增量更新，新发现的导师自动保存到数据库

### 智能域名推断

- 自动从大学名称推断域名（如 "University of Oxford" → "ox.ac.uk"）
- 支持常见大学的映射
- 支持UK大学的标准模式（firstword.ac.uk）

### UCL特殊支持

- 识别UCL的profile URL格式：`profiles.ucl.ac.uk/XXXXX-name`
- 过滤非个人页面（alumni, discover等）
- 验证URL格式（必须有数字前缀）

### 评分阈值

- **Core**: `fit_score >= 0.35`（核心匹配）
- **Adjacent**: `fit_score >= 0.20`（相邻匹配）
- 过滤低相关性结果（`fit_score < 0.15` 或无匹配关键词）

