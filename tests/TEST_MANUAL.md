# 无限生成小说 — 测试手册

## 1. 测试环境要求

### 1.1 软件环境
- Python 3.8+（仅使用标准库，无需安装额外依赖）
- Node.js（用于前端构建，服务器启动时自动处理）
- 操作系统：Windows / Linux / macOS

### 1.2 服务器启动
```bash
# 在项目根目录启动服务器（默认端口 5025）
python run.py

# 指定端口
python run.py 3000
```

### 1.3 验证服务器运行
```bash
curl http://127.0.0.1:5025/api/novels
```
返回 JSON 数组即表示服务器正常运行。

---

## 2. 测试脚本说明

### 2.1 边界测试 — `test_boundary.py`

**运行方式：**
```bash
python tests/test_boundary.py
```

**测试范围（36 个用例）：**

| 编号 | 分类 | 场景 |
|------|------|------|
| T01-T02 | GET /api/novels | 空数据、正常数据 |
| T03-T06 | GET /api/novels/{id} | 有效 id、无效 id、超长 id、特殊字符 id |
| T07-T14 | POST /api/novels | 空 body、缺少 theme、缺少 apiKey、负数 chapterCount、负数 wordsPerChapter、超大值、空字符串、Unicode 主题 |
| T15-T17 | POST /api/novels/stop | 缺少 id、无效 id、已暂停的小说 |
| T18-T20 | POST /api/novels/continue | 缺少 id、无效 id、已完成的小说 |
| T21-T23 | POST /api/novels/regenerate | 缺少 id、无效 id、正在生成的小说 |
| T24-T25 | POST /api/novels/regenerate-chapter | 缺少参数、无效参数 |
| T26-T28 | POST /api/novels/delete | 缺少 id、无效 id、有效小说 |
| T29-T30 | 并发 | 同时创建多个、同时删除和创建 |
| T31-T32 | 大 payload | 超长主题、超长系统提示词 |
| T33-T34 | 配置页面 | 零值、超大值 |
| T35-T36 | 书架页面 | 空书架、多本小说 |

**预期结果：**
- 所有用例应返回 PASS
- 测试完成后自动清理临时数据
- 输出格式化的测试报告（PASS/FAIL 统计）

### 2.2 压力测试 — `test_stress.py`

**运行方式：**
```bash
python tests/test_stress.py
```

**测试场景：**

| 测试 | 场景 | 参数 |
|------|------|------|
| 1 | 并发读取 | 10 / 50 / 100 / 500 并发 GET |
| 2 | 并发写入 | 10 / 50 / 100 并发 POST |
| 3 | 混合负载 | 200 请求，70% 读 + 30% 写 |
| 4 | 长连接 | 持续 30s 请求轰炸（10 并发） |
| 5 | 大文件读取 | 10 并发读取单本小说 |

**输出指标：**
- 总请求数 / 成功数 / 失败数
- 平均响应时间 / 最大响应时间
- P50 / P95 / P99 响应时间
- QPS（每秒查询数）
- 错误类型分布

---

## 3. 测试步骤

### 3.1 边界测试步骤

1. 启动服务器：`python run.py`
2. 等待服务器就绪（看到 "服务启动" 字样）
3. 运行边界测试：`python tests/test_boundary.py`
4. 观察输出，确认所有用例 PASS
5. 如有 FAIL，查看报告中的"预期"和"实际"列

### 3.2 压力测试步骤

1. 启动服务器：`python run.py`
2. 运行压力测试：`python tests/test_stress.py`
3. 等待所有测试完成（约 2-3 分钟）
4. 记录各场景的性能指标

### 3.3 手动测试步骤

#### 配置页面测试
1. 打开浏览器访问 `http://127.0.0.1:5025`
2. 在配置页面输入以下边界值：
   - 章节数：留空、0、-1、999999
   - 每章字数：留空、0、-1、999999
   - 主题：空字符串、超长字符串（10000+ 字符）、Unicode 字符
3. 观察前端验证是否正确拦截

