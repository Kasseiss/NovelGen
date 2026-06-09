# 墨流小说生成器 — 部署手册

## 快速部署

### 环境要求
- Python 3.8+
- 无需安装任何第三方依赖（全部使用 Python 标准库）

### 部署步骤

1. 克隆代码
   ```bash
   git clone https://github.com/Kasseiss/NovelGen.git
   cd NovelGen
   ```

2. 启动服务
   ```bash
   python run.py
   ```
   默认端口 3000，可通过参数指定：`python run.py 8080`

3. 打开浏览器访问 `http://localhost:3000`

### 首次使用
1. 注册账号
2. 配置 API（设置 API 地址、Key、模型名称）
3. 创建小说开始生成

### 数据存储
- 所有数据存储在 `data/novelgen.db`（SQLite 数据库）
- `data/` 目录在 `.gitignore` 中，不会被推送到 Git

### 重置部署
如需清除所有数据重新开始：
```bash
# 停止服务后执行
rm -rf data/novelgen.db
python run.py  # 会自动重新创建数据库
```

### 功能说明
- **用户注册/登录**：密码加密存储，每个用户数据完全隔离
- **API 配置**：保存在用户账号中，无需重复输入
- **小说生成**：支持无限模式和指定章节数模式
- **停止/继续/重新生成**：支持暂停、续写、重头开始
- **单章重新生成**：支持重新生成指定章节
- **导出**：支持导出为 TXT 文件
