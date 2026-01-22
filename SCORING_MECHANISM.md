# 评分机制与过滤逻辑说明 / Scoring Mechanism and Filtering Logic

## 📊 评分机制概览 / Scoring Overview

### 核心文件位置 / Key Files

1. **评分函数**: `app/modules/scoring.py`
   - `score_supervisor()`: 计算每个导师的 fit_score
   - `score_and_tier()`: 分配 Core/Adjacent 等级
   - `select_with_diversity()`: 最终选择导师

2. **配置阈值**: `app/config.py`
   - `CORE_THRESHOLD = 0.35`
   - `ADJACENT_THRESHOLD = 0.2`

3. **过滤逻辑**: `app/pipeline.py`
   - 在线搜索后的过滤（第 602-638 行）
   - 最终选择前的过滤（第 87-92 行）

---

## 🔢 评分计算方式 / Score Calculation

### `score_supervisor()` 函数 (`app/modules/scoring.py:200-329`)

**评分公式：**

```python
# 1. 核心关键词匹配 (每个 0.1 分，最高 1.0)
core_score = min(len(core_matches) * 0.1, 1.0)

# 2. 相邻关键词匹配 (每个 0.05 分，最高 0.5)
adjacent_score = min(len(adjacent_matches) * 0.05, 0.5)

# 3. 基础分数
fit_score = core_score + adjacent_score

# 4. 邮箱奖励 (+0.1)
if supervisor.email:
    fit_score += 0.1

# 5. 高置信度邮箱奖励 (+0.05)
if supervisor.email_confidence == "high":
    fit_score += 0.05

# 6. 最终分数 (最高 1.0)
fit_score = min(fit_score, 1.0)
```

**示例：**
- 匹配 3 个核心关键词 + 2 个相邻关键词 + 有邮箱 = 0.3 + 0.1 + 0.1 = **0.5**
- 匹配 5 个核心关键词 + 有邮箱 + 高置信度邮箱 = 0.5 + 0.1 + 0.05 = **0.65**

---

## 🚫 过滤机制 / Filtering Mechanisms

### 1. 在线搜索后过滤 (`app/pipeline.py:602-638`)

**过滤条件：**
```python
# 条件 1: fit_score >= 0.15 且 matched_terms > 0
# 条件 2: 或者是 PI (Principal Investigator) 且 fit_score >= 0.05

if (fit_score >= 0.15 and len(matched_terms) > 0) or (is_pi and fit_score >= 0.05):
    # 保留
else:
    # 过滤掉
```

**这意味着：**
- ❌ `fit_score < 0.15` 且不是 PI → **被过滤**
- ❌ `matched_terms == 0` 且不是 PI → **被过滤**
- ✅ `fit_score >= 0.15` 且有匹配关键词 → **保留**
- ✅ PI 且 `fit_score >= 0.05` → **保留**

### 2. 最终选择前过滤 (`app/modules/scoring.py:87-92`)

**在 `select_with_diversity()` 函数中：**

```python
filtered_profiles = [
    p for p in profiles 
    if p.fit_score > 0.15 and len(p.matched_terms) > 0
]
```

**这意味着：**
- ❌ `fit_score <= 0.15` → **被过滤**
- ❌ `matched_terms == 0` → **被过滤**

### 3. 其他过滤条件

**艺术上下文检查** (`app/modules/scoring.py:245-281`):
- 如果研究需要艺术上下文（如 "music education"），但导师没有艺术关键词 → `fit_score = 0.0` → **被过滤**

**负面关键词检查** (`app/modules/scoring.py:236-239`):
- 如果导师包含负面关键词 → `fit_score = 0.0` → **被过滤**

**Emeritus Professor 过滤** (`app/pipeline.py:721-726`):
- 所有 Emeritus Professor → **被过滤**

---

## 📉 为什么导出的数量不够？/ Why Export Count is Insufficient?

### 问题分析

**可能的原因：**

1. **过滤阈值过高** (`fit_score > 0.15`)
   - 很多导师的分数在 0.1-0.15 之间被过滤掉
   - 即使有匹配的关键词，如果分数不够高也会被排除

2. **必须有关键词匹配** (`len(matched_terms) > 0`)
   - 如果导师的关键词与用户研究不匹配，即使分数 > 0.15 也会被过滤
   - 这可能导致很多相关但关键词不完全匹配的导师被排除

3. **多样性限制** (`max_per_institution`)
   - 付费用户：每个机构最多 10 个导师
   - 如果某个机构有很多高分导师，其他机构的导师可能被排除

4. **去重后数量减少**
   - 去重可能合并了一些重复的导师记录

---

## 🔍 关键代码位置 / Key Code Locations

### 1. 评分计算
**文件**: `app/modules/scoring.py`
- **行 200-329**: `score_supervisor()` 函数
- **行 298-316**: 分数计算逻辑

### 2. 在线搜索过滤
**文件**: `app/pipeline.py`
- **行 602-638**: 在线搜索后的过滤逻辑
- **行 633**: 关键过滤条件 `fit_score >= 0.15`

