# 姓名和职称过滤改进

## 问题描述

1. **错误识别为姓名**：某些内容（如 "Taught Masters Mechanical Engineering， Manchester Hydrodynamics Lab"）被错误识别为姓名
2. **缺少职称检查**：没有职称（prof, dr, professor, reader, lecturer, research fellow等）的页面应该被排除
3. **PI 保存问题**：低相关性但有效的 PI（Principal Investigator）应该仍然保存到数据库

## 改进内容

### 1. 增强姓名过滤 (`profile.py`)

**修改了 `_looks_like_name()` 方法**：

#### 新增过滤规则：

1. **学术/课程名称过滤**：
   - 过滤包含以下术语的内容：
     - `taught`, `masters`, `bachelor`, `beng`, `meng`, `msc`, `phd`
     - `mechanical engineering`, `electronic engineering`, `civil engineering`
     - `hydrodynamics`, `lab`, `laboratory`
     - `studentship`, `studentships`, `student support`
     - `accessibility`, `links`, `general engineering`
     - `integrated`, `comfort`, `engineering`, `mediacom`, `support`
     - `fellowship`, `fellowships`, `scholarship`, `scholarships`

2. **逗号检查**：
   - 如果包含 2 个或更多逗号，可能是列表或描述，不是姓名

3. **学术短语过滤**：
   - 过滤包含以下完整短语的内容：
     - "mechanical engineering"
     - "electronic engineering"
     - "general engineering"
     - "student support"
     - "phd studentship"
     - "accessibility links"
     - "integrated comfort engineering"
     - "hydrodynamics lab"

**示例**：
- ❌ "Taught Masters Mechanical Engineering" → 被过滤
- ❌ "Manchester Hydrodynamics Lab" → 被过滤
- ❌ "PhD Studentship" → 被过滤
- ✅ "John Smith" → 通过
- ✅ "Dr. Jane Doe" → 通过

### 2. 职称要求检查 (`profile.py`)

**新增职称检查逻辑**：

#### 要求的职称模式：
- `prof`, `professor`
- `dr`, `doctor`
- `reader`
- `lecturer`, `senior lecturer`
- `research fellow`, `senior research fellow`
- `principal investigator`, `pi`
- `group leader`
- `lab head`, `lab director`
- `director`
- `head of`

#### 检查逻辑：

1. **检查页面是否包含学术职称**
2. **如果没有职称，检查是否是 PI（Principal Investigator）**
3. **如果是 profile URL（如 `profiles.ucl.ac.uk`），更宽松（可能标题在结构化数据中）**
4. **如果既没有职称也不是 PI，且不是 profile URL，则拒绝**

**示例**：
- ❌ 页面只有 "John Smith" 但没有职称 → 被拒绝（除非是 profile URL）
- ✅ 页面有 "Prof. John Smith" → 通过
- ✅ 页面有 "Principal Investigator" → 通过（即使没有其他职称）
- ✅ `profiles.ucl.ac.uk/xxx` URL → 更宽松，允许通过

### 3. PI 特殊处理

**PI（Principal Investigator）识别**：

#### PI 标识符：
- `principal investigator`
- `pi`
- `group leader`
- `lab head`
- `lab director`
- `research group leader`

#### 特殊处理：

1. **提取阶段**：
   - PI 即使没有其他职称也允许通过
   - PI 即使 `fit_score < 0.1` 也允许通过（但至少需要 `>= 0.05`）

2. **验证阶段** (`validators.py`)：
   - PI 即使 `fit_score < 0.1` 也允许通过验证

3. **Pipeline 过滤阶段** (`pipeline.py`)：
   - PI 即使 `fit_score < 0.15` 也允许保存（但至少需要 `>= 0.05`）
   - 日志中会显示：`Including PI {name} despite low score`

4. **标记**：
   - 如果检测到 PI，会在 `notes` 字段中添加 "Principal Investigator/Group Leader"

**示例**：
- ✅ PI with `fit_score = 0.08` → 保存到数据库
- ✅ PI with `fit_score = 0.12` → 保存到数据库
- ❌ 非 PI with `fit_score = 0.08` → 被过滤

## 代码修改位置

### `app/modules/profile.py`

1. **`_looks_like_name()` 方法**：
   - 添加学术术语过滤
   - 添加逗号检查
   - 添加学术短语过滤

2. **`extract()` 方法**：
   - 添加职称检查逻辑
   - 添加 PI 识别
   - 在 notes 中标记 PI 状态

### `app/modules/validators.py`

- **`validate_profile()` 方法**：
  - 检查 PI 状态
  - PI 即使 `fit_score < 0.1` 也允许通过

### `app/pipeline.py`

- **在线 profile 过滤逻辑**：
  - 检查 PI 状态
  - PI 即使 `fit_score < 0.15` 也允许保存（但至少需要 `>= 0.05`）

## 测试建议

### 测试姓名过滤

```python
# 这些应该被拒绝
test_cases = [
    "Taught Masters Mechanical Engineering",
    "Manchester Hydrodynamics Lab",
    "Student Support",
    "PhD Studentship",
    "Mechanical Engineering, Electronic Engineering BEng",
    "Accessibility Links",
    "General Engineering BEng",
    "ICE Integrated Comfort Engineering",
    "Mediacom"
]

# 这些应该通过
valid_names = [
    "John Smith",
    "Dr. Jane Doe",
    "Professor Mary Johnson"
]
```

### 测试职称检查

```python
# 这些应该被拒绝（没有职称）
no_title_pages = [
    "Page with only name, no title",
    "Student page without title"
]

# 这些应该通过
valid_pages = [
    "Prof. John Smith",
    "Dr. Jane Doe",
    "Principal Investigator John Smith",  # PI
    "Group Leader Mary Johnson"  # PI
]
```

### 测试 PI 保存

```python
# PI with low fit_score should be saved
pi_profile = SupervisorProfile(
    name="John Smith",
    fit_score=0.08,  # Low but valid
    notes="Principal Investigator",
    keywords=["research", "group leader"]
)
# Should pass validation and be saved
```

## 预期效果

### 改进前：
- ❌ "Taught Masters Mechanical Engineering" 被识别为姓名
- ❌ 没有职称的页面被保存
- ❌ 低相关性但有效的 PI 被过滤

### 改进后：
- ✅ 学术/课程名称被正确过滤
- ✅ 没有职称的页面被拒绝（除非是 PI 或 profile URL）
- ✅ 低相关性但有效的 PI 被保存到数据库

## 日志输出

运行 pipeline 时，会看到：

```
Including PI John Smith (University of X) despite low score (score=0.08)
```

这表明 PI 即使相关性较低也被保存了。

## 配置

目前没有新增配置项，所有阈值都是硬编码的：
- 职称检查：必需（除非是 PI 或 profile URL）
- PI fit_score 最低阈值：0.05
- 非 PI fit_score 最低阈值：0.15（pipeline 过滤）或 0.1（验证）

如果需要调整，可以修改代码中的阈值。

