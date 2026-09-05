# 心程导航（Mood Guardian）

一个面向个人用户的情绪管理与生活辅助 Web 应用。用户可以记录每日心情与日记，系统借助 DeepSeek 大模型分析情绪与事件，并通过统计图表、周报/月报呈现情绪变化；同时支持日程管理、电影片单与书单管理，以及根据近期心情、空闲时间和个人偏好生成个性化的治愈建议。

## 技术栈

- **后端**：Python 3.10 + FastAPI + SQLAlchemy + SQLite
- **前端**：Vue 3 + Vite + Element Plus + ECharts
- **AI 服务**：DeepSeek Chat API
- **统计分析**：SciPy

## 主要功能

- 用户注册、登录与 JWT 认证
- 心情日记的增删改查与情绪/事件标签
- AI 情绪与事件分析
- 心情统计与标签关联性检验
- 周报 / 月报
- 日程管理
- 治愈助手推荐（电影 / 读书 / 运动 / 放松）
- 电影片单与书单管理、评价
- 个人偏好与多主题切换

## 环境要求

- Python 3.10 及以上
- Node.js 18 及以上
- （生产环境）Linux + Nginx
- SQLite 无需单独安装

## 本地开发部署

### 1. 部署后端

进入后端目录：

```bash
cd backend
```

创建并激活虚拟环境：

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

配置必需的环境变量（`SECRET_KEY` 为 JWT 签名密钥，必须设置）：

```bash
# Windows PowerShell
$env:SECRET_KEY = "请替换为足够长的随机密钥"

# macOS / Linux
export SECRET_KEY="请替换为足够长的随机密钥"
```

启动后端：

```bash
uvicorn main:app --reload
```

> 注意：请务必在 `backend` 目录下启动后端。数据库使用相对路径 `sqlite:///./mood.db`，首次启动会自动创建 `mood.db` 及全部数据表。

后端默认运行在 `http://127.0.0.1:8000`，接口文档位于 `http://127.0.0.1:8000/docs`。

### 2. 部署前端

进入前端目录：

```bash
cd frontend
```

安装依赖：

```bash
npm install
```

启动开发服务器：

```bash
npm run dev
```

前端默认运行在 `http://localhost:5173`（若端口被占用会自动切换到 5174），开发环境下 `/api` 请求会由 Vite 代理转发到本地后端 `http://127.0.0.1:8000`。

## 环境变量说明

| 变量名 | 是否必需 | 说明 |
|---|---|---|
| `SECRET_KEY` | 必需 | JWT 签名密钥，生产环境务必使用足够长的随机字符串 |
| `DEEPSEEK_API_KEY` | 可选 | DeepSeek API 密钥；未设置时情绪分析返回默认结果、推荐接口使用本地规则兜底 |
| `CORS_ORIGINS` | 可选 | 允许跨域的前端来源，逗号分隔；默认已包含 localhost:5173 / 5174 |

## 生产环境部署

### 1. 构建前端

```bash
cd frontend
npm install
npm run build
```

构建产物位于 `frontend/dist`。

### 2. 部署后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

在 `backend/.env` 中写入环境变量（例如）：

```bash
SECRET_KEY=请替换为足够长的随机密钥
DEEPSEEK_API_KEY=你的DeepSeek密钥
```

启动后端（建议使用 systemd 托管）：

```bash
venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. 配置 Nginx

将 `frontend/dist` 作为静态目录，并将 `/api`、`/docs`、`/static` 反向代理到后端 8000 端口。参考配置见 `deploy/mood-guardian.conf`，核心内容：

```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    root /var/www/mood_guardian/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000;
    }

    location /static/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

检查并重载 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4. systemd 服务（推荐）

创建 `/etc/systemd/system/mood-guardian.service`：

```ini
[Unit]
Description=Mood Guardian FastAPI Service
After=network.target

[Service]
User=你的用户名
WorkingDirectory=/var/www/mood_guardian/backend
EnvironmentFile=/var/www/mood_guardian/backend/.env
ExecStart=/var/www/mood_guardian/backend/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable mood-guardian
sudo systemctl start mood-guardian
```

## 项目目录结构

```text
mood_guardian/
├── backend/                 # 后端 FastAPI
│   ├── main.py              # 应用入口，注册路由、CORS、初始化数据库
│   ├── database.py          # SQLAlchemy 引擎与会话
│   ├── models.py            # ORM 数据模型
│   ├── schemas.py           # Pydantic 请求/响应模型
│   ├── utils.py             # 空闲时间计算等工具
│   ├── recommendation_catalog.py  # 电影/书籍/运动/放松资源
│   ├── requirements.txt     # 后端依赖
│   ├── static/              # Swagger UI 本地静态资源
│   └── routers/             # 各功能路由
├── frontend/                # 前端 Vue 3
│   ├── package.json
│   ├── vite.config.js
│   └── src/                 # 页面、组件、API 封装等
├── deploy/
│   └── mood-guardian.conf   # Nginx 配置示例
└── DESIGN_SPEC.md           # 设计规范
```

## 使用说明

启动后打开前端页面，使用用户名和密码注册或登录，即可开始记录心情日记、查看统计报告、管理日程、使用治愈助手和管理片单书单。
