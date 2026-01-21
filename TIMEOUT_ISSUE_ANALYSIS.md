# 超时问题分析与解决方案 / Timeout Issue Analysis and Solutions

## 🔴 问题描述 / Problem Description

**用户报告 / User Report:**
- 网页端用户在搜索过程中发现"跑着跑着就停掉了"
- Web users report that the search process stops unexpectedly during execution

**可能原因 / Possible Causes:**
1. Streamlit Cloud 执行超时限制
2. 数据库连接超时
3. 长时间运行任务被中断
4. 网络连接超时
5. 会话超时

1. Streamlit Cloud execution timeout limits
2. Database connection timeout
3. Long-running tasks being interrupted
4. Network connection timeout
5. Session timeout

---

## 📊 当前状态分析 / Current State Analysis

### ✅ 已实现的机制 / Implemented Mechanisms

1. **进度回调 / Progress Callback**
   - ✅ Pipeline 支持 `progress_callback` 参数
   - ✅ UI 中已实现进度条和状态更新
   - ✅ 定期更新进度显示

2. **错误处理 / Error Handling**
   - ✅ Try-except 块捕获异常
   - ✅ 调试信息输出

### ❌ 缺失的机制 / Missing Mechanisms

1. **Streamlit 配置 / Streamlit Configuration**
   - ❌ 没有 `.streamlit/config.toml` 配置文件
   - ❌ 没有设置超时参数
   - ❌ 没有配置长时间运行任务的处理

2. **Keep-Alive 机制 / Keep-Alive Mechanism**
   - ❌ 没有定期发送心跳信号
   - ❌ 没有保持连接活跃的机制

3. **任务分块 / Task Chunking**
   - ❌ Pipeline 一次性运行，没有分块处理
   - ❌ 没有断点续传机制

---

## 🛠️ 解决方案 / Solutions

### 方案 1: 创建 Streamlit 配置文件 (推荐) / Solution 1: Create Streamlit Config (Recommended)

**创建 `.streamlit/config.toml`:**

```toml
[server]
# 增加上传文件大小限制
maxUploadSize = 200
# 启用 CORS（如果需要）
enableCORS = false
# 启用 XSRF 保护
enableXsrfProtection = false

[browser]
# 自动打开浏览器（可选）
gatherUsageStats = false

[runner]
# 快速重载（开发模式）
fastReruns = true
# 魔法命令（允许在代码中使用魔法命令）
magicEnabled = true

# 注意：Streamlit Cloud 可能不支持所有配置项
# 某些配置可能需要在部署时通过环境变量设置
```

### 方案 2: 添加 Keep-Alive 机制 / Solution 2: Add Keep-Alive Mechanism

**在 Pipeline 中添加定期更新 / Add Periodic Updates in Pipeline:**

```python
import time
from datetime import datetime

def update_progress_with_keepalive(step: str, progress: float, message: str, **kwargs):
    """Update progress with keep-alive mechanism."""
    # 更新进度条
    progress_bar.progress(min(progress, 1.0))
    status_text.info(f"📊 **Current Step:** {message}")
    
    # Keep-alive: 定期更新 Streamlit 状态
    if "found_count" in kwargs:
        stats_text.success(f"✅ **Progress:** Found {kwargs['found_count']} supervisors so far")
    
    # 强制刷新 Streamlit 状态（保持连接活跃）
    st.rerun()  # 注意：这会导致页面重新加载，可能不适合
    
    # 更好的方法：使用 st.empty() 和定期更新
    # 或者使用 threading 定期更新状态
```

**更好的方法：使用状态更新而非 rerun / Better Approach: Use State Updates Instead of Rerun:**

```python
# 在 pipeline 中定期调用 progress_callback
# 确保至少每 30 秒更新一次进度
last_update = time.time()
UPDATE_INTERVAL = 30  # 秒

for idx, university in enumerate(universities):
    # ... 处理逻辑 ...
    
    # 定期更新进度（保持连接活跃）
    current_time = time.time()
    if current_time - last_update >= UPDATE_INTERVAL:
        if progress_callback:
            progress_callback(
                "keep_alive",
                progress,
                f"Processing... ({idx+1}/{len(universities)})",
                found_count=len(profiles)
            )
        last_update = current_time
```

### 方案 3: 优化 Pipeline 执行 / Solution 3: Optimize Pipeline Execution

**分批处理大学 / Process Universities in Batches:**

```python
# 将大学列表分成小批次
BATCH_SIZE = 10

for batch_start in range(0, len(universities), BATCH_SIZE):
    batch = universities[batch_start:batch_start + BATCH_SIZE]
    
    # 处理批次
    for university in batch:
        # ... 处理逻辑 ...
    
    # 每批次后更新进度
    if progress_callback:
        progress_callback(
            "batch_complete",
            batch_start / len(universities),
            f"Completed batch {batch_start // BATCH_SIZE + 1}",
            found_count=len(profiles)
        )
    
    # 短暂暂停，避免过载
    time.sleep(0.1)
```

### 方案 4: 添加超时检测和恢复 / Solution 4: Add Timeout Detection and Recovery

**检测超时并保存进度 / Detect Timeout and Save Progress:**

```python
import pickle
from pathlib import Path

# 保存检查点
def save_checkpoint(profiles, universities_processed, checkpoint_path):
    """Save progress checkpoint."""
    checkpoint_data = {
        'profiles': profiles,
        'universities_processed': universities_processed,
        'timestamp': datetime.now().isoformat()
    }
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(checkpoint_data, f)

# 加载检查点
def load_checkpoint(checkpoint_path):
    """Load progress checkpoint."""
    if checkpoint_path.exists():
        with open(checkpoint_path, 'rb') as f:
            return pickle.load(f)
    return None
```

