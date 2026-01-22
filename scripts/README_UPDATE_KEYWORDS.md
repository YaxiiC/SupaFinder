# 更新导师关键词脚本 / Update Supervisor Keywords Script

## 功能说明 / Description

这个脚本用于更新数据库中已有导师的关键词，通过重新访问他们的 homepage 并使用 DeepSeek 提取 3-5 个关键词。

This script updates keywords for existing supervisors in the database by re-visiting their homepages and extracting 3-5 keywords using DeepSeek.

## 使用方法 / Usage

### 运行脚本 / Run the Script

```bash
cd /Users/chrissychen/Documents/PhD_Final_Year/SuperFinder
python scripts/update_supervisor_keywords.py
```

### 脚本行为 / Script Behavior

1. **读取数据库**: 从 `supervisors` 表中读取所有导师记录
2. **筛选有主页的导师**: 只处理有 `homepage` 或 `profile_url` 的导师
3. **跳过已有正确数量的**: 如果导师已经有 3-5 个关键词，则跳过
4. **提取关键词**: 
   - 访问导师的 homepage
   - 使用 DeepSeek LLM 提取 3-5 个高级别研究关键词
   - 更新数据库中的 `keywords_json` 和 `keywords_text`

### 注意事项 / Notes

- **API 调用**: 脚本会为每个导师调用 DeepSeek API，可能需要一些时间
- **速率限制**: 脚本会使用现有的爬虫速率限制机制
- **缓存**: 脚本不使用缓存（`use_cache=False`），确保获取最新内容
- **错误处理**: 如果提取失败，会记录但继续处理下一个导师

## 输出示例 / Example Output

```
Supervisor Keywords Update Script

Initializing database...
Fetching supervisors from database...
Found 150 supervisors in database

Supervisors with homepage/profile_url: 120

Do you want to proceed with updating keywords? (yes/no): yes

Updating keywords...
✅ Updated John Smith: 4 keywords
⏭️  Skipped Jane Doe (already has 4 keywords)
✅ Updated Bob Johnson: 3 keywords
...

Summary:
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Status                ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ ✅ Updated            │ 85    │
│ ⏭️  Skipped (already 3-5) │ 20    │
│ ❌ Failed            │ 15    │
│ 📊 Total Processed   │ 120   │
└──────────────────────┴───────┘
```

## 关键词提取规则 / Keyword Extraction Rules

提取的关键词遵循以下规则：

1. **高级别研究领域**: 只提取广泛的研究领域术语，不包含具体技术细节
2. **数量**: 3-5 个关键词
3. **示例好的关键词**: "oncology", "cancer research", "medical imaging", "biomedical engineering"
4. **示例不好的关键词**: "EGFR mutation", "CRISPR-Cas9", "single-cell sequencing"

## 故障排除 / Troubleshooting

### 问题: 脚本无法连接到数据库

**解决方案**: 检查 `.env` 文件中的数据库配置

### 问题: DeepSeek API 调用失败

**解决方案**: 检查 `DEEPSEEK_API_KEY` 是否在环境变量或 Streamlit Secrets 中正确配置

### 问题: 很多导师提取失败

**可能原因**:
- Homepage URL 无效或已失效
- 页面内容太少（少于 100 字符）
- 网络连接问题

**解决方案**: 检查失败的导师的 homepage URL 是否可访问

## 相关文件 / Related Files

- `app/modules/llm_deepseek.py`: DeepSeek LLM 客户端，包含关键词提取逻辑
- `app/modules/crawl.py`: 爬虫模块，用于获取页面内容
- `app/db_cloud.py`: 数据库连接和操作

