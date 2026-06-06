# 功能修改/设计方案

## 1. 书架加载速度优化：大JSON拆分为独立文件

### 问题分析
- 当前所有小说（含全部章节内容）都存在 `data/history.json` 一个文件中
- `GET /api/novels`（书架列表）返回所有小说的完整数据（含所有章节内容），数据量极大
- 多部小说累积后，JSON 文件可能达到数MB甚至数十MB，读写极其缓慢

### 设计方案
- 书架列表仅存储元信息（id, theme, status, chapterCount, wordsPerChapter, createdAt, updatedAt, chapterMeta）
- `data/history.json` 改为只存元信息，chapters 字段只保留各章的概要（id, title, status, wordCount），不含 content 和 plan
- 每本小说的完整数据（含 chapters 完整内容）存储为独立文件：`data/novels/{novel_id}.json`
- `GET /api/novels` 只返回元信息（书架列表），速度极快
- `GET /api/novels/{id}` 返回完整数据（从独立文件读取），仅访问单本时才加载内容
- 所有写操作（create/update/regenerate/continue/delete）同时更新元信息和独立文件

### 数据结构变化
```
data/
├── history.json          # 只存元信息，章节仅含概要（无content/plan）
└── novels/
    ├── {id1}.json        # 完整小说数据（含所有content/plan）
    └── {id2}.json
```

### history.json 新结构（书架列表用）
```json
[
  {
    "id": "xxx",
    "theme": "xxx",
    "status": "completed",
    "chapterCount": 50,
    "wordsPerChapter": 3000,
    "createdAt": "2026-06-03 08:35:24",
    "updatedAt": "2026-06-03 09:04:07",
    "error": "",
    "chapterMeta": [
      {"id": 1, "title": "xxx", "status": "completed", "wordCount": 3231}
    ]
  }
]
```

### novels/{id}.json 完整结构
- 包含 apiConfig（含 apiKey）、所有章节完整 content 和 plan

---

## 2. API 密钥安全管理

### 问题分析
- 当前 API 密钥存储在 `data/history.json` 中
- `data/history.json` 被 Git 追踪，已推送至 GitHub
- GitHub 仓库上可看到明文 API 密钥 `sk-15943c6e13d247c8b42897cdc6c44bdb`

### 设计方案
- 创建 `api_keys.json` 文件存储所有小说对应的 API 密钥，映射关系：`{novel_id: apiConfig}`
- `api_keys.json` 加入 `.gitignore`，绝不推送到 GitHub
- `data/novels/` 目录也加入 `.gitignore`
- 从 Git 追踪中移除 `data/history.json`（使用 `git rm --cached`）
- 轮换已泄露的 API 密钥（需用户自己在 DeepSeek 平台操作）
- 前端发送 API 密钥时不再持久化到会被追踪的文件中
- 后端读取 `api_keys.json` 获取密钥，文件不存在则使用空值

### 文件保护
```
.gitignore 新增:
api_keys.json
data/novels/
```

---

## 3. 输入框限制问题彻底排查与修复

### 问题分析
- 用户反馈章节数量和字数输入框被上下限卡住
- 可能是浏览器缓存旧版 JS、HTML 属性残留、或 JS 逻辑中有 clamp

### 检查清单
- [ ] ConfigPanel.tsx: input type 是否为 "text"
- [ ] ConfigPanel.tsx: 有无 min/max/step 属性
- [ ] ConfigPanel.tsx: handleSubmit 中有无范围校验
- [ ] store.ts: 有无默认值自动填入
- [ ] run.py: 后端有无 clamp
- [ ] 所有 .tsx/.ts 文件中有无 Math.min/Math.max 影响输入
- [ ] dist/ 构建产物中是否残留旧代码

### 设计方案
- 全面排查所有文件，移除所有输入限制
- 输入框必须是纯文本 `type="text"`，无 min/max/step
- 初始状态为空字符串
- 提交时不做范围校验，后端也不做 clamp
- 确保 dist 重建后无旧代码残留
```

## 实施顺序
1. 先修 API 密钥泄露（最紧急）
2. 再拆分散文件系统
3. 最后排查输入框限制
