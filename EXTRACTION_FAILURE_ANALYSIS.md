# Extraction Failure 分析改进

## 问题描述

之前很多 URL 被标记为 `extraction_failed`，但无法知道具体失败原因，导致难以诊断和修复问题。

## 改进内容

### 1. 详细的失败原因追踪 (`profile.py`)

`extract()` 方法现在返回 `Tuple[Optional[SupervisorProfile], Optional[str]]`：
- 成功时：`(profile, None)`
- 失败时：`(None, detailed_reason)`

#### 失败原因分类：

1. **`domain_mismatch`**
   - URL 域名与大学域名不匹配
   - 例如：UCL 的 profile 被分配给其他大学

2. **`no_name (h1=..., title=..., og_title=..., text_len=...)`**
   - 无法提取姓名
   - 包含诊断信息：是否有 H1、title、og:title，文本长度

3. **`invalid_name (extracted='...')`**
   - 提取到的名称无效（可能是 URL 或其他非名称内容）
   - 显示实际提取到的内容

4. **`student_postdoc`**
   - 明确是学生/博士后职位

5. **`negative_keyword`**
   - 包含负面关键词

6. **`very_low_fit_score_X.XX`**
   - 匹配度极低（< 0.1）

### 2. 改进的错误处理 (`pipeline.py`)

- 使用详细的失败原因替代通用的 `extraction_failed`
- 统计分类更细：
  - `extraction_failed: no_name`
  - `extraction_failed: invalid_name`
  - `extraction_failed: student_postdoc`
  - `extraction_failed: negative_keyword`
  - `extraction_failed: very_low_fit_score`
  - `extraction_failed` (其他原因)

### 3. 诊断工具 (`scripts/diagnose_extraction_failures.py`)

新增诊断脚本，可以单独测试 URL 并查看详细的失败原因：

```bash
python scripts/diagnose_extraction_failures.py \
  'https://profiles.ucl.ac.uk/94114-natalie-wint' \
  'ucl.ac.uk' \
  'University College London'
```

脚本会显示：
- HTTP 状态码
- 文本内容长度
- HTML 结构分析（H1、title、og:title、email 等）
- 提取尝试和详细失败原因
- 改进建议

## 常见失败原因分析

### 1. `text_too_short`

**原因**：页面文本内容太少（< 20 字符，profile URL < 10 字符）

**可能的情况**：
- 页面是重定向
- 页面需要 JavaScript 渲染
- 页面结构特殊，文本提取失败

**改进**：
- 已降低阈值（普通页面 20，profile URL 10）
- 对于 profile URL，即使文本短也尝试从 HTML 提取

### 2. `extraction_failed: no_name`

**原因**：无法从页面提取姓名

**可能的情况**：
- 页面不是个人主页（可能是目录页、部门页等）
- 页面结构特殊，姓名不在常见位置（H1、title、og:title）
- 页面需要 JavaScript 渲染才能显示内容

**诊断信息**：
- `h1=True/False` - 是否有 H1 标签
- `title=True/False` - 是否有 title 标签
- `og_title=True/False` - 是否有 og:title meta
- `text_len=XXX` - 文本长度

**建议**：
- 检查 URL 是否真的是个人主页
- 如果页面需要 JS，考虑使用 Playwright 渲染
- 检查页面是否有特殊结构需要特殊处理

### 3. `extraction_failed: invalid_name`

**原因**：提取到的"姓名"实际上是 URL 或其他无效内容

**可能的情况**：
- 页面结构混乱，提取到了错误的内容
- 页面是搜索结果页或列表页

**诊断信息**：
- 显示实际提取到的内容（前 50 字符）

### 4. `extraction_failed: ucl_profile_no_data`

**原因**：UCL profile 页面没有足够的数据

**可能的情况**：
- Profile 页面存在但内容为空
- 需要登录才能查看
- 页面结构变化

**建议**：
- 检查是否需要特殊处理 UCL profiles
- 考虑从其他数据源补充信息

## 使用诊断工具

### 测试单个 URL

```bash
cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder
source .venv/bin/activate

python scripts/diagnose_extraction_failures.py \
  'https://profiles.ucl.ac.uk/94114-natalie-wint' \
  'ucl.ac.uk' \
  'University College London'
```

### 批量分析失败 URL

可以从日志中提取失败的 URL，然后批量测试：

```bash
# 从日志中提取失败的 URL（示例）
grep "Dropped.*extraction_failed" your_log.txt | \
  awk '{print $2}' | \
  while read url; do
    python scripts/diagnose_extraction_failures.py "$url" "ucl.ac.uk" "UCL"
  done
```

## 下一步改进建议

1. **JavaScript 渲染支持**
   - 对于需要 JS 的页面，使用 Playwright 渲染
   - 已在 `requirements.txt` 中注释了 `playwright`

2. **特殊页面处理**
   - 为 UCL profiles 添加特殊处理逻辑
   - 为其他常见大学添加特殊处理

3. **重试机制**
   - 对于 `text_too_short`，可以尝试不同的文本提取方法
   - 对于 `no_name`，可以尝试更宽松的姓名提取策略

4. **日志增强**
   - 保存失败 URL 和原因到文件
   - 定期分析失败模式

## 配置选项

可以在 `.env` 中调整阈值：

```bash
# 文本提取阈值
MIN_TEXT_LENGTH_FOR_EXTRACTION=20      # 普通页面最小文本长度
MIN_TEXT_LENGTH_FOR_PROFILE_URL=10     # Profile URL 最小文本长度
```

## 统计报告

运行 pipeline 后，会看到详细的失败原因统计：

```
Pipeline Statistics Summary:
  Profile pages total: 200
  Crawled OK: 195
  Reclassified as profile: 5
  Extracted OK: 120
  Saved to DB: 115
  Dropped reasons:
    - text_too_short: 10
    - extraction_failed: no_name: 30
    - extraction_failed: invalid_name: 5
    - extraction_failed: student_postdoc: 3
    - extraction_failed: very_low_fit_score: 2
    - validate_failed: 5
```

这样可以清楚地看到哪些原因导致最多失败，便于针对性改进。

