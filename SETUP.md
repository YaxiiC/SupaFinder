# SuperFinder 环境设置指南

## 快速开始

### 1. 激活虚拟环境

项目已经有一个虚拟环境（`.venv`），直接激活即可：

```bash
# 进入项目目录
cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder

# 激活虚拟环境（macOS/Linux）
source .venv/bin/activate

# 或者如果使用 fish shell
source .venv/bin/activate.fish

# Windows 用户使用
# .venv\Scripts\activate
```

激活成功后，命令行提示符前面会显示 `(.venv)`。

### 2. 安装/更新依赖

如果虚拟环境是新创建的，或者需要更新依赖：

```bash
# 确保在虚拟环境中
pip install -r requirements.txt
```

### 3. 配置环境变量

项目已经有 `.env` 文件，如果还没有，可以复制示例文件：

```bash
# 如果 .env 不存在，从示例文件创建
cp env.example .env
```

然后编辑 `.env` 文件，填入你的 API 密钥：
- `DEEPSEEK_API_KEY`: DeepSeek API 密钥
- `GOOGLE_CSE_KEY`: Google Custom Search Engine API 密钥
- `GOOGLE_CSE_CX`: Google CSE Engine ID

### 4. 验证环境

```bash
# 检查 Python 版本（建议 3.9+）
python --version

# 检查关键包是否安装
python -c "import pydantic, httpx, pandas; print('✓ 依赖安装成功')"
```

## 使用项目

### 命令行方式

```bash
# 确保虚拟环境已激活
python -m app.main \
  --cv data/your_cv.pdf \
  --keywords "your research keywords" \
  --universities data/universities_template.xlsx
```

### Streamlit UI

```bash
# 确保虚拟环境已激活
streamlit run ui/streamlit_app.py
```

## 退出虚拟环境

```bash
deactivate
```

## 如果虚拟环境不存在

如果 `.venv` 文件夹不存在，需要创建新的虚拟环境：

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 常见问题

### Q: 激活后提示 "command not found"
A: 确保你在项目根目录，并且 `.venv` 文件夹存在。

### Q: 安装依赖时出错
A: 尝试升级 pip：`pip install --upgrade pip`，然后重新安装依赖。

### Q: 如何确认虚拟环境已激活？
A: 命令行提示符前面应该显示 `(.venv)`，或者运行 `which python` 应该指向 `.venv/bin/python`。

