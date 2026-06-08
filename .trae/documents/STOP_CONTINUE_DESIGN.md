# 停止生成 / 继续生成 / 重新生成 — 设计稿

## 一、当前问题

### 问题1：停止生成后，正在写的章节被标记为 error
- 用户点击"停止生成" → 后端将 writing/planning 章节标记为 error
- 用户看到红色错误状态，以为是程序出错
- 实际只是用户主动停止，不应该显示为错误

### 问题2：停止后无法干净地继续
- "继续生成"按钮的逻辑是：跳过 error 章节，从下一个未完成章节开始
- 但停止时章节已被标记为 error，继续时这些章节被跳过
- 用户期望：停止 = 暂停，继续 = 从暂停处继续

### 问题3：重新生成整本时，章节列表瞬间清空
- 用户点击"重新生成" → chapters 清空 → 页面显示"正在准备生成..."
- 用户看不到任何进度，直到第一个章节生成完成

### 问题4：三个按钮（停止/继续/重新生成）的逻辑混乱
- "继续生成"只在有错误或未完成时显示
- "重新生成"清空所有章节重来
- 用户分不清"继续"和"重新生成"的区别

---

## 二、设计目标

用一句话描述：**像视频播放器一样控制小说生成**

- **开始生成** = 播放
- **停止生成** = 暂停（保留进度）
- **继续生成** = 继续播放（从暂停处继续）
- **重新生成** = 从头播放（清空进度）

---

## 三、章节状态机

```
pending → planning → writing → completed
  ↑         ↓          ↓
  +---------+----------+--- (停止时，writing/planning 回到 pending)
  
pending → error (API 失败时)
error → pending (继续生成时，清除错误，重新尝试)
```

### 状态说明
| 状态 | 含义 | 显示 |
|------|------|------|
| `pending` | 等待生成 | 灰色，显示"等待生成" |
| `planning` | 正在规划大纲 | 黄色旋转图标 |
| `writing` | 正在写正文 | 黄色旋转图标 |
| `completed` | 已完成 | 绿色，显示字数 |
| `error` | 生成失败（API 错误等） | 红色，显示错误原因 |

---

## 四、按钮逻辑

### 4.1 顶部按钮区域

```
[书架] [阅读] [停止/继续] [重新生成] [配置]
```

| 条件 | 显示的按钮 |
|------|-----------|
| 正在生成中 | [书架] [停止生成] |
| 已停止/已完成，有未完成章节 | [书架] [阅读] [继续生成] [重新生成] [配置] |
| 已完成，所有章节完成 | [书架] [阅读] [重新生成] [配置] |
| 刚打开，无章节 | [书架] [重新生成] [配置] |

### 4.2 按钮行为

#### 停止生成
- 前端：调用 `POST /api/novels/stop`
- 后端：
  1. 将 `writing`/`planning` 状态的章节**恢复为 `pending`**（不是 error）
  2. 设置小说状态为 `paused`（不是 completed）
  3. 触发 cancel_events 停止后台线程
- 前端更新：状态变为 `paused`，按钮切换为"继续生成"

#### 继续生成
- 前端：调用 `POST /api/novels/continue`
- 后端：
  1. 将 `error` 状态的章节恢复为 `pending`（给失败章节一次重试机会）
  2. 设置小说状态为 `generating`
  3. 启动生成任务
- 生成任务：从第一个非 `completed` 章节开始生成

#### 重新生成
- 前端：调用 `POST /api/novels/regenerate`
- 后端：
  1. 清空所有章节
  2. 设置小说状态为 `generating`
  3. 启动生成任务
- 生成任务：从第1章开始生成

---

## 五、后端 API 变更

### 5.1 `POST /api/novels/stop`

```python
# 当前实现（有bug）：
for c in novel.get('chapters', []):
    if c.get('status') in ('writing', 'planning'):
        c['status'] = 'error'  # ← 错误！应该恢复为 pending
novel['status'] = 'completed'  # ← 错误！应该设为 paused

# 新实现：
for c in novel.get('chapters', []):
    if c.get('status') in ('writing', 'planning'):
        c['status'] = 'pending'  # ← 恢复为等待状态
        c['content'] = ''        # ← 清空半成品内容
        c['wordCount'] = 0
novel['status'] = 'paused'       # ← 新状态：已暂停
novel['error'] = ''
```

### 5.2 `POST /api/novels/continue`

```python
# 当前实现：
for c in novel.get('chapters', []):
    if c.get('status') in ('writing', 'planning'):
        c['status'] = 'error'

# 新实现：
for c in novel.get('chapters', []):
    if c.get('status') in ('error', 'writing', 'planning'):
        c['status'] = 'pending'  # ← 所有异常状态都恢复为 pending
        c['content'] = c.get('content', '') or ''  # ← 保留已写内容
        c['wordCount'] = len(c.get('content', '').replace(' ', '').replace('\n', ''))
novel['status'] = 'generating'
```

