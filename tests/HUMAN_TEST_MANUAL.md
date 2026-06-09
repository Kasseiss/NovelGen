# 墨流小说生成器 — 人类使用手册 & 边界测试指南

> 本文档基于源码逐行分析生成，覆盖所有用户可见页面、按钮、交互路径和边界情况。
> 适用版本：基于 `run.py` 后端 + React/Vite 前端架构

---

## 目录

- [第一部分：用户决策树](#第一部分用户决策树)
  - [决策树 1：首次使用与配置](#决策树-1首次使用与配置)
  - [决策树 2：生成中操作](#决策树-2生成中操作)
  - [决策树 3：停止/暂停后操作](#决策树-3停止暂停后操作)
  - [决策树 4：阅读页面操作](#决策树-4阅读页面操作)
  - [决策树 5：书架操作](#决策树-5书架操作)
  - [决策树 6：侧边栏操作](#决策树-6侧边栏操作)
  - [决策树 7：顶部导航操作](#决策树-7顶部导航操作)
  - [决策树 8：错误恢复](#决策树-8错误恢复)
  - [决策树 9：服务器生命周期](#决策树-9服务器生命周期)
- [第二部分：边界测试清单](#第二部分边界测试清单)
- [第三部分：发现的问题](#第三部分发现的问题)

---

## 第一部分：用户决策树

> 图例说明：
> - ✅ 已验证行为正确
> - ⚠️ 存在潜在问题（详见第三部分）
> - ❌ 功能缺陷
> - 🔍 需要人工验证

---

### 决策树 1：首次使用与配置

**入口**：用户打开网页 → 默认显示书架页面（`view: 'history'`），侧边栏不显示

```
用户打开网页（默认 view = 'history'）
├── 书架为空
│   ├── 看到"书架空空如也"提示 + "开始创作"按钮
│   ├── 点击"开始创作" → setView('config') → 进入配置页面
│   └── 点击顶部"书架"按钮 → 无反应（已在书架页）
│
├── 有历史小说（见决策树 5）
│
└── 点击顶部"写新作品"按钮 → 进入配置页面
    ⚠️ 注意：Header 的"新作品"按钮在 view='history' 时隐藏，
       只有书架页的"写新作品"按钮可用
```

**配置页面（ConfigPanel）表单操作：**

```
配置页面
├── 【小说主题与要求】textarea
│   ├── 不输入任何内容（空）→ 留空
│   ├── 输入纯空格 → trim() 后为空
│   ├── 输入正常主题 → 正常赋值
│   └── 输入超长文本 → 无限制，正常接受
│
├── 【章节数量】input[type=text]（只允许数字，非数字自动过滤）
│   ├── 留空 → chapterCount = 0 → 无限模式
│   ├── 输入 0 → chapterCount = 0 → 无限模式
│   ├── 输入 10 → chapterCount = 10 → 有限模式
│   ├── 输入 -5 → 正则过滤后变为 "5"（负号被过滤）⚠️ 见问题 P-01
│   ├── 输入 abc → 正则过滤后变为空 → 无限模式
│   ├── 输入 3.14 → 正则过滤后变为 "314" ⚠️ 见问题 P-02
│   ├── 输入 3,000 → 正则过滤后变为 "3000" ✅
│   ├── 输入 999999 → 正常接受（服务端无上限检查）⚠️ 见问题 P-03
│   └── 粘贴含特殊字符文本 → 非数字字符被自动过滤
│
├── 【每章字数】input[type=text]（只允许数字，非数字自动过滤）
│   ├── 留空 → wordsPerChapter = 3000（默认值）
│   ├── 输入 0 → parseInt("0") = 0, 0 < 1 → Toast: "每章字数必须大于0"
│   ├── 输入 5000 → wordsPerChapter = 5000
│   ├── 输入 -100 → 正则过滤后变为 "100" ⚠️ 见问题 P-01
│   ├── 输入 abc → 正则过滤后变为空 → wordsPerChapter = 3000
│   ├── 输入 3,000 → 正则过滤后变为 "3000" ✅
│   ├── 输入 1 → wordsPerChapter = 1（最小有效值）
│   └── 输入 999999 → 正常接受
│
├── 【API 配置】可折叠面板
│   ├── 点击展开/收起按钮 → 切换 showApiConfig 状态
│   ├── 收起状态 → 仅显示 "API 配置" 标题 + 箭头
│   ├── 展开状态 → 显示以下字段：
│   │   ├── 【API 地址】input[type=text]
│   │   │   ├── 留空 → 使用用户清空后的空字符串
│   │   │   ├── 默认值: "https://api.openai.com/v1"
│   │   │   ├── 输入自定义地址 → 正常赋值
│   │   │   └── 输入含空格的 URL → 不做 trim，原样传递 ⚠️ 见问题 P-04
│   │   │
│   │   ├── 【API Key】input[type=password]
│   │   │   ├── 留空 → 空字符串 → 点击开始生成时 Toast: "请输入 API Key"
│   │   │   ├── 输入 sk-xxx → 正常赋值（密码遮罩显示）
│   │   │   └── 输入含空格的 Key → 不做 trim ⚠️ 见问题 P-04
│   │   │
│   │   ├── 【模型名称】input[type=text]
│   │   │   ├── 留空 → 使用用户清空后的空字符串
│   │   │   ├── 默认值: "gpt-4"
│   │   │   └── 输入自定义模型 → 正常赋值
│   │   │
│   │   └── 【系统提示词】
│   │       ├── 点击预设按钮（共 4 个）→ 覆盖整个 textarea
│   │       │   ├── 点击"默认" → 填入默认创作提示词
│   │       │   ├── 点击"热血爽文" → 填入热血爽文提示词
│   │       │   ├── 点击"细腻文艺" → 填入细腻文艺提示词
│   │       │   └── 点击"轻松搞笑" → 填入轻松搞笑提示词
│   │       │   ⚠️ 无确认提示，已有自定义内容会被直接覆盖
│   │       │
│   │       └── 直接编辑 textarea → 自定义系统提示词
│   │
│   └── 收起 API 配置 → 已填入的值保留
│
└── 【开始生成小说】按钮 → 执行 handleStart() 验证流程
    ├── 校验 1: localTheme.trim() 为空 → Toast: "请输入小说主题"（红色错误）
    ├── 校验 2: localApiKey.trim() 为空 → Toast: "请输入 API Key"（红色错误）
    ├── 校验 3: localChapterCount !== '' && parseInt(localChapterCount) < 0
    │   → Toast: "章节数不能为负数"
    │   ⚠️ 实际不可触发：输入框正则已过滤负号（见问题 P-01）
    ├── 校验 4: wordsPerChapter < 1 → Toast: "每章字数必须大于0"
    │   ├── wordsPerChapter = "" → 默认 3000 → 通过
    │   ├── wordsPerChapter = "0" → parseInt = 0 → 0 < 1 → 拦截 ✅
    │   └── wordsPerChapter = "1" → parseInt = 1 → 通过 ✅
    │
    ├── 所有校验通过 → POST /api/novels
    │   ├── 服务端返回 201 → setSelectedNovel(data) + setView('generating')
    │   ├── 服务端返回错误 → Toast: data.error 或 "创建失败"
    │   └── 网络异常 → Toast: "创建任务失败"
    │
    └── 配置保存到 localStorage（每次 setNovelConfig/setApiConfig 时）
```

---

### 决策树 2：生成中操作

**入口**：进入生成页面（`view: 'generating'`），服务端状态为 `generating`

```
生成页面（GeneratingPanel）— 正在生成
│
├── 【自动行为】
│   ├── 每 3 秒轮询 GET /api/novels/{id} 获取最新状态
│   ├── 章节列表实时更新（状态、标题、字数）
│   └── 当服务端 status 变为 'completed' → 停止轮询，显示"生成完成"
│
├── 【顶部状态栏】
│   ├── 生成中 → 显示 Loader2 旋转图标 + "第 N 章 - 正在写作中..."
│   ├── 章节规划中 → "第 N 章 - 生成大纲中..." ⚠️ 见问题 P-05
│   ├── 完成 → 显示 Sparkles 图标 + "生成完成"（绿色）
│   └── 无章节 → "准备就绪"（绿色）
│
├── 【进度条】
│   ├── 有限模式（chapterCount > 0）→ 显示百分比进度
│   └── 无限模式（chapterCount = 0）→ 进度始终为 0% ⚠️ 见问题 P-06
│
├── 【统计信息】
│   ├── 有限模式 → "已完成 X/Y 章"
│   ├── 无限模式 → "已完成 X 章"
│   └── 总字数 → "总字数: X,XXX"
│
├── 【错误信息区域】
│   └── remote.error 非空 → 显示红色错误条 + AlertCircle 图标
│
├── 【章节列表】
│   ├── 空列表 → 显示 Loader2 + "正在准备生成..."
│   ├── 有章节 → 按 ID 顺序显示
│   │   ├── pending 章节（灰色）
│   │   │   ├── 灰色圆点 + 章节标题
│   │   │   ├── "等待生成..." 文字
│   │   │   └── 点击 → 无反应（非 completed 章节不可点击）
│   │   │
│   │   ├── writing 章节（金色高亮）
│   │   │   ├── Loader2 旋转图标 + 章节标题
│   │   │   ├── "正在写作中..." 文字
│   │   │   ├── 大纲区域（如果 plan 非空）→ 显示"大纲"标签 + 内容
│   │   │   └── 点击 → 无反应
│   │   │
│   │   ├── completed 章节（可点击）
│   │   │   ├── 绿色圆点 + 章节标题 + Eye 图标 + 字数
│   │   │   ├── 大纲区域（如果 plan 非空）
│   │   │   ├── 鼠标悬停 → 边框变为金色
│   │   │   └── 点击 → setCurrentChapterId(id) + setView('reading') → 进入阅读
│   │   │
│   │   └── error 章节（红色）
│   │       ├── 红色边框背景
│   │       └── 点击 → 无反应
│   │
│   └── planning 章节
│       ⚠️ 服务端不使用 'planning' 状态，此分支理论上不会出现（见问题 P-05）
│
├── 【按钮区域 — 生成中】
│   ├── "阅读"按钮 → setView('reading')（仅当 completedCount > 0 时显示）
│   ├── "书架"按钮 → setView('history')
│   ├── "停止生成"按钮 → handleStop()
│   │   ├── POST /api/novels/stop
│   │   ├── 前端乐观更新：
│   │   │   ├── writing/planning 章节 → pending（清空 content 和 wordCount）
│   │   │   └── status → 'paused'
│   │   └── 服务端同步处理
│   │       ├── writing/planning 章节 → pending（清空 content 和 wordCount）
│       ├── status → 'paused'
│       └── 取消正在运行的生成线程
│   └── ⚠️ 无确认对话框，点击即停止（见问题 P-07）
│
└── 【按钮区域 — 已完成/已暂停/错误】
    ├── "阅读"按钮（仅当 completedCount > 0）
    ├── "书架"按钮
    ├── "继续生成"按钮（仅当 hasUncompletedChapters 为 true）
    │   ├── POST /api/novels/continue
    │   ├── 服务端处理：
    │   │   ├── error/writing/planning 章节 → pending
    │   │   ├── error 章节保留已有 content
    │   │   ├── status → 'generating'
    │   │   └── 启动新的生成线程
    │   └── 前端：status → 'generating'
    │
    ├── "重新生成"按钮
    │   ├── POST /api/novels/regenerate
    │   ├── 服务端处理：
    │   │   ├── 清空所有 chapters
    │   │   ├── status → 'generating'
    │   │   └── 启动新的生成线程
    │   └── 前端：清空 chapters，status → 'generating'
    │   ⚠️ 无确认对话框，所有已完成章节将被清空（见问题 P-08）
    │
    └── "配置"按钮 → setView('config')
        ⚠️ 点击后回到配置页面，当前小说状态保留在 store 中
```

---

### 决策树 3：停止/暂停后操作

**入口**：生成页面，服务端状态为 `paused`

```
生成页面 — 已暂停（paused）
│
├── 【章节状态分布】
│   ├── 已完成章节（completed）→ 绿色，可点击阅读
│   ├── 待生成章节（pending）→ 灰色，显示"等待生成"
│   │   ⚠️ 被停止的 writing/planning 章节内容已被清空
│   └── 错误章节（error）→ 红色
│
├── 点击"继续生成"
│   ├── POST /api/novels/continue
│   ├── 服务端：error/writing/planning → pending，status → 'generating'
│   ├── 生成线程从第一个 pending 章节开始
│   └── 前端轮询恢复
│
├── 点击"重新生成"
│   ├── POST /api/novels/regenerate
│   ├── 清空所有章节，从第 1 章重新开始
│   └── ⚠️ 无确认提示，所有已完成章节内容丢失
│
├── 点击已完成章节卡片 → 进入阅读页面
├── 点击"阅读"按钮 → 进入阅读页面
├── 点击"书架" → 回到书架
└── 点击"配置" → 进入配置页面（创建新小说）
```

---

### 决策树 4：阅读页面操作

**入口**：`view: 'reading'`，有已完成的章节

```
阅读页面（ReaderPanel）
│
├── 【无章节情况】
│   └── currentChapter 不存在 → 显示 BookOpen 图标 + "请选择一章阅读"
│
├── 【有章节情况】
│   ├── 显示章节标题："第X章：标题"（金色大号字体）
│   ├── 显示章节正文（按段落分割，空行跳过）
│   └── 内容超长 → 正常滚动（overflow-y-auto）
│
├── 【点击操作】（handleAreaClick，基于鼠标位置比例）
│   ├── 点击左侧 35%（ratio < 0.35）→ 上一章
│   │   ├── 有上一章 → 切换到上一章（自动滚动到顶部）
│   │   └── 已是第一章 → 无反应（goToPrev 中 completedIndex <= 0 时 return）
│   │
│   ├── 点击右侧 35%（ratio > 0.65）→ 下一章
│   │   ├── 有下一章 → 切换到下一章
│   │   └── 已是最后一章 → 无反应
│   │
│   └── 点击中间 30%（0.35 <= ratio <= 0.65）→ 切换控制面板
│       ├── 首次点击 → 显示控制面板
│       ├── 再次点击 → 隐藏控制面板
│       └── 切换章节时 → 控制面板自动隐藏
│
├── 【控制面板覆盖层】
│   ├── 半透明黑色背景（bg-black/60）
│   ├── 中央导航区
│   │   ├── ‹ 按钮（上一章）
│   │   │   ├── 有上一章 → 白色高亮，可点击
│   │   │   └── 无上一章 → 半透明灰色，cursor-not-allowed
│   │   │
│   │   ├── 中间信息
│   │   │   ├── 显示 "X / Y"（当前索引 / 总已完成章节数）
│   │   │   └── 字数（wordCount > 0 时显示）
│   │   │
│   │   └── › 按钮（下一章）
│   │       ├── 有下一章 → 白色高亮，可点击
│   │       └── 无下一章 → 半透明灰色，cursor-not-allowed
│   │
│   ├── 底部操作栏
│   │   ├── "书架" → setView('history')
│   │   ├── "重新生成" → 重新生成当前章节
│   │   │   ├── POST /api/novels/regenerate-chapter
│   │   │   ├── 请求体: { novelId, chapterId }
│   │   │   ├── 前端：当前章节 status → 'writing'，清空 content
│   │   │   ├── setView('generating') → 跳转到生成页面
│   │   │   ⚠️ 无确认对话框
│   │   │
│   │   └── "关闭" → setShowControls(false)
│   │
│   └── 点击背景空白区域 → setShowControls(false)
│
├── 【键盘操作】（桌面端）
│   ├── 按 ← → goToPrev()（同上一章逻辑）
│   ├── 按 → → goToNext()（同下一章逻辑）
│   ├── 按 Escape → 关闭控制面板
│   └── 输入框/文本框内按键 → 不触发导航（已做 target 检查）
│
├── 【触摸操作】（移动端）
│   ├── 右滑（dx > 60px）→ 上一章
│   ├── 左滑（dx < -60px）→ 下一章
│   ├── 短滑（|dx| < 60px）→ 忽略
│   └── 滑动阈值: 60px
│
├── 【边界情况】
│   ├── 只有一章 → 左右导航均不可用
│   ├── 第一章 + 按 ← → 无反应
│   ├── 最后一章 + 按 → → 无反应
│   ├── 章节内容为空 → 正文区域为空（只有标题）
│   ├── 章节内容含空行 → 空行被跳过（paragraph.trim() 过滤）
│   ├── 切换章节 → 内容区自动 scrollTop = 0 + 控制面板隐藏
│   └── completedIndex = -1（currentChapterId 不在已完成列表中）
│       → currentChapter 不存在 → 显示"请选择一章阅读"
│
└── 【顶部 Header 操作】（阅读页面特有）
    ├── "生成视图"按钮 → setView('generating')
    ├── "导出"按钮 → 导出 TXT（见决策树 7）
    └── "书架"按钮 → setView('history')
```

---

### 决策树 5：书架操作

**入口**：`view: 'history'`

```
书架页面（HistoryPanel）
│
├── 【自动行为】
│   ├── 每 3 秒轮询 GET /api/novels 刷新列表
│   └── 列表数据不含完整章节内容（只有元数据）
│
├── 【空书架】
│   ├── 显示 BookMarked 图标 + "书架空空如也"
│   ├── "点击上方'写新作品'开始你的第一部小说" 提示
│   └── "开始创作"按钮 → setView('config')
│
├── 【顶部栏】
│   ├── "我的书架" 标题 + 作品数量
│   └── "写新作品"按钮 → setView('config')
│
├── 【小说卡片列表】
│   ├── 卡片样式（按状态区分）
│   │   ├── generating → 琥珀色边框 + Loader2 旋转 + "正在后台生成..."
│   │   ├── error → 红色边框 + 红点 + "生成失败"
│   │   ├── completed → 绿点 + 更新时间
│   │   └── paused → "已暂停" 文字
│   │
│   ├── 卡片内容
│   │   ├── 主题（前 60 字符，超出截断）
│   │   ├── 状态信息（状态文字 + 章节数 + 总字数 + 模式）
│   │   │   ├── 有限模式 → "X 章目标"
│   │   │   └── 无限模式 → "无限模式"
│   │   ├── 进度条（仅 generating 状态）
│   │   │   ├── 有限模式 → 已完成 X/Y 章
│   │   │   └── 无限模式 → 已完成 X 章（进度基于 500 章计算）⚠️
│   │   └── 章节标签（最多显示 6 个，超出显示 "+N"）
│   │
│   ├── 卡片右侧操作区（hover 时显示）
│   │   ├── generating → "查看" 标签
│   │   ├── completed + 有章节 → "阅读" 标签
│   │   └── 删除按钮（Trash2 图标，始终可点击）
│   │
│   └── 【点击卡片】→ openNovel(record)
│       ├── fetch GET /api/novels/{id} 获取完整数据
│       ├── 成功且无 error → setSelectedNovel(fullNovel)
│       │   ├── status 为 generating/error/paused → setView('generating')
│       │   └── status 为 completed → setView('reading')
│       │
│       └── fetch 失败 → 降级使用列表数据（无章节内容）⚠️
│           ├── status 为 generating/error/paused → setView('generating')
│           └── status 为 completed → setView('reading')
│
└── 【删除操作】
    ├── 点击删除按钮（e.stopPropagation 阻止卡片点击）
    ├── 弹出确认对话框
    │   ├── 标题: "确认删除"
    │   ├── 说明: "确定要删除这部作品吗？删除后无法恢复。"
    │   ├── "取消"按钮 → setConfirmDeleteId(null) → 关闭对话框
    │   ├── "确认删除"按钮 → POST /api/novels/delete + 刷新列表
    │   └── 点击背景遮罩 → 关闭对话框
    │
    └── 服务端处理
        ├── 删除小说文件 (data/novels/{id}.json)
        ├── 删除 API Key 记录
        ├── 从历史记录中移除
        └── 取消正在运行的生成线程
```

---

### 决策树 6：侧边栏操作

**入口**：`view` 为 `generating` 或 `reading` 时显示

```
侧边栏（Sidebar）
│
├── 【桌面端】（md 以上屏幕）
│   ├── 展开状态（默认，sidebarCollapsed = false）
│   │   ├── 左侧 288px 固定宽度
│   │   ├── 顶部: "章节列表" 标题 + 收起按钮（ChevronLeft）
│   │   ├── 章节列表
│   │   │   ├── 每个章节项
│   │   │   │   ├── 状态图标
│   │   │   │   │   ├── completed → 绿色圆点
│   │   │   │   │   ├── pending → 灰色圆点
│   │   │   │   │   ├── planning → 琥珀色旋转图标 ⚠️ 服务端不使用此状态
│   │   │   │   │   ├── writing → 金色旋转图标
│   │   │   │   │   └── error → 红色 AlertCircle
│   │   │   │   ├── 章节标题/状态文字
│   │   │   │   │   ├── 有标题 → 显示标题（截断）
│   │   │   │   │   ├── planning → "规划中..."
│   │   │   │   │   ├── writing → "写作中..."
│   │   │   │   │   └── pending → "等待生成"
│   │   │   │   ├── completed 章节 → Eye 图标 + 字数
│   │   │   │   ├── 当前章节 → 金色高亮边框
│   │   │   │   │
│   │   │   │   └── 【点击行为】
│   │   │   │       ├── completed 章节 → setCurrentChapterId + setView('reading')
│   │   │   │       └── 非 completed 章节 → 无反应
│   │   │   │           ⚠️ 无视觉反馈表明不可点击（见问题 P-09）
│   │   │   │
│   │   │   └── 空列表 → "暂无章节" 提示
│   │   │
│   │   └── 底部统计: "共 X 章" + "X,XXX 字"
│   │
│   └── 收起状态（sidebarCollapsed = true）
│       ├── 左边缘显示 ChevronRight 展开按钮
│       ├── 仅在 chapters.length > 0 时显示
│       └── 点击 → setSidebarCollapsed(false) → 展开侧边栏
│
├── 【移动端】（md 以下屏幕）
│   ├── 收起状态（默认）
│   │   ├── 左下角浮动 Menu 按钮
│   │   ├── 仅在 chapters.length > 0 时显示
│   │   └── 点击 → setMobileOpen(true) → 打开覆盖层
│   │
│   ├── 展开状态（覆盖层）
│   │   ├── 全屏半透明黑色背景
│   │   ├── 左侧 288px 面板（SidebarContent）
│   │   ├── 点击背景 → setMobileOpen(false) → 关闭
│   │   └── 点击章节 → 同桌面端行为
│   │       ⚠️ 点击 completed 章节后不会自动关闭移动端覆盖层（见问题 P-10）
│   │
│   └── 收起按钮（SidebarContent 内 ChevronLeft）
│       ├── 点击 → setSidebarCollapsed(true)
│       └── useEffect 监听 sidebarCollapsed → setMobileOpen(false) → 关闭移动端覆盖层
│
└── 【无章节时】
    ├── 侧边栏不渲染（App.tsx 中 Sidebar 仅在 generating/reading 时渲染）
    └── 即使在 generating/reading 视图，chapters 为空时显示"暂无章节"
```

---

### 决策树 7：顶部导航操作

**入口**：所有页面均显示 Header

```
顶部导航（Header）
│
├── 左侧
│   ├── BookOpen 图标 + "墨流" 品牌名
│   └── 已完成章节统计（completedChapters.length > 0 时）
│       └── "X 章 · X,XXX 字"（仅桌面端显示）
│
├── 右侧按钮
│   ├── "书架"按钮（Clock 图标）
│   │   ├── 始终显示
│   │   ├── 当前是书架页 → 金色高亮（active 样式）
│   │   └── 点击 → setView('history')
│   │
│   ├── "生成视图"按钮（FileText 图标）
│   │   ├── 仅在 view === 'reading' 时显示
│   │   └── 点击 → setView('generating')
│   │
│   ├── "导出"按钮（Download 图标）
│   │   ├── 仅在 completedChapters.length > 0 时显示
│   │   ├── 点击 → handleExportTXT()
│   │   │   ├── 过滤 completed 章节
│   │   │   ├── 格式: "第X章：标题\n\n内容\n\n---\n\n"
│   │   │   ├── 生成 Blob → 创建下载链接
│   │   │   ├── 文件名: "{主题前20字}_{日期}.txt"
│   │   │   │   ├── 主题特殊字符替换为下划线
│   │   │   │   ├── 只保留中文、英文、数字
│   │   │   │   └── 主题为空 → 文件名: "小说_{日期}.txt"
│   │   │   └── 自动触发下载
│   │   │
│   │   └── 无已完成章节 → 按钮不显示
│   │
│   └── "新作品"按钮（Settings 图标）
│       ├── 显示条件: !isGenerating && view !== 'config' && view !== 'history'
│       │   ├── config 页面 → 不显示
│       │   ├── history 页面 → 不显示
│       │   ├── generating 页面 + 非生成中 → 显示
│       │   ├── generating 页面 + 生成中 → 不显示
│       │   └── reading 页面 → 显示
│       │
│       └── 点击 → setView('config') → 进入配置页面
│           ⚠️ 此时 store 中的 novelConfig/apiConfig 可能是上一部小说的值
```

---

### 决策树 8：错误恢复

```
错误场景与恢复路径
│
├── 【API Key 无效】
│   ├── 服务端 api_request 返回 401/403
│   ├── 服务端: novel.status → 'error', novel.error → 错误信息
│   ├── 前端: 显示红色错误条
│   ├── 恢复: 点击"继续生成"
│   │   ├── 服务端将 error 章节重置为 pending
│   │   ├── 重新启动生成线程
│   │   └── 如果 API Key 仍然无效 → 再次失败
│   └── 最佳实践: 回到配置页面修改 API Key（创建新小说）
│
├── 【API 超时】
│   ├── 服务端 api_request timeout = 120 秒
│   ├── 超时后抛出异常
│   ├── 服务端: status → 'error'
│   └── 恢复: 点击"继续生成"
│
├── 【API 频率限制 (429)】
│   ├── 同上，status → 'error'
│   ├── 恢复: 等待一段时间后点击"继续生成"
│   └── ⚠️ 无自动退避重试机制（见问题 P-11）
│
├── 【API 返回空内容】
│   ├── 内容长度 < 10 字符 → 章节 status 设为 'error'
│   ├── 生成线程继续处理下一章
│   └── 恢复: 点击"继续生成"
│
├── 【网络断开（前端）】
│   ├── 轮询请求失败 → catch 为空 → 静默忽略
│   ├── 章节列表停止更新（显示最后一次成功数据）
│   ├── 网络恢复后 → 下次轮询自动获取最新数据
│   └── ⚠️ 无网络状态提示（见问题 P-12）
│
├── 【服务器重启】
│   ├── 启动时 restore_generating_jobs()
│   │   ├── 所有 status = 'generating' 的小说 → 设为 'pending'
│   │   └── 所有 status = 'pending' 的小说 → 启动生成线程
│   ├── 前端自动恢复轮询
│   └── 生成自动继续
│
├── 【章节重新生成失败】
│   ├── run_chapter_regen_job 异常
│   ├── 服务端: status → 'error', error → "重新生成第X章失败: ..."
│   └── 恢复: 在生成页面点击"继续生成"或再次"重新生成"
│
└── 【并发操作冲突】
    ├── 同时对同一章节点击"重新生成"
    │   ├── 第二个请求返回 409 "already regenerating"
    │   └── 前端 catch 为空，静默忽略
    │
    ├── 生成中点击"停止"再点击"继续"
    │   ├── stop 设置 cancel_event
    │   ├── continue 重新启动生成线程
    │   └── 由于 start_job 会先设置已有 cancel_event，安全
    │
    └── 生成中点击"重新生成"
        ├── 服务端清空章节并启动新线程
        ├── 旧线程通过 cancel_event 检测退出
        └── ⚠️ 竞态窗口：旧线程可能在 cancel 检查之间写入章节（见问题 P-13）
```

---

### 决策树 9：服务器生命周期

```
服务器启动流程（run.py）
│
├── 1. ensure_dirs() → 创建 data/ 和 data/novels/ 目录
├── 2. migrate_data() → 旧版 history.json 数据迁移到独立文件
├── 3. npm_build_if_needed() → 如果 dist/ 不存在则自动构建
├── 4. restore_generating_jobs() → 恢复中断的生成任务
│   ├── 将 'generating' 状态重置为 'pending'
│   └── 为所有 'pending' 状态小说启动生成线程
├── 5. 启动 HTTP 服务器（默认端口 5025）
│   └── ThreadedHTTPServer → 多线程处理请求
│
├── 【API 端点总览】
│   ├── GET  /api/novels            → 获取书架列表（不含完整章节）
│   ├── GET  /api/novels/{id}       → 获取单本小说详情（不含 apiConfig）
│   ├── POST /api/novels            → 创建新小说并开始生成
│   ├── POST /api/novels/delete     → 删除小说
│   ├── POST /api/novels/stop       → 停止生成
│   ├── POST /api/novels/continue   → 继续生成
│   ├── POST /api/novels/regenerate → 重新生成整本小说
│   └── POST /api/novels/regenerate-chapter → 重新生成单章
│
├── 【静态文件服务】
│   ├── 非 /api/ 路径 → 从 dist/ 目录提供文件
│   ├── 目录请求 → 自动查找 index.html
│   ├── 不存在的路径 → 回退到 index.html（SPA 路由）
│   └── HTML 文件 → 自动追加版本号缓存破坏参数
│
├── 【数据存储】
│   ├── data/history.json  → 书架列表（精简元数据）
│   ├── data/novels/{id}.json → 单本小说完整数据（不含 apiConfig）
│   └── data/api_keys.json → API Key 存储（独立文件）
│       ⚠️ API Key 明文存储在磁盘（见问题 P-14）
│
└── 【无限模式的实际限制】
    ├── chapterCount = 0 时，服务端 target = 500
    ├── 即"无限模式"实际最多生成 500 章
    └── ⚠️ 见问题 P-15
```

---

## 第二部分：边界测试清单

### 2.1 配置页面测试

| 编号 | 决策路径 | 预期结果 | 实际代码行为 | 测试状态 |
|------|----------|----------|--------------|----------|
| C-01 | 主题留空 → 点击开始生成 | Toast: 请输入小说主题 | `localTheme.trim()` 为空 → showToast ✅ | 🔍 |
| C-02 | 主题输入纯空格 → 开始生成 | Toast: 请输入小说主题 | trim() 后为空 ✅ | 🔍 |
| C-03 | 主题正常输入 + API Key 为空 | Toast: 请输入 API Key | `localApiKey.trim()` 为空 ✅ | 🔍 |
| C-04 | 主题 + API Key + 章节留空 | 无限模式 (chapterCount=0) | `'' ? 0 : ...` → 0 ✅ | 🔍 |
| C-05 | 主题 + API Key + 章节输入 0 | 无限模式 (chapterCount=0) | `Math.max(0, 0)` → 0 ✅ | 🔍 |
| C-06 | 主题 + API Key + 章节输入 10 | 有限模式 (chapterCount=10) | `Math.max(0, 10)` → 10 ✅ | 🔍 |
| C-07 | 章节输入 -5 | 正则过滤后变为 "5" | `replace(/[^0-9]/g, '')` 过滤负号 ⚠️ | 🔍 |
| C-08 | 章节输入 abc | 正则过滤后为空 → 无限模式 | 无数字字符 → 空字符串 ✅ | 🔍 |
| C-09 | 字数留空 | 默认 3000 | `'' ? 3000 : ...` ✅ | 🔍 |
| C-10 | 字数输入 0 | Toast: 每章字数必须大于0 | `parseInt("0") \|\| 0` = 0 < 1 ✅ | 🔍 |
| C-11 | 字数输入 5000 | 自定义字数 5000 | `parseInt("5000")` = 5000 ✅ | 🔍 |
| C-12 | 字数输入 -100 | 正则过滤后变为 "100" | 负号被过滤 ⚠️ | 🔍 |
| C-13 | 字数输入 1 | 最小有效值 | 1 >= 1 通过 ✅ | 🔍 |
| C-14 | 展开 API 配置 → 修改 API 地址 | 正常更新 localBaseUrl | setState 正常 ✅ | 🔍 |
| C-15 | 展开 API 配置 → 修改模型名称 | 正常更新 localModel | setState 正常 ✅ | 🔍 |
| C-16 | 点击"默认"预设 | textarea 填入默认提示词 | `setLocalSystemPrompt(preset.prompt)` ✅ | 🔍 |
| C-17 | 点击"热血爽文"预设 | textarea 填入热血提示词 | 同上 ✅ | 🔍 |
| C-18 | 点击"细腻文艺"预设 | textarea 填入文艺提示词 | 同上 ✅ | 🔍 |
| C-19 | 点击"轻松搞笑"预设 | textarea 填入搞笑提示词 | 同上 ✅ | 🔍 |
| C-20 | 有自定义提示词 → 点击预设 | 直接覆盖，无确认 | ⚠️ 无确认提示 | 🔍 |
| C-21 | 修改配置 → 切换页面 → 回来 | 配置保存在 localStorage | loadConfig() 恢复 ✅ | 🔍 |
| C-22 | 正常创建小说 | POST /api/novels → 201 → 跳转生成页 | try/catch + setView ✅ | 🔍 |
| C-23 | 服务端返回错误 | Toast: data.error 或 "创建失败" | `resp.ok` 检查 ✅ | 🔍 |
| C-24 | 网络异常 | Toast: "创建任务失败" | catch 块 ✅ | 🔍 |

### 2.2 生成页面测试

| 编号 | 决策路径 | 预期结果 | 实际代码行为 | 测试状态 |
|------|----------|----------|--------------|----------|
| G-01 | 进入生成页面 | 自动开始轮询 (3s) | useEffect + setInterval ✅ | 🔍 |
| G-02 | 章节列表为空 | "正在准备生成..." + 旋转图标 | `localChapters.length === 0` ✅ | 🔍 |
| G-03 | 点击 pending 章节 | 无反应 | `chapter.status === 'completed'` 才触发 ✅ | 🔍 |
| G-04 | 点击 completed 章节 | 进入阅读页面，跳到该章节 | handleReadChapter ✅ | 🔍 |
| G-05 | 点击 error 章节 | 无反应 | 同 G-03 ✅ | 🔍 |
| G-06 | 点击 writing 章节 | 无反应 | 同 G-03 ✅ | 🔍 |
| G-07 | 生成中点击"停止生成" | 立即停止，无确认 | POST /api/novels/stop ⚠️ | 🔍 |
| G-08 | 停止后 writing 章节 | 变为 pending，内容清空 | 前端 + 服务端均清空 ✅ | 🔍 |
| G-09 | 已暂停 + 点击"继续生成" | 从第一个 pending 章节继续 | POST /api/novels/continue ✅ | 🔍 |
| G-10 | 已暂停 + 点击"重新生成" | 清空所有章节，从头开始 | POST /api/novels/regenerate ⚠️ | 🔍 |
| G-11 | 已完成 + 点击"重新生成" | 清空所有章节，从头开始 | 同 G-10 ⚠️ | 🔍 |
| G-12 | 有 error 章节 + 继续生成 | error 章节重置为 pending | 服务端代码 ✅ | 🔍 |
| G-13 | 点击"阅读"按钮 | 进入阅读页面 | setView('reading') ✅ | 🔍 |
| G-14 | 点击"书架"按钮 | 回到书架页面 | setView('history') ✅ | 🔍 |
| G-15 | 点击"配置"按钮 | 进入配置页面 | setView('config') ✅ | 🔍 |
| G-16 | 无限模式进度条 | 进度始终为 0% | `chapterCount > 0 ? ... : 0` ⚠️ | 🔍 |
| G-17 | 有限模式进度条 | 按百分比显示 | `completedCount / chapterCount * 100` ✅ | 🔍 |
| G-18 | 显示错误信息 | 红色错误条 | `remote?.error` ✅ | 🔍 |
| G-19 | 生成完成 | "生成完成" 绿色文字 | `!isGenerating` 分支 ✅ | 🔍 |
| G-20 | 自动停止轮询 | status !== 'generating' 时停止 | `stop = true` ✅ | 🔍 |
| G-21 | 完成后点击"继续生成" | 无此按钮 | `hasUncompletedChapters` 为 false ✅ | 🔍 |

### 2.3 阅读页面测试

| 编号 | 决策路径 | 预期结果 | 实际代码行为 | 测试状态 |
|------|----------|----------|--------------|----------|
| R-01 | 无章节时进入阅读 | "请选择一章阅读" | `!currentChapter` ✅ | 🔍 |
| R-02 | 点击屏幕左侧 35% | 上一章 | `ratio < 0.35` → goToPrev ✅ | 🔍 |
| R-03 | 点击屏幕右侧 35% | 下一章 | `ratio > 0.65` → goToNext ✅ | 🔍 |
| R-04 | 点击屏幕中间 30% | 切换控制面板 | `setShowControls(v => !v)` ✅ | 🔍 |
| R-05 | 第一章按 ← | 无反应 | `completedIndex <= 0` check ✅ | 🔍 |
| R-06 | 最后一章按 → | 无反应 | `completedIndex >= length - 1` check ✅ | 🔍 |
| R-07 | 按 Escape | 关闭控制面板 | `setShowControls(false)` ✅ | 🔍 |
| R-08 | 右滑 > 60px | 上一章 | `dx > 0` → goToPrev ✅ | 🔍 |
| R-09 | 左滑 > 60px | 下一章 | `dx < 0` → goToNext ✅ | 🔍 |
| R-10 | 短滑 < 60px | 忽略 | `Math.abs(dx) < 60` return ✅ | 🔍 |
| R-11 | 控制面板 › 按钮（无下一章） | 灰色禁用 | `!hasNext` → disabled 样式 ✅ | 🔍 |
| R-12 | 控制面板 ‹ 按钮（无上一章） | 灰色禁用 | `!hasPrev` → disabled 样式 ✅ | 🔍 |
| R-13 | 控制面板 → "书架" | 回到书架 | setView('history') ✅ | 🔍 |
| R-14 | 控制面板 → "重新生成" | 重新生成当前章节 | POST regenerate-chapter + setView('generating') ⚠️ | 🔍 |
| R-15 | 控制面板 → "关闭" | 关闭面板 | setShowControls(false) ✅ | 🔍 |
| R-16 | 控制面板 → 点击背景 | 关闭面板 | 外层 onClick ✅ | 🔍 |
| R-17 | 空内容章节 | 正文区域为空 | `content.split('\n')` → 空数组 ✅ | 🔍 |
| R-18 | 超长内容章节 | 正常滚动 | overflow-y-auto ✅ | 🔍 |
| R-19 | 切换章节 | 自动滚动到顶部 + 隐藏面板 | useEffect ✅ | 🔍 |
| R-20 | 章节含空行 | 空行被过滤 | `paragraph.trim() ? ... : null` ✅ | 🔍 |
| R-21 | 在输入框内按方向键 | 不触发章节导航 | target instanceof check ✅ | 🔍 |

### 2.4 书架页面测试

| 编号 | 决策路径 | 预期结果 | 实际代码行为 | 测试状态 |
|------|----------|----------|--------------|----------|
| H-01 | 空书架 | "书架空空如也" + 开始创作按钮 | `records.length === 0` ✅ | 🔍 |
| H-02 | 空书架 → "开始创作" | 进入配置页面 | setView('config') ✅ | 🔍 |
| H-03 | 空书架 → "写新作品" | 进入配置页面 | setView('config') ✅ | 🔍 |
| H-04 | 点击 generating 小说卡片 | 进入生成页面 | `status === 'generating'` → setView('generating') ✅ | 🔍 |
| H-05 | 点击 completed 小说卡片 | 进入阅读页面 | `status === 'completed'` → setView('reading') ✅ | 🔍 |
| H-06 | 点击 paused 小说卡片 | 进入生成页面 | `status === 'paused'` → setView('generating') ✅ | 🔍 |
| H-07 | 点击 error 小说卡片 | 进入生成页面 | `status === 'error'` → setView('generating') ✅ | 🔍 |
| H-08 | 点击删除按钮 | 弹出确认对话框 | setConfirmDeleteId ✅ | 🔍 |
| H-09 | 确认对话框 → "取消" | 关闭对话框 | setConfirmDeleteId(null) ✅ | 🔍 |
| H-10 | 确认对话框 → "确认删除" | 删除小说 + 刷新列表 | POST /api/novels/delete ✅ | 🔍 |
| H-11 | 确认对话框 → 点击背景 | 关闭对话框 | `onClick={() => setConfirmDeleteId(null)}` ✅ | 🔍 |
| H-12 | 自动生成中卡片 | 进度条 + 琥珀色样式 | isGenerating 分支 ✅ | 🔍 |
| H-13 | 无限模式卡片 | "无限模式" + 进度基于 500 | `chapterCount \|\| 500` ⚠️ | 🔍 |
| H-14 | 轮询刷新 | 每 3 秒刷新 | setInterval(load, 3000) ✅ | 🔍 |
| H-15 | 章节标签显示 | 最多 6 个 + "+N" | `slice(0, 6)` ✅ | 🔍 |
| H-16 | fetch 失败降级 | 使用列表数据 | catch → 使用 item 数据 ⚠️ | 🔍 |

### 2.5 侧边栏测试

| 编号 | 决策路径 | 预期结果 | 实际代码行为 | 测试状态 |
|------|----------|----------|--------------|----------|
| S-01 | 桌面端默认状态 | 展开 288px 侧边栏 | `!sidebarCollapsed` ✅ | 🔍 |
| S-02 | 桌面端点击收起 | 侧边栏收起 | setSidebarCollapsed(true) ✅ | 🔍 |
| S-03 | 桌面端收起后点击展开 | 侧边栏展开 | setSidebarCollapsed(false) ✅ | 🔍 |
| S-04 | 点击 completed 章节 | 跳转到阅读 | handleChapterClick ✅ | 🔍 |
| S-05 | 点击 pending 章节 | 无反应 | `status === 'completed'` check ✅ | 🔍 |
| S-06 | 空章节列表 | "暂无章节" | `chapters.length === 0` ✅ | 🔍 |
| S-07 | 移动端点击 Menu 按钮 | 打开覆盖层 | setMobileOpen(true) ✅ | 🔍 |
| S-08 | 移动端点击背景 | 关闭覆盖层 | `onClick={() => setMobileOpen(false)}` ✅ | 🔍 |
| S-09 | 移动端点击章节后 | 覆盖层仍然打开 | ⚠️ handleChapterClick 不关闭覆盖层 | 🔍 |
| S-10 | 收起侧边栏 → 移动端 Menu 隐藏 | 覆盖层关闭 | useEffect ✅ | 🔍 |

### 2.6 顶部导航测试

| 编号 | 决策路径 | 预期结果 | 实际代码行为 | 测试状态 |
|------|----------|----------|--------------|----------|
| N-01 | 书架页 → "书架"按钮 | 金色高亮（当前页） | `view === 'history'` active 样式 ✅ | 🔍 |
| N-02 | 阅读页 → "生成视图"按钮 | 显示，可点击 | `view === 'reading'` 条件 ✅ | 🔍 |
| N-03 | 生成页 → "生成视图"按钮 | 不显示 | `view !== 'reading'` ✅ | 🔍 |
| N-04 | 有完成章节 → "导出"按钮 | 显示，点击下载 TXT | completedChapters.length > 0 ✅ | 🔍 |
| N-05 | 无完成章节 → "导出"按钮 | 不显示 | `completedChapters.length === 0` ✅ | 🔍 |
| N-06 | 导出文件名含特殊字符 | 特殊字符替换为下划线 | `replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_')` ✅ | 🔍 |
| N-07 | 生成中 → "新作品"按钮 | 不显示 | `!isGenerating` check ✅ | 🔍 |
| N-08 | 非生成中 + 生成/阅读页 → "新作品" | 显示 | 条件通过 ✅ | 🔍 |
| N-09 | config 页 → "新作品"按钮 | 不显示 | `view !== 'config'` check ✅ | 🔍 |
| N-10 | history 页 → "新作品"按钮 | 不显示 | `view !== 'history'` check ✅ | 🔍 |
| N-11 | 导出空主题小说 | 文件名 "小说_{日期}.txt" | `safeName \|\| '小说'` ✅ | 🔍 |

### 2.7 Toast 通知测试

| 编号 | 决策路径 | 预期结果 | 实际代码行为 | 测试状态 |
|------|----------|----------|--------------|----------|
| T-01 | 触发 Toast | 右上角显示通知 | fixed top-16 right-4 ✅ | 🔍 |
| T-02 | error 类型 Toast | 红色边框 + AlertCircle | bgColors.error ✅ | 🔍 |
| T-03 | success 类型 Toast | 绿色边框 + CheckCircle | bgColors.success ✅ | 🔍 |
| T-04 | info 类型 Toast | 金色边框 + Info | bgColors.info ✅ | 🔍 |
| T-05 | 3 秒后自动消失 | 自动移除 | setTimeout 3000ms ✅ | 🔍 |
| T-06 | 手动点击关闭 | 立即移除 | onClick filter ✅ | 🔍 |
| T-07 | 多个 Toast 同时显示 | 垂直堆叠 | flex-col gap-2 ✅ | 🔍 |

---

## 第三部分：发现的问题

### P-01：章节/字数输入的负数校验是死代码

- **位置**：[ConfigPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/ConfigPanel.tsx#L107-L109)
- **描述**：章节数量和每章字数的输入框使用了 `replace(/[^0-9]/g, '')` 正则过滤（第 196、210 行），这意味着负号 `-` 会被自动过滤掉，用户根本无法输入负数。因此第 107-109 行的 `parseInt(localChapterCount) < 0` 检查永远不会触发。
- **影响**：代码冗余，不影响功能。但 Toast "章节数不能为负数" 永远不会显示。
- **建议**：移除死代码，或者改用 `type="number"` 输入框以允许负数输入（然后保留校验）。

### P-02：小数点被过滤为数字拼接

- **位置**：[ConfigPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/ConfigPanel.tsx#L196)
- **描述**：如果用户输入 "3.14"，正则 `replace(/[^0-9]/g, '')` 会过滤掉小数点，结果变为 "314"。这可能不是用户期望的行为。
- **影响**：用户可能误以为输入了 3.14 章/字，实际得到 314。不过对于章节/字数来说，整数是合理的。
- **建议**：当前行为可接受，但建议在输入框旁添加"仅限整数"提示。

### P-03：章节数量无上限检查

- **位置**：[ConfigPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/ConfigPanel.tsx#L104) + [run.py](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/run.py#L692)
- **描述**：章节数量没有上限检查。用户可以输入 999999，服务端会接受这个值。虽然无限模式的上限是 500（见 P-15），但有限模式没有上限。
- **影响**：如果用户输入超大数字，生成将运行很长时间，消耗大量 API 费用。
- **建议**：在前端和服务端添加合理的上限（如 1000 章）。

### P-04：API 地址和 API Key 不做 trim 处理

- **位置**：[ConfigPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/ConfigPanel.tsx#L89-L90)
- **描述**：`localBaseUrl` 和 `localApiKey` 在赋值时不做 trim。如果用户复制粘贴时带有多余空格，API 请求会失败。
- **影响**：可能导致 API 请求 URL 或 Authorization header 包含多余空格，造成 401/404 错误。
- **建议**：在 `handleStart` 中对 `localBaseUrl` 和 `localApiKey` 做 trim。

### P-05：'planning' 章节状态在服务端从未使用

- **位置**：[types.ts](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/types.ts#L20) vs [run.py](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/run.py#L228)
- **描述**：类型定义中 Chapter.status 包含 'planning'，前端 GeneratingPanel 也检查了这个状态（显示"生成大纲中"），但服务端 `run_generation_job` 的流程是 `pending → writing → completed/error`，从未设置 'planning' 状态。
- **影响**：用户永远看不到"生成大纲中"的提示。前端的 planning 相关 UI 代码是死代码。
- **建议**：在服务端规划阶段（API 请求 plan 之前）设置章节状态为 'planning'，让用户能看到更细粒度的进度。

### P-06：无限模式进度条始终为 0%

- **位置**：[GeneratingPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/GeneratingPanel.tsx#L43)
- **描述**：`novelConfig.chapterCount > 0 ? Math.min(100, ...) : 0`。当 chapterCount = 0（无限模式）时，进度始终为 0%。
- **影响**：无限模式下进度条没有视觉反馈，用户无法感知生成进度。
- **建议**：无限模式下可以用动态目标（如已完成章节数 / max(50, 已完成) * 100）来显示进度。

### P-07：停止生成无确认对话框

- **位置**：[GeneratingPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/GeneratingPanel.tsx#L143)
- **描述**：点击"停止生成"按钮直接执行 `handleStop()`，没有确认对话框。正在写作的章节内容会被清空。
- **影响**：用户可能误触停止按钮，导致正在生成的章节内容丢失（特别是规划阶段的大纲）。
- **建议**：添加确认对话框："确定要停止生成吗？当前正在写作的章节内容将被清空。"

### P-08：重新生成整本小说无确认对话框

- **位置**：[GeneratingPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/GeneratingPanel.tsx#L153)
- **描述**：点击"重新生成"按钮直接执行 `handleRegenNovel()`，所有已完成章节会被清空。没有确认对话框。
- **影响**：如果用户已完成大量章节，误触"重新生成"将导致所有内容丢失，且无法恢复。
- **建议**：添加确认对话框："确定要重新生成吗？所有已完成的 X 章内容将被清空。"

### P-09：侧边栏非 completed 章节点击无视觉反馈

- **位置**：[Sidebar.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/Sidebar.tsx#L59-L63)
- **描述**：非 completed 章节的样式中没有 `cursor-pointer` 或 `hover` 效果，用户点击后没有任何视觉反馈，可能误以为功能故障。
- **影响**：用户体验不佳。
- **建议**：为非 completed 章节添加 `cursor-not-allowed` 或禁用状态的视觉提示。

### P-10：移动端侧边栏点击章节后不自动关闭

- **位置**：[Sidebar.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/Sidebar.tsx#L12-L18)
- **描述**：`handleChapterClick` 函数设置了章节 ID 和视图，但没有关闭移动端覆盖层（`setMobileOpen(false)`）。用户点击章节后需要手动关闭覆盖层。
- **影响**：移动端用户体验不佳，覆盖层遮挡阅读内容。
- **建议**：在 `handleChapterClick` 中添加 `setMobileOpen(false)` 或 `setSidebarCollapsed(true)`。

### P-11：API 失败无自动退避重试

- **位置**：[run.py](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/run.py#L459-L461)
- **描述**：当 API 请求失败时（如 429 频率限制），服务端直接将状态设为 'error' 并停止生成线程。没有指数退避重试机制。
- **影响**：遇到临时性错误（如频率限制、网络抖动）时，生成会立即停止，需要用户手动点击"继续生成"。
- **建议**：添加自动重试逻辑（最多 3 次，指数退避），只在重试全部失败后才设为 error。

### P-12：网络断开无前端提示

- **位置**：[GeneratingPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/GeneratingPanel.tsx#L32)
- **描述**：轮询请求失败时 catch 为空，静默忽略。用户不知道网络已断开。
- **影响**：用户可能以为生成正在进行，实际上已经断开连接。
- **建议**：添加网络状态检测，连续失败 N 次后显示"网络连接中断"提示。

### P-13：生成线程与停止/重新生成的竞态条件

- **位置**：[run.py](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/run.py#L232-L235)
- **描述**：生成线程通过 `cancel_events[novel_id].is_set()` 检查是否应该停止。但检查点只在特定位置（每章开始前和 API 调用前后）。如果用户在 API 调用期间点击停止/重新生成，旧线程可能在 cancel 检查之间写入章节数据。
- **影响**：低概率下可能出现章节数据冲突（旧线程写入的数据覆盖新线程的数据）。
- **建议**：在 update_novel 时检查 cancel_event 状态，或使用更细粒度的锁。

### P-14：API Key 明文存储在磁盘

- **位置**：[run.py](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/run.py#L59-L60)
- **描述**：API Key 以明文 JSON 格式存储在 `data/api_keys.json` 文件中。
- **影响**：任何能访问服务器文件系统的人都可以读取 API Key。
- **建议**：至少做 Base64 编码或使用系统密钥环存储。对于个人使用的本地工具，当前方案可接受。

### P-15："无限模式"实际最多 500 章

- **位置**：[run.py](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/run.py#L244)
- **描述**：`target = chapter_count if chapter_count and chapter_count > 0 else 500`。当 chapterCount = 0 时，target 被设为 500。也就是说"无限模式"实际上是"最多 500 章"。
- **影响**：用户期望无限生成，但到 500 章时会自动停止（状态变为 completed）。
- **建议**：将 500 改为一个更大的数字（如 9999），或在 UI 中明确说明"无限模式"的实际限制。

### P-16：前端与服务端 API 超时不匹配

- **位置**：[api.ts](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/utils/api.ts#L3) vs [run.py](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/run.py#L203)
- **描述**：前端 `fetchWithTimeout` 超时为 60 秒，服务端 `api_request` 超时为 120 秒。如果 API 响应时间在 60-120 秒之间，前端会超时但服务端仍在等待。
- **影响**：前端可能显示超时错误，但服务端最终会成功写入章节。前端再次轮询时会获取到新数据，所以实际影响较小。
- **说明**：前端的 api.ts 实际上没有被使用（GenerationRunner 返回 null，生成逻辑完全在服务端），所以此问题仅影响理论分析。

### P-17：HistoryPanel 降级使用列表数据时缺少章节内容

- **位置**：[HistoryPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/HistoryPanel.tsx#L51-L57)
- **描述**：`openNovel` 中如果 fetch `/api/novels/{id}` 失败，会降级使用列表中的 `item` 数据。但列表数据的 chapters 只有元数据（id, title, status, wordCount），没有 content 和 plan。
- **影响**：如果进入阅读页面，章节内容会显示为空。
- **建议**：fetch 失败时显示错误提示，而非静默降级。

### P-18：Header "新作品"按钮在配置页面和书架页面隐藏

- **位置**：[Header.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/Header.tsx#L77)
- **描述**：`!isGenerating && view !== 'config' && view !== 'history'`。在配置页面和书架页面，Header 的"新作品"按钮不显示。
- **影响**：功能上不影响，因为这两个页面本身就有导航到配置页面的方式（书架页有"写新作品"按钮）。但可能让用户困惑为什么"新作品"按钮时有时无。
- **建议**：可以考虑始终显示此按钮，或在 UI 上做更清晰的说明。

### P-19：生成页面的"配置"按钮不清除当前小说上下文

- **位置**：[GeneratingPanel.tsx](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/src/components/GeneratingPanel.tsx#L158)
- **描述**：点击"配置"按钮后 `setView('config')`，但 store 中的 `novelConfig` 和 `apiConfig` 仍然保留当前小说的配置。用户在配置页面看到的是上一部小说的配置。
- **影响**：如果用户不修改直接点击"开始生成"，会用上一部小说的配置创建新小说。
- **说明**：这是设计选择（方便用户基于上次配置创建类似小说），但可能让用户困惑。

### P-20：服务端 continue 章节保留了 error 章节的内容但 wordCount 被重新计算

- **位置**：[run.py](file:///c:/Users/china/OneDrive/Desktop/SOLO/%E6%97%A0%E9%99%90%E7%94%9F%E6%88%90%E5%B0%8F%E8%AF%B4/run.py#L800-L803)
- **描述**：continue 操作中，error 章节的 content 被保留，但 wordCount 被重新计算为 `len(content.replace(' ', '').replace('\n', ''))`。
- **影响**：如果 error 章节的 content 包含部分生成的内容（如 API 返回了部分内容后失败），这些内容会被保留但状态变为 pending。下次生成时会覆盖这些内容。
- **说明**：这是预期行为，但用户可能会困惑为什么 pending 章节有内容。

---

## 附录：测试环境信息

- **前端**：React + Vite + Zustand + Tailwind CSS + Lucide Icons
- **后端**：Python HTTP Server (ThreadingMixIn)，默认端口 5025
- **数据存储**：本地 JSON 文件（data/ 目录）
- **API 兼容**：OpenAI Chat Completions API 格式

## 附录：快速测试流程

### 最小可用测试（5 分钟）

1. 打开网页 → 看到空书架
2. 点击"开始创作" → 配置页面
3. 不输入主题 → 点击开始 → Toast 错误
4. 输入主题 → 不输入 API Key → Toast 错误
5. 输入主题 + API Key → 点击开始 → 跳转生成页
6. 等待第一章完成 → 点击章节 → 进入阅读
7. 点击中间区域 → 控制面板弹出
8. 点击"书架" → 回到书架 → 看到小说卡片

### 完整功能测试（30 分钟）

1. 完成最小可用测试
2. 在配置页面测试所有输入边界（空、0、负数、超大数、特殊字符）
3. 测试 4 种预设提示词
4. 测试停止/继续/重新生成流程
5. 测试阅读页面的键盘、触摸、点击操作
6. 测试书架的删除功能
7. 测试导出 TXT 功能
8. 测试移动端响应式布局（侧边栏、按钮文字隐藏）
9. 测试服务器重启后的自动恢复
