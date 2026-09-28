# Xinghan Lead Factory V1

广东星汉实业有限公司海外 B2B 潜客发现与评分系统。本地运行，采集公开企业网页，完成去重、规则评分、产品匹配和人工审核。系统**不会自动发送邮件、WhatsApp 或其他外联消息**。

## 快速开始（Windows）

前置条件：Windows 10/11、PowerShell、Python 包管理器 `uv`、Node.js 20+。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/seed-demo.ps1
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

打开 http://127.0.0.1:3000 。停止服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop.ps1
```

演示数据带 `[Demo]` 标签，使用保留的 `.invalid` 域名，不会与真实客户域名冲突；重复执行 seed 不会重复插入。

## 配置

首次 setup 会从 `.env.example` 生成不会提交到 Git 的 `.env`。默认配置使用 SQLite 和纯规则模式，无需任何 API Key。

- `LF_DATABASE_URL`：默认 `sqlite+pysqlite:///./data/lead_factory.db`。生产 PostgreSQL 可改为 `postgresql+psycopg://user:password@host/database`，并安装相应驱动。
- `LF_AI_PROVIDER=disabled`：稳定、零模型成本的默认模式。
- `LF_AI_PROVIDER=openai`、`LF_AI_API_KEY`、`LF_AI_MODEL`：可选 AI 补充。缺 Key 或调用失败时回退到规则结果。
- `NEXT_PUBLIC_API_URL`：前端 API 地址，默认 `http://127.0.0.1:8000/api/v1`。

ICP、评分、抓取与产品匹配规则位于 `config/`；AI 提示词位于 `config/prompts/`，修改后可版本管理和审阅。

## 使用流程

1. 在 Search Tasks 中选择 ICP、国家、关键词或公开 seed URL，并设置本次上限。
2. 系统只读取无需登录的公开网页，遵守 URL 安全校验、robots 指令、域名延迟、页面/域名/AI 调用预算和响应体上限。
3. 在 Dashboard 和 A/B/C Leads 查看优先级；在 Account Detail 查看每个分数和产品推荐的来源证据。
4. 人工标记 Approved、Rejected 或 Needs Review。审核只更新本地记录，不触发外联。

避免抓取个人邮箱、绕过登录或验证码、突破网站条款，或用结果进行未经同意的批量营销。实际运营前应按目标国家审查隐私、电子营销与数据留存要求。

## 验证与日志

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
npm --prefix apps/web run test:e2e
```

端到端测试首次运行前可执行 `npx playwright install chromium`。运行日志位于 `logs/api.log` 和 `logs/web.log`；日志会隐藏常见密钥字段。健康检查：`/api/v1/health`，就绪检查：`/api/v1/readiness`。

## 成本与频率控制

每个搜索任务均有最大结果、页面、域名和 AI 调用预算；爬虫按域名限速、限制跳转与下载大小。建议从 10–20 个候选域名的小任务开始，确认信号质量后再逐步增加。纯规则模式的模型成本为零。

## 常见问题

- 页面显示 API unavailable：确认 `scripts/dev.ps1` 已运行，并查看 `logs/api.log`。
- SQLite 无法打开：确认项目根目录存在 `data/`，或重新运行 setup。
- AI 未启用：这是默认安全状态；只有在 `.env` 显式配置 provider 和 Key 后才启用。
- 抓取被跳过：目标可能拒绝 robots、解析到私网地址、响应过大、内容类型不允许，或任务预算已用完。
- 端口被占用：先运行 `scripts/stop.ps1`，或修改 `.env` 中端口并同步前端 API 地址。
