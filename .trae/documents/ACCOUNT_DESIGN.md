# 账号系统 + 数据库 — 设计稿

## 一、目标

1. 用户注册/登录，密码保护
2. 每个用户的数据完全隔离（小说、API 配置）
3. API 配置存储在用户账号中，无需重复输入
4. 使用 SQLite 替代 JSON 文件存储
5. 清理所有现有数据，干净部署

## 二、技术选型

| 组件 | 方案 | 理由 |
|------|------|------|
| 数据库 | SQLite | Python 内置，无需安装，单文件 |
| 密码哈希 | hashlib.sha256 + salt | Python 内置，无需安装 |
| 认证 | 自定义 token（uuid4） | 简单有效，无需 JWT 库 |
| 前端存储 | localStorage 存 token | 与现有架构一致 |

## 三、数据库 Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    api_config TEXT DEFAULT '{}',  -- JSON: baseUrl, apiKey, model, systemPrompt
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE novels (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    theme TEXT NOT NULL,
    chapter_count INTEGER DEFAULT 0,
    words_per_chapter INTEGER DEFAULT 3000,
    status TEXT DEFAULT 'generating',
    error TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE chapters (
    id INTEGER NOT NULL,
    novel_id TEXT NOT NULL,
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    word_count INTEGER DEFAULT 0,
    plan TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    PRIMARY KEY (novel_id, id),
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);
```

## 四、API 设计

### 4.1 认证相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册 {username, password} |
| POST | /api/auth/login | 登录 {username, password} → token |
| POST | /api/auth/logout | 登出（使 token 失效） |
| GET | /api/auth/me | 获取当前用户信息 |

### 4.2 认证机制

- 注册/登录成功后返回 token
- 前端将 token 存入 localStorage
- 所有 API 请求在 Header 中携带 `Authorization: Bearer <token>`
- 后端验证 token，提取 user_id

### 4.3 小说相关（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/novels | 获取当前用户的小说列表 |
| GET | /api/novels/{id} | 获取当前用户的小说详情 |
| POST | /api/novels | 创建小说（使用用户的 API 配置） |
| POST | /api/novels/delete | 删除当前用户的小说 |
| POST | /api/novels/regenerate | 重新生成 |
| POST | /api/novels/continue | 继续生成 |
| POST | /api/novels/stop | 停止生成 |
| POST | /api/novels/regenerate-chapter | 重新生成某章 |

### 4.4 用户配置（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/user/config | 获取用户的 API 配置 |
| PUT | /api/user/config | 更新用户的 API 配置 |

## 五、前端变更

### 5.1 新增页面

- **登录页面**：用户名 + 密码输入框 + 登录/注册切换
- 首次打开如果没有 token，显示登录页面

### 5.2 修改现有页面

- **ConfigPanel**：API 配置从用户账号加载，创建小说时使用用户的 API 配置
- **Header**：显示用户名 + 登出按钮

### 5.3 认证流程

```
用户打开网页
├── localStorage 有 token？
│   ├── 是 → 调用 /api/auth/me 验证
│   │   ├── 有效 → 显示书架
│   │   └── 无效 → 清除 token，显示登录页
│   └── 否 → 显示登录页
└── 登录/注册
    ├── 成功 → 存储 token，跳转书架
    └── 失败 → 显示错误
```

## 六、数据迁移

- 现有 JSON 数据不迁移（用户要求清理）
- 删除 `data/` 目录下所有文件
- 删除 `api_keys.json`
- 数据库文件：`data/novelgen.db`

## 七、部署

- 首次运行自动创建数据库
- 无需手动初始化
- `data/` 目录在 `.gitignore` 中

## 八、实施顺序

1. 修改 `run.py` — 添加 SQLite 数据库层 + 认证中间件 + 修改所有 API
2. 修改前端 — 添加登录页面 + 认证集成 + API 配置存储
3. 清理数据 + 编写部署手册
4. 测试 + 推送