#### 生成页面测试
1. 创建一个新小说（章节数=1，字数=100）
2. 观察生成进度
3. 测试暂停/继续功能
4. 测试重新生成功能

#### 阅读页面测试
1. 等待小说生成完成
2. 点击章节阅读
3. 测试章节切换
4. 测试空章节、超长章节的显示

#### 书架页面测试
1. 创建多本小说（5-10 本）
2. 刷新页面，确认列表正确
3. 测试删除功能
4. 测试搜索/筛选功能（如有）

---

## 4. 预期结果说明

### 4.1 边界测试预期

| 测试类型 | 预期行为 |
|----------|----------|
| 缺少必填字段 | 返回 400，错误消息明确 |
| 无效 ID | 返回 404 |
| 负数值 | 自动修正为最小合法值（0 或 1） |
| 超大值 | 服务器接受（前端应做限制） |
| 空字符串 | 返回 400 |
| Unicode | 正确存储和返回 |
| 并发请求 | 无崩溃，数据一致 |
| 大 payload | 服务器不崩溃 |

### 4.2 压力测试预期

| 指标 | 可接受范围 |
|------|------------|
| 成功率 | ≥ 99%（低并发），≥ 95%（高并发） |
| 平均响应时间 | < 100ms（读），< 200ms（写） |
| P95 响应时间 | < 500ms |
| P99 响应时间 | < 1000ms |
| QPS | ≥ 100（读），≥ 50（写） |

---

## 5. 测试报告模板

```
======================================================================
  无限生成小说 — 测试报告
======================================================================
  测试日期: YYYY-MM-DD HH:MM:SS
  测试环境: Windows/Linux/macOS
  服务器版本: x.x.x
======================================================================

  边界测试结果:
  - 总计: 36
  - 通过: XX
  - 失败: XX
  - 通过率: XX.X%

  压力测试结果:
  - 并发读取 (500): QPS=XXX, P95=XXXms, 成功率=XX%
  - 并发写入 (100): QPS=XXX, P95=XXXms, 成功率=XX%
  - 混合负载: QPS=XXX, P95=XXXms, 成功率=XX%
  - 长连接 (30s): QPS=XXX, P95=XXXms, 成功率=XX%

  发现的问题:
  1. [问题描述]
  2. [问题描述]

  建议:
  1. [改进建议]
  2. [改进建议]

======================================================================
```

---

## 6. 已知限制和瓶颈分析

### 6.1 架构限制

| 限制 | 说明 | 影响 |
|------|------|------|
| 单进程 Python HTTP 服务器 | 使用 `BaseHTTPRequestHandler`，非异步 | 高并发下响应延迟增加 |
| JSON 文件存储 | 无数据库，每次读写都是文件 I/O | 大量数据时性能下降 |
| 全局锁 `store_lock` | 所有写操作串行化 | 写入吞吐量受限 |
| 无缓存层 | 每次请求都读取文件 | 重复读取性能差 |

### 6.2 性能瓶颈

1. **文件 I/O 瓶颈**
   - 每次 `save_history()` 都写入整个 `history.json`
   - 小说数量增加后，文件大小线性增长
   - 建议：引入 SQLite 或 LevelDB

2. **锁竞争**
   - `store_lock` 是全局 RLock
   - 并发写入时所有请求排队等待
   - 建议：细粒度锁或无锁数据结构

3. **内存使用**
   - 每个请求都会加载完整的小说数据
   - 大量章节的小说占用大量内存
   - 建议：分页加载，只返回必要字段

4. **生成任务管理**
   - 每个小说生成任务占用一个线程
   - 大量同时生成会耗尽线程池
   - 建议：任务队列 + 工作线程池

### 6.3 安全限制

| 风险 | 说明 | 建议 |
|------|------|------|
| 无认证 | API 无鉴权，任何人可访问 | 添加 API Key 或 JWT 认证 |
| 无速率限制 | 可被恶意请求淹没 | 添加速率限制中间件 |
| 路径遍历 | 特殊字符 ID 可能导致问题 | 严格验证 ID 格式 |
| XSS | 主题等字段未转义 | 前端输出时转义 |