### 5.3 `POST /api/novels/regenerate`

不变，清空所有章节，从头开始。

### 5.4 `run_generation_job` 变更

当前逻辑：
```python
chapters = [c for c in chapters if c.get('status') != 'error']
chapter_num = len(chapters) + 1
```

新逻辑：
```python
# 不删除 error 章节，而是找到第一个未完成的章节
pending_chapters = [c for c in chapters if c.get('status') != 'completed']
if not pending_chapters:
    # 所有章节都完成了
    update_novel(novel_id, lambda n: n.update({'status': 'completed'}))
    break

# 从第一个 pending 章节开始
chapter_num = pending_chapters[0]['id']
```

### 5.5 小说状态枚举

```python
# 当前：
'generating' | 'completed' | 'error'

# 新增：
'generating' | 'completed' | 'error' | 'paused'
```

---

## 六、前端变更

### 6.1 `GeneratingPanel.tsx`

#### 按钮逻辑重写
```tsx
// 正在生成中 → 显示停止按钮
{isGenerating && (
  <button onClick={handleStop}>停止生成</button>
)}

// 已暂停或已完成，有未完成章节 → 显示继续按钮
{!isGenerating && hasUncompletedChapters && (
  <button onClick={handleContinue}>继续生成</button>
)}

// 非生成中 → 显示重新生成和配置按钮
{!isGenerating && (
  <button onClick={handleRegenNovel}>重新生成</button>
  <button onClick={() => setView('config')}>配置</button>
)}
```

#### 状态判断
```tsx
const isGenerating = remote?.status === 'generating';
const isPaused = remote?.status === 'paused';
const hasUncompletedChapters = localChapters.some(c => c.status !== 'completed');
```

### 6.2 `types.ts`

```typescript
// 当前：
status: 'generating' | 'completed' | 'error'

// 新增：
status: 'generating' | 'completed' | 'error' | 'paused'
```

### 6.3 `HistoryPanel.tsx`

书架页面需要识别 `paused` 状态：
```tsx
// 当前：
if (item.status === 'generating' || item.status === 'error') {
  setView('generating');
} else {
  setView('reading');
}

// 新增 paused：
if (item.status === 'generating' || item.status === 'error' || item.status === 'paused') {
  setView('generating');
} else {
  setView('reading');
}
```

### 6.4 `Sidebar.tsx`

侧边栏章节列表需要显示 `pending` 状态：
```tsx
case 'pending':
  return <div className="w-2 h-2 rounded-full bg-ink-600" />;
```

### 6.5 章节卡片样式（GeneratingPanel）

```tsx
chapter.status === 'pending' ? 'bg-ink-900/20 border-ink-800/30' :
chapter.status === 'writing' ? 'bg-gold-400/5 border-gold-400/20' :
chapter.status === 'completed' ? 'bg-ink-900/50 border-ink-800' :
chapter.status === 'error' ? 'bg-red-500/5 border-red-500/20' :
```

---

## 七、用户操作流程

### 场景1：正常生成
1. 用户输入主题，点击"开始生成"
2. 章节列表立即出现第1章（status=pending→planning→writing→completed）
3. 第1章完成后，第2章自动开始
4. 所有章节完成，状态变为 completed

### 场景2：停止后继续
1. 生成到第5章时，用户点击"停止生成"
2. 第5章状态从 writing 恢复为 pending
3. 小说状态变为 paused
4. 按钮变为"继续生成"
5. 用户点击"继续生成"
6. 小说状态变为 generating
7. 从第5章（第一个 pending）开始继续生成

### 场景3：停止后重新生成
1. 用户停止生成
2. 用户点击"重新生成"
3. 所有章节清空，从第1章重新开始

### 场景4：API 失败后继续
1. 生成到第5章时，API 返回错误
2. 第5章状态变为 error，小说状态变为 error
3. 用户看到错误信息和"继续生成"按钮
4. 用户点击"继续生成"
5. 第5章状态从 error 恢复为 pending
6. 从第5章重新尝试生成

### 场景5：书架打开已暂停的小说
1. 用户在书架看到"已暂停"的小说
2. 点击进入生成页面
3. 看到已完成的章节 + pending 章节
4. 点击"继续生成"继续

---

## 八、实施顺序

1. 修改 `types.ts` — 添加 'paused' 状态类型
2. 修改 `run.py` — stop/continue/生成逻辑
3. 修改 `GeneratingPanel.tsx` — 按钮逻辑和状态显示
4. 修改 `HistoryPanel.tsx` — 识别 paused 状态
5. 修改 `Sidebar.tsx` — 显示 pending 状态
6. 构建测试