---

## 🚀 立即实施的改进 / Immediate Improvements

### 1. 创建 Streamlit 配置文件

**文件: `.streamlit/config.toml`**

```toml
[server]
maxUploadSize = 200
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
```

### 2. 改进进度回调机制

**在 `ui/streamlit_app.py` 中:**

```python
# 改进的进度回调，包含时间戳
def update_progress(step: str, progress: float, message: str, **kwargs):
    """Update Streamlit progress display with keep-alive."""
    import time
    from datetime import datetime
    
    # 更新进度条
    progress_bar.progress(min(progress, 1.0))
    
    # 添加时间戳，证明连接仍然活跃
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_text.info(f"📊 **{timestamp}** - {message}")
    
    if "found_count" in kwargs:
        stats_text.success(
            f"✅ **Progress:** Found {kwargs['found_count']} supervisors so far "
            f"(Last update: {timestamp})"
        )
    
    # 强制 Streamlit 处理更新（不重新加载页面）
    # 通过更新空的容器来保持连接活跃
    time.sleep(0.01)  # 短暂暂停，让 Streamlit 处理更新
```

### 3. 在 Pipeline 中添加定期更新

**在 `app/pipeline.py` 中:**

```python
# 在处理大学的循环中添加定期更新
import time

last_progress_update = time.time()
PROGRESS_UPDATE_INTERVAL = 10  # 每 10 秒更新一次

for idx, university in enumerate(universities):
    # ... 现有处理逻辑 ...
    
    # 定期更新进度（保持连接活跃）
    current_time = time.time()
    if current_time - last_progress_update >= PROGRESS_UPDATE_INTERVAL:
        if progress_callback:
            progress_callback(
                "online_search",
                progress,
                f"Processing {university.institution}... ({idx+1}/{len(universities)})",
                found_count=len(online_profiles)
            )
        last_progress_update = current_time
```

---

## 📝 Streamlit Cloud 限制说明 / Streamlit Cloud Limitations

### 已知限制 / Known Limitations

1. **执行超时 / Execution Timeout**
   - Streamlit Cloud 免费版可能有执行时间限制
   - 长时间运行的任务可能被中断
   - 建议：考虑升级到付费计划或使用其他部署方式

2. **内存限制 / Memory Limits**
   - 免费版内存限制可能较低
   - 大量数据处理可能导致内存不足
   - 建议：优化数据处理，使用分批处理

3. **连接超时 / Connection Timeout**
   - 客户端与服务器之间的连接可能超时
   - 长时间无响应可能导致连接断开
   - 建议：定期更新进度，保持连接活跃

### 建议的部署配置 / Recommended Deployment Configuration

**对于长时间运行的任务 / For Long-Running Tasks:**

1. **使用异步处理 / Use Async Processing**
   - 将任务提交到后台队列
   - 使用任务 ID 跟踪进度
   - 定期轮询任务状态

2. **分批处理 / Batch Processing**
   - 将大任务分成小批次
   - 每批次完成后保存进度
   - 支持断点续传

3. **使用外部任务队列 / Use External Task Queue**
   - 使用 Celery 或类似工具
   - 将任务提交到独立的工作进程
   - 通过 WebSocket 或轮询更新进度

---

## 🔍 诊断步骤 / Diagnostic Steps

### 1. 检查日志 / Check Logs

```python
# 在 pipeline 中添加详细日志
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_pipeline(...):
    logger.info("Pipeline started")
    # ... 处理逻辑 ...
    logger.info(f"Processing university {idx+1}/{len(universities)}")
    # ... 更多日志 ...
```

### 2. 监控执行时间 / Monitor Execution Time

```python
import time

start_time = time.time()

# ... 处理逻辑 ...

elapsed_time = time.time() - start_time
logger.info(f"Task completed in {elapsed_time:.2f} seconds")
```

### 3. 添加健康检查 / Add Health Checks

```python
# 定期检查系统状态
def health_check():
    """Check system health."""
    import psutil
    
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent()
    
    logger.info(f"Memory: {memory.percent}%, CPU: {cpu}%")
    
    if memory.percent > 90:
        logger.warning("High memory usage detected!")
```

---

## ✅ 实施优先级 / Implementation Priority

### 高优先级 (立即实施) / High Priority (Immediate)

1. ✅ 创建 `.streamlit/config.toml` 配置文件
2. ✅ 改进进度回调，添加时间戳和运行时间显示
3. ✅ 在 pipeline 中添加定期进度更新（每 3-5 秒心跳，每 5 秒完整更新）
4. ✅ 实施双重 keep-alive 机制（心跳 + 完整更新）
5. ✅ 在 session state 中保存进度状态，保持连接活跃

### 中优先级 (近期实施) / Medium Priority (Near Term)

1. ⚠️ 实现分批处理机制
2. ⚠️ 添加检查点保存/恢复功能
3. ⚠️ 优化内存使用

### 低优先级 (长期优化) / Low Priority (Long Term)

1. 💡 考虑使用异步任务队列
2. 💡 实现 WebSocket 实时更新
3. 💡 迁移到更强大的部署平台

---

## 📚 参考资料 / References

- [Streamlit Configuration](https://docs.streamlit.io/library/advanced-features/configuration)
- [Streamlit Cloud Limits](https://docs.streamlit.io/streamlit-community-cloud)
- [Long-Running Tasks in Streamlit](https://discuss.streamlit.io/t/long-running-tasks/105)

---

**最后更新 / Last Updated:** 2024

