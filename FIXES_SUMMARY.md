# SuperFinder 修复总结

## 修复的问题

修复了以下核心问题：
1. **目录页解析漏抓**：HKU 的 `/faculty-academics/` 路径未被识别
2. **个人页被误判为目录页**：导致很多真实个人主页未被处理
3. **Email 验证过严**：因为 email 缺失（如 JS 保护）就丢弃整条记录
4. **缺少丢弃原因统计**：无法定位到底卡在哪一步

## 修改的文件

### 1. `app/modules/directory.py`

#### 新增功能：
- **扩展 URL pattern allowlist**：
  - 添加了 `/faculty-academics/[a-z0-9_-]+/?$` 模式（HKU Faculty of Education）
  - 兼容分页路径（如 `/faculty-academics/a-c`）会被排除

- **新增 `looks_like_profile_url()` 函数**：
  - 更宽松的 URL 检查，支持域名可配置的路径
  - 专门处理 `/faculty-academics/` 路径

- **新增 `is_directory_like_page()` 函数**：
  - 判断页面是目录页还是个人页
  - 目录页特征：包含 >= 8 个 profile-like 链接
  - 个人页特征：h1/og:title 像人名 + 包含 Biography/Research/Publications 等段落
  - 阈值可配置（`DIRECTORY_MIN_PROFILE_LINKS`, `DIRECTORY_CONSERVATIVE_THRESHOLD`）

#### 修改的方法：
- `extract_profile_urls()`: 使用 `looks_like_profile_url()` 替代 `_is_profile_url()`
- `_is_profile_url()`: 现在作为 `looks_like_profile_url()` 的别名（向后兼容）

### 2. `app/modules/validators.py`

#### 修改：
- **`validate_profile()` 返回值改为 `Tuple[bool, str]`**：
  - 返回 `(is_valid, reason)` 而不是简单的 `bool`
  - `reason` 为空字符串表示验证通过，否则为失败原因

- **Email 不再是必填字段**：
  - 必须字段：`name`、`institution`、`source_url`
  - `email` 可以为空；如果存在则必须格式正确
  - `profile_url` 可选，但如果存在必须格式正确

- **失败原因枚举**：
  - `no_name_or_too_short`
  - `no_institution`
  - `no_source_url`
  - `invalid_email_format`
  - `invalid_profile_url_format`
  - `very_low_fit_score`

### 3. `app/pipeline.py`

#### 新增功能：
- **页面类型判别**：
  - 在处理目录候选 URL 时，先判断是目录页还是个人页
  - 如果是个人页，直接加入 `profile_urls` 队列，不进行目录解析
  - 日志中显示重新分类的 URL

- **丢弃原因统计**：
  - 为每个 URL 记录最终状态：`saved` / `dropped`
  - 记录 `dropped_reason`（枚举：`domain_mismatch`, `validate_failed`, `text_too_short`, `not_a_person`, `fetch_failed`, `extraction_failed`, `other`）
  - 在 debug 日志中打印前 30 个被丢弃的 URL + 原因
  - Pipeline 最后打印汇总表：
    - `profile_pages_total`
    - `crawled_ok`
    - `reclassified_as_profile`
    - `extracted_ok`
    - `saved_db`
    - `dropped_*` 各原因计数

#### 修改的方法：
- `process_university()`: 
  - 返回类型改为 `Tuple[List[SupervisorProfile], Dict]`
  - 返回统计信息字典
  - 添加页面类型判别逻辑
  - 添加详细的丢弃原因跟踪

- `run_pipeline()`:
  - 更新 `validate_profile()` 调用（现在返回 tuple）
  - 添加统计信息收集和汇总打印

### 4. `app/config.py`

#### 新增配置项：
```python
# Directory page detection thresholds
DIRECTORY_MIN_PROFILE_LINKS = int(os.getenv("DIRECTORY_MIN_PROFILE_LINKS", "8"))
DIRECTORY_CONSERVATIVE_THRESHOLD = int(os.getenv("DIRECTORY_CONSERVATIVE_THRESHOLD", "5"))
```

可通过环境变量配置：
- `DIRECTORY_MIN_PROFILE_LINKS`: 判断为目录页的最小 profile 链接数（默认 8）
- `DIRECTORY_CONSERVATIVE_THRESHOLD`: 保守判断阈值（默认 5）

## 关键改进

### 【A】目录页解析漏抓修复
- ✅ 扩展了 URL pattern，支持 `/faculty-academics/` 路径
- ✅ 添加了 `looks_like_profile_url()` 函数，更灵活地识别个人主页
- ✅ 在目录解析中优先提取"疑似个人页"的链接

### 【B】避免把个人页当目录页
- ✅ 添加了 `is_directory_like_page()` 函数进行页面类型判别
- ✅ 如果目录候选 URL 被判定为个人页，直接加入 `profile_pages` 队列
- ✅ 日志中显示重新分类的 URL（便于 debug）

### 【C】放宽验证策略
- ✅ Email 不再是必填字段
- ✅ 必须字段：`name`、`institution`、`source_url`
- ✅ Email 可以为空，`email_confidence` 自动标记为 `none`

### 【D】丢弃原因统计
- ✅ 每个 URL 记录最终状态和丢弃原因
- ✅ Pipeline 最后打印汇总表
- ✅ Debug 日志显示前 30 个被丢弃的 URL + 原因

### 【E】最小改动原则
- ✅ 只修改了 `directory.py`、`validators.py`、`pipeline.py`、`config.py`
- ✅ 保持现有接口和数据结构（`SupervisorProfile`, `ResearchProfile`）不变
- ✅ 向后兼容：`_is_profile_url()` 作为 `looks_like_profile_url()` 的别名

## 测试建议

### 最小可复现测试

使用 HKU 域名测试：

```python
# 测试 URL 示例
test_urls = [
    "https://web.edu.hku.hk/about-the-faculty/people",
    "https://web.edu.hku.hk/faculty-academics/john-smith",  # 个人页示例
    "https://web.edu.hku.hk/faculty-academics/a-c",  # 分页（应被排除）
]
```

### 预期改进

**修改前**：
- Found 20 directory pages / Found 41 researcher profile pages
- Extracted 1~2 个 profile URLs
- 很多真实个人主页未被识别

**修改后**：
- ✅ `/faculty-academics/` 路径被正确识别
- ✅ 个人页不会被误判为目录页
- ✅ Email 缺失不会导致整条记录被丢弃
- ✅ 可以看到详细的丢弃原因统计

## 配置说明

新增的配置项可以通过环境变量设置（在 `.env` 文件中）：

```bash
# Directory page detection thresholds
DIRECTORY_MIN_PROFILE_LINKS=8      # 判断为目录页的最小 profile 链接数
DIRECTORY_CONSERVATIVE_THRESHOLD=5  # 保守判断阈值
```

## 注意事项

1. **向后兼容**：所有修改都保持了向后兼容性，不会破坏现有功能
2. **日志增强**：现在可以看到更详细的处理过程和丢弃原因
3. **性能影响**：页面类型判别会增加少量计算，但影响很小
4. **Email 处理**：Email 为空时，`email_confidence` 会自动设置为 `"none"`，符合预期

## 下一步

建议在实际运行中观察：
1. `Extracted profile URLs` 数量是否提升
2. 丢弃原因统计中哪些原因最常见
3. 是否需要进一步调整阈值或模式