### 3. 最终选择过滤
**文件**: `app/modules/scoring.py`
- **行 87-92**: `select_with_diversity()` 中的过滤
- **行 91**: 关键过滤条件 `fit_score > 0.15`

### 4. 配置阈值
**文件**: `app/config.py`
- **行 65**: `CORE_THRESHOLD = 0.35`
- **行 66**: `ADJACENT_THRESHOLD = 0.2`

---

## 📊 当前过滤阈值总结 / Current Filtering Thresholds Summary

| 位置 | 阈值 | 说明 |
|------|------|------|
| `pipeline.py:633` | `fit_score >= 0.15` | 在线搜索后过滤 |
| `scoring.py:91` | `fit_score > 0.15` | 最终选择前过滤 |
| `scoring.py:319` | `fit_score >= 0.35` | Core 等级阈值 |
| `scoring.py:321` | `fit_score >= 0.2` | Adjacent 等级阈值 |
| `validators.py:67` | `fit_score < 0.1` | 验证时拒绝（PI 除外） |
| `profile.py:205` | `fit_score < 0.1` | 提取时拒绝（PI 除外） |

---

## 💡 建议的改进方案 / Suggested Improvements

### 方案 1: 降低过滤阈值

**当前**: `fit_score > 0.15`
**建议**: `fit_score > 0.1` 或 `fit_score > 0.05`

**影响**: 会保留更多导师，但可能包含一些相关性较低的导师

### 方案 2: 放宽关键词匹配要求

**当前**: 必须 `len(matched_terms) > 0`
**建议**: 允许 `fit_score > 0.2` 的导师即使没有匹配关键词也保留

**影响**: 会保留更多导师，但可能包含一些关键词不匹配的导师

### 方案 3: 动态调整阈值

**根据找到的导师数量动态调整**:
- 如果找到的导师 < target，降低阈值
- 如果找到的导师 >= target，保持当前阈值

**影响**: 确保尽可能达到目标数量，同时保持质量

### 方案 4: 显示过滤统计

**添加日志显示**:
- 有多少导师因为 `fit_score < 0.15` 被过滤
- 有多少导师因为 `matched_terms == 0` 被过滤
- 平均分数分布

**影响**: 帮助理解为什么数量不够

---

## 🔧 如何调整阈值 / How to Adjust Thresholds

### 方法 1: 修改配置文件

**文件**: `app/config.py`

```python
# 当前值
CORE_THRESHOLD = 0.35
ADJACENT_THRESHOLD = 0.2

# 建议值（更宽松）
CORE_THRESHOLD = 0.25  # 降低 Core 阈值
ADJACENT_THRESHOLD = 0.15  # 降低 Adjacent 阈值
```

### 方法 2: 修改过滤条件

**文件**: `app/pipeline.py` (行 633)

```python
# 当前
if (fit_score >= 0.15 and len(matched_terms) > 0) or (is_pi and fit_score >= 0.05):

# 建议（更宽松）
if (fit_score >= 0.1 and len(matched_terms) > 0) or (is_pi and fit_score >= 0.05):
# 或者
if fit_score >= 0.1 or (is_pi and fit_score >= 0.05):  # 移除 matched_terms 要求
```

**文件**: `app/modules/scoring.py` (行 91)

```python
# 当前
if p.fit_score > 0.15 and len(p.matched_terms) > 0

# 建议（更宽松）
if p.fit_score > 0.1 and len(p.matched_terms) > 0
# 或者
if p.fit_score > 0.1  # 移除 matched_terms 要求
```

---

## 📈 分数分布示例 / Score Distribution Examples

### 典型分数分布

假设找到 100 个导师，分数分布可能是：

| 分数范围 | 数量 | 是否保留 (当前) | 是否保留 (建议) |
|---------|------|----------------|----------------|
| 0.5 - 1.0 | 20 | ✅ 保留 | ✅ 保留 |
| 0.35 - 0.5 | 15 | ✅ 保留 | ✅ 保留 |
| 0.2 - 0.35 | 25 | ✅ 保留 | ✅ 保留 |
| 0.15 - 0.2 | 20 | ✅ 保留 | ✅ 保留 |
| 0.1 - 0.15 | 15 | ❌ 过滤 | ✅ 保留 |
| 0.05 - 0.1 | 5 | ❌ 过滤 | ✅ 保留 (如果降低阈值) |

**当前设置**: 保留 80 个导师
**如果降低到 0.1**: 保留 100 个导师

---

## 🎯 推荐调整 / Recommended Adjustments

基于您的问题（导出的数量不够），建议：

1. **降低在线搜索过滤阈值**: `0.15` → `0.1`
2. **降低最终选择过滤阈值**: `0.15` → `0.1`
3. **可选**: 移除 `matched_terms > 0` 要求（如果分数足够高）

这样可以保留更多导师，同时仍然过滤掉完全不相关的导师。

---

**最后更新 / Last Updated:** 2024

