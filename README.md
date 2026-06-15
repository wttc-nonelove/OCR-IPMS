# 智能项目管理系统（OCR-IPMS）

智能项目管理系统是一个面向项目立项、合同解析、开票回款、结项审批和统计报表的 Web 系统。当前版本为最终课程设计版，采用 Vue 3 + Element Plus、FastAPI、MySQL 8.0、PaddleOCR 和 Docker Compose 实现。

## 核心能力

- 多角色协同：管理员、商务、财务、项目经理。
- 管理员超级权限：管理员可访问并处理其他角色的业务任务。
- 合同智能解析：`.doc/.docx` 走文档解析，PDF/图片走 OCR；弱标识合同可通过 LLM 兜底解析。
- 合同编号可为空：项目编号、招标编号、采购编号不会被误当作合同编号。
- 合同差异确认：保存登记值、识别值、人工采用值、确认人、确认时间和备注。
- 开票回款台账：发票识别税率、税额、不含税金额、价税合计；回款按项目级累计校验。
- 项目级回款规则：累计回款金额不得超过该项目累计开票价税合计。
- 结项审批：项目经理提交结项，财务审批通过后项目变为已结项，只读不可再开票。
- 查询报表：支持年度/月度趋势、发票回款明细和 Excel 浏览器下载。
- 系统配置：系统管理页支持多模型 LLM 配置、PaddleOCR 状态、审计日志和 OCR 日志查看。

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Element Plus、Pinia、Vue Router、Vite |
| 后端 | FastAPI、SQLAlchemy、Pydantic、JWT、BCrypt |
| 数据库 | MySQL 8.0 |
| OCR | 独立 PaddleOCR HTTP 服务，PDF 先转图片再识别 |
| LLM | OpenAI 兼容接口，可在系统管理页配置多个模型 |
| 导出 | openpyxl 生成 `.xlsx`，运行时任务队列维护 |
| 部署 | Docker Compose，前端 Nginx，后端 Uvicorn |

## 目录结构

```text
backend/              FastAPI 后端服务
frontend/             Vue 3 前端应用
paddleocr/            OCR 独立服务
prototype/            HTML 原型
uploads/              本地上传文件目录
backend/alembic/      数据库迁移脚本
docker-compose.yml    容器编排配置
```

## 快速启动

```powershell
cd F:\课设\OCR-NLP
docker compose up -d --build
```

启动后访问：

- 前端系统：`http://localhost`
- 后端健康检查：`http://localhost:8000/health`
- 后端接口文档：`http://localhost:8000/docs`
- OCR 健康检查：`http://localhost:8001/health`

## 默认账号

默认账号密码均为 `123456`。

| 身份 | 用户名 |
|---|---|
| 管理员 | `admin` |
| 商务 | `business01` |
| 财务 | `finance01` |
| 项目经理 | `pm01` |

## 常用命令

```powershell
# 重建并启动
docker compose up -d --build

# 仅重建前后端
docker compose up -d --build backend frontend

# 查看容器状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 后端测试
$env:PYTHONPATH='backend'; pytest -q

# 前端构建
cd frontend
npm.cmd run build
```

## 当前最终业务规则

- 项目编号格式为 `PRJ-YYYY-NNNN`。
- 用户不支持多角色，一个用户仅绑定一个角色。
- 管理员是超级角色，可访问全部业务模块。
- 合同编号允许为空。
- `.doc/.docx` 合同通过文档解析，PDF/图片合同通过 PaddleOCR。
- 弱标识合同可启用 LLM 兜底解析，但规则明确识别到的总金额、甲乙方和日期优先。
- 发票号码全局唯一。
- 发票 `amount` 表示价税合计，`amount_without_tax` 表示不含税金额。
- 开票额度按不含税金额控制，不得超过合同金额。
- 回款不再强制关联具体发票，按项目级累计回款不超过累计开票价税合计控制。
- 导出任务不落库，只保存在运行时任务队列中。
- 不采用软删除；删除按业务规则和外键约束处理。
