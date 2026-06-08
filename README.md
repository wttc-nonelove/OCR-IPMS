# 智能项目管理系统

基于需求说明书、概要设计、数据库设计、详细设计和 HTML 原型实现的项目管理系统 MVP。

## 技术栈

- 前端：Vue 3 + Element Plus + Pinia + Vue Router
- 后端：FastAPI + SQLAlchemy + JWT + BCrypt
- 数据库：MySQL 8.0，开发默认也支持 SQLite
- 文件：本地 `uploads`
- OCR：后端内置占位解析服务，`paddleocr` 目录提供可替换服务壳

## 本地后端开发

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload
```

默认账号密码均为 `123456`：

- `admin`
- `business01`
- `finance01`
- `pm01`

## 本地前端开发

```powershell
cd frontend
npm install
npm run dev
```

## Docker 启动

```powershell
docker compose up --build
```

访问：

- 前端：http://localhost
- 后端健康检查：http://localhost:8000/health

## 当前实现边界

- 导出任务不落库，只保存在运行时队列中
- OCR/NLP 当前为本地占位实现，可替换为 PaddleOCR + 百度 OCR
- 不实现站内信、邮件、短信、自动催办、自动转交
- 不实现软删除