### 6.4 扩展性建议

1. **短期优化**
   - 添加内存缓存（LRU Cache）
   - 使用 `asyncio` 替代线程
   - 历史记录分页加载

2. **中期优化**
   - 迁移到 SQLite 数据库
   - 引入 Redis 缓存
   - 添加 API 速率限制

3. **长期优化**
   - 迁移到 FastAPI + PostgreSQL
   - 使用消息队列管理生成任务
   - 添加 WebSocket 实时推送

---

## 7. 常见问题

### Q1: 测试脚本无法连接服务器
**A:** 确保服务器已启动：`python run.py`，等待看到 "服务启动" 字样。

### Q2: 压力测试超时
**A:** 压力测试会产生大量请求，服务器处理需要时间。如持续超时，降低并发数。

### Q3: 测试数据会污染正式数据
**A:** 测试脚本使用 `__boundary_test_theme__` 和 `__stress_test_theme__` 前缀标识测试数据，测试完成后自动清理。

### Q4: Windows 下中文输出乱码
**A:** 在 PowerShell 中运行 `chcp 65001` 切换到 UTF-8 编码。

---

## 8. API 端点参考

| 方法 | 路径 | 说明 | 请求体 |
|------|------|------|--------|
| GET | /api/novels | 获取小说列表 | - |
| GET | /api/novels/{id} | 获取单本小说 | - |
| POST | /api/novels | 创建小说 | `{theme, apiConfig, novelConfig}` |
| POST | /api/novels/delete | 删除小说 | `{id}` |
| POST | /api/novels/stop | 暂停生成 | `{id}` |
| POST | /api/novels/continue | 继续生成 | `{id}` |
| POST | /api/novels/regenerate | 重新生成 | `{id}` |
| POST | /api/novels/regenerate-chapter | 重新生成章节 | `{novelId, chapterId}` |

### 请求体示例

**创建小说：**
```json
{
  "theme": "科幻冒险",
  "apiConfig": {
    "baseUrl": "https://api.openai.com/v1",
    "apiKey": "sk-xxx",
    "model": "gpt-4",
    "systemPrompt": ""
  },
  "novelConfig": {
    "chapterCount": 10,
    "wordsPerChapter": 3000
  }
}
```

**删除/暂停/继续/重新生成：**
```json
{
  "id": "novel_id_here"
}
```

**重新生成章节：**
```json
{
  "novelId": "novel_id_here",
  "chapterId": 1
}
```

---

## 9. 数据存储结构

### data/history.json
```json
[
  {
    "id": "novel_id",
    "theme": "主题",
    "status": "generating|completed|error|paused",
    "chapterCount": 10,
    "wordsPerChapter": 3000,
    "createdAt": "2024-01-01 00:00:00",
    "updatedAt": "2024-01-01 00:00:00",
    "error": "",
    "chapterMeta": [
      {"id": 1, "title": "第一章", "status": "completed", "wordCount": 3000}
    ]
  }
]
```

### data/novels/{id}.json
```json
{
  "id": "novel_id",
  "theme": "主题",
  "chapterCount": 10,
  "wordsPerChapter": 3000,
  "status": "generating",
  "createdAt": "2024-01-01 00:00:00",
  "updatedAt": "2024-01-01 00:00:00",
  "error": "",
  "chapters": [
    {
      "id": 1,
      "title": "第一章：开始",
      "content": "正文内容...",
      "wordCount": 3000,
      "plan": "本章大纲...",
      "status": "completed"
    }
  ]
}
```

### data/api_keys.json
```json
{
  "novel_id": {
    "baseUrl": "https://api.openai.com/v1",
    "apiKey": "sk-xxx",
    "model": "gpt-4",
    "systemPrompt": ""
  }
}
```

---

## 10. 变更记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-06-10 | 1.0 | 初始版本，包含 36 个边界测试用例和 5 个压力测试场景 |
