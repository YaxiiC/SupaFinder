# 国家筛选功能说明

## 功能概述

现在支持按国家筛选大学和导师，可以指定一个或多个国家（如新加坡、瑞典等）。

## 使用方法

### 1. 命令行方式

使用 `--countries` 参数，多个国家用逗号分隔：

```bash
# 筛选单个国家
python -m app.main \
  --cv data/cv.pdf \
  --keywords "machine learning" \
  --universities data/universities.xlsx \
  --countries "Singapore"

# 筛选多个国家
python -m app.main \
  --cv data/cv.pdf \
  --keywords "AI" \
  --universities data/universities.xlsx \
  --countries "Singapore,Sweden,United Kingdom"

# 组合筛选：国家 + QS 排名
python -m app.main \
  --cv data/cv.pdf \
  --keywords "AI" \
  --universities data/universities.xlsx \
  --countries "Singapore,Sweden" \
  --qs_max 100

# 组合筛选：国家 + 地区
python -m app.main \
  --cv data/cv.pdf \
  --keywords "AI" \
  --universities data/universities.xlsx \
  --countries "United Kingdom" \
  --regions "Europe"
```

### 2. Streamlit UI

在 Streamlit 界面中：

1. 打开 `ui/streamlit_app.py`
2. 在 "Filters" 部分找到 "Countries" 输入框
3. 输入国家名称，多个国家用逗号分隔，例如：
   - `Singapore,Sweden`
   - `United Kingdom,Germany,France`

### 3. 筛选顺序

筛选按以下顺序执行：
1. **地区筛选**（如果指定）
2. **国家筛选**（如果指定）
3. **QS 排名筛选**（如果指定）

筛选是累积的，例如：
- 先按地区筛选 → 再按国家筛选 → 最后按 QS 排名筛选

## 国家名称格式

国家名称应该与 Excel 文件中的 `country` 列完全匹配（不区分大小写）。

常见国家名称示例：
- `Singapore`
- `Sweden`
- `United Kingdom`
- `United States`
- `Germany`
- `France`
- `Canada`
- `Australia`

**注意**：确保 Excel 文件中的 `country` 列使用一致的国家名称格式。

## 代码修改位置

### 1. `app/pipeline.py`
- `run_pipeline()` 函数添加 `countries` 参数
- 添加国家筛选逻辑
- 在本地数据库查询时传递国家筛选条件

### 2. `app/main.py`
- 添加 `--countries` 命令行参数
- 解析逗号分隔的国家列表

### 3. `ui/streamlit_app.py`
- 添加 "Countries" 输入框
- 解析并传递国家筛选条件

### 4. `app/modules/local_repo.py`
- `query_candidates()` 函数支持 `countries` 列表筛选
- 保持向后兼容（仍支持单个 `country`）

## 示例输出

运行时会看到类似输出：

```
Loading inputs...
  Filtered by country ['Singapore', 'Sweden']: 200 -> 15 universities
  Final: 15 universities (from 200 total)
```

## 注意事项

1. **国家名称匹配**：国家名称必须与 Excel 文件中的 `country` 列完全匹配（不区分大小写）
2. **组合筛选**：可以同时使用地区、国家和 QS 排名筛选
3. **本地数据库**：国家筛选也会应用到本地数据库查询
4. **空值处理**：如果某个大学的 `country` 字段为空，它不会被包含在国家筛选结果中

## 故障排除

### 问题：筛选后没有结果

**可能原因**：
1. 国家名称不匹配（检查 Excel 文件中的实际国家名称）
2. 大小写问题（已自动处理，不区分大小写）
3. Excel 文件中的 `country` 列为空

**解决方法**：
- 检查 Excel 文件中的 `country` 列
- 确保国家名称与 Excel 中的完全一致
- 使用 `--regions` 作为替代方案（如果地区信息更准确）

### 问题：某些国家没有被筛选

**可能原因**：
- 国家名称格式不一致（例如 "UK" vs "United Kingdom"）

**解决方法**：
- 统一 Excel 文件中的国家名称格式
- 使用完整国家名称（如 "United Kingdom" 而不是 "UK"）

