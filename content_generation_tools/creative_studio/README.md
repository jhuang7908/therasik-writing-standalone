# Creative Studio (MVP)

面向中国商业客户的 **AI 图文并茂文件生成平台**。
与 InSynBio / Therasik 主业务**完全隔离**（独立网络 `creative_studio_net`，独立容器，独立端口 8100）。

> 核心理念：**图文分离** — AI 写内容 + 多模型生背景图 + 代码精准排版 + 导出**可编辑**文件。

---

## 目录结构

```text
creative_studio/
├── app/                          # FastAPI 后端
│   ├── main.py                   # 应用入口 + CORS
│   ├── config.py                 # Pydantic Settings (reads .env)
│   ├── db.py                     # SQLAlchemy session
│   ├── models.py                 # ORM: User, Job, UsageLedger, CreditOrder
│   ├── auth.py                   # JWT + bcrypt
│   └── routers/
│       ├── auth.py               # /api/auth/register|login|me
│       ├── jobs.py               # /api/jobs CRUD + Celery dispatch
│       ├── templates.py          # /api/templates list + get
│       └── webhooks.py           # /api/webhooks/stripe|wechat (payment)
├── worker/
│   ├── tasks.py                  # Celery app + run_generation_task
│   ├── llm_router.py             # DeepSeek → GPT-4o-mini → Claude fallback chain
│   └── image_router.py           # stock | standard (gpt-image-1) | premium (gpt-image-2)
├── renderer/
│   ├── ppt_renderer.py           # ContentDoc → editable .pptx
│   └── html_renderer.py          # ContentDoc → styled HTML (XHS / WeChat / Whitepaper)
├── schemas/
│   ├── content_doc.schema.json   # JSON Schema (Draft 2020-12)
│   ├── content_doc.py            # Pydantic v2 ContentDoc model
│   ├── example_ppt.json          # PPT 示例
│   ├── example_xhs.json          # 小红书示例
│   └── _validate.py              # 校验脚本
├── templates/                    # 20 套模板 JSON (8 PPT + 5 XHS + 4 WeChat + 3 WP)
│   └── _generate_templates.py    # 生成脚本
├── docs/
│   ├── TECH_SPEC.md              # MVP 技术方案书
│   ├── CONTENT_PROTOCOL.md       # JSON 内容协议说明
│   └── PPTX_TEMPLATE_SPEC.md     # python-pptx 模板规范
├── ui_prototype/
│   └── console.html              # 三栏布局 UI 原型（纯静态）
├── outputs/                      # 生成文件输出目录
├── Dockerfile.api                # API + Worker 共用镜像
├── docker-compose.yml            # 一键启动 (API + Worker + Flower + Postgres + Redis)
├── requirements.txt              # Python 依赖
└── .env.example                  # 环境变量模板
```

---

## 快速启动（本地开发）

### 1. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY
```

### 2. Docker Compose 一键启动

```bash
docker compose up --build -d
```

服务就绪后：
- API:    http://localhost:8100/api/health
- API 文档 (debug only): http://localhost:8100/api/docs
- Flower: http://localhost:5555

### 3. 数据库初始化（首次）

```bash
docker exec -it creative_api python -c "
from app.db import engine
from app.models import Base
Base.metadata.create_all(engine)
print('Tables created.')
"
```

---

## API 路由一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册用户 |
| POST | /api/auth/login | 登录，返回 JWT |
| GET  | /api/auth/me | 当前用户信息 + 积分余额 |
| GET  | /api/templates | 列出模板（支持 ?doc_type=ppt&style=tech） |
| GET  | /api/templates/{id} | 获取模板详情 |
| POST | /api/jobs | 提交生成任务（异步，返回 202） |
| GET  | /api/jobs | 历史任务列表 |
| GET  | /api/jobs/{id} | 查询任务状态 + 下载 URL |
| DELETE | /api/jobs/{id} | 取消排队中的任务 |
| POST | /api/webhooks/stripe | Stripe 支付回调 |
| POST | /api/webhooks/wechat | 微信支付回调 |

---

## 生成流水线（一次任务）

```
用户请求 (brief + doc_type + template_id)
        │
        ▼
  Celery Task (worker/tasks.py)
        │
        ├─① LLM Router (worker/llm_router.py)
        │   DeepSeek-chat ─(失败)→ GPT-4o-mini ─(失败)→ Claude Haiku
        │   输出: ContentDoc JSON
        │
        ├─② Image Router (worker/image_router.py)
        │   每个 block.visual.tier 决定引擎:
        │   stock(免费占位) / standard(gpt-image-1) / premium(gpt-image-2)
        │   输出: ContentDoc with visual.resolved.url
        │
        ├─③ Renderer
        │   ppt  → python-pptx → .pptx
        │   xhs/wechat/whitepaper → html_renderer → .html
        │
        ├─④ Upload (S3/R2/OSS 或本地 outputs/)
        │
        └─⑤ 更新 DB (Job.status=done, result_url, credit_actual)
```

---

## 积分计费（估算）

| 操作 | 积分消耗 |
|------|---------|
| PPT 生成（LLM）| 120 |
| 小红书生成（LLM）| 60 |
| 公众号图文（LLM）| 80 |
| 白皮书（LLM）| 200 |
| 每张图（standard）| +10 |
| 每张图（premium）| +20 |

---

## 模板库（20 套）

| 类型 | 套数 | 风格 |
|------|------|------|
| PPT | 8 | 科技蓝、极简白、暖色品牌、深色高端、医疗、环保、教育、金融 |
| 小红书 | 5 | 生活方式、美食、数码测评、旅行、干货知识 |
| 微信公众号 | 4 | 企业公告、品牌故事、行业洞察、活动促销 |
| 白皮书 | 3 | B2B 正式、创业路演、研究报告 |

---

## 交付状态

| 组件 | 状态 |
|------|------|
| ① 技术方案书 | ✅ |
| ② JSON 内容协议 + schema + Pydantic | ✅ |
| ③ python-pptx 渲染器 | ✅ |
| ④ HTML 渲染器（XHS/WeChat/白皮书）| ✅ |
| ⑤ LLM 路由器（三级容错）| ✅ |
| ⑥ 图像路由器（stock/standard/premium）| ✅ |
| ⑦ Celery 任务队列 + 积分计费 | ✅ |
| ⑧ FastAPI 后端骨架（auth/jobs/templates/webhooks）| ✅ |
| ⑨ 20 套模板 JSON | ✅ |
| ⑩ Docker Compose 编排（隔离）| ✅ |
| ⑪ UI 原型（三栏）| ✅ |

---

## 下一步

- Alembic 数据库迁移脚本
- Stripe / 微信支付真实集成测试
- 前端 Next.js 接入（替换静态 UI 原型）
- CDN + 自定义域名 (studio.insynbio.com)
- GPT-Image-2 限流 + 本地缓存（相同 prompt hash 复用）
