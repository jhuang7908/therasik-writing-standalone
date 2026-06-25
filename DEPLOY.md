# TheraSIK 部署指南

## 架构概览

```
GitHub私有仓库（客户clone）          云端服务器 Railway（你维护）
─────────────────────────          ──────────────────────────────
scripts/mcp_server.py        →     https://api.therasik.io/validate
scripts/literature_db.py           https://api.therasik.io/consume
scripts/build_journal_db.py        https://api.therasik.io/journal/{name}
assets/project-template/           assets/journal_requirements/ (5600+本)
references/                        licenses.db（Key管理数据库）
```

---

## 第一步：推送代码到GitHub私有仓库

在PowerShell里运行（或交给Cursor执行）：

```powershell
cd "D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\writing_system_productization\therasik-academic-writing-suite"

git init
git add .
git commit -m "feat: initial TheraSIK writing suite"

# 在GitHub创建私有仓库后：
git remote add origin https://github.com/你的账号/therasik-suite.git
git push -u origin main
```

**注意**：设为Private仓库，只有付费客户收到邀请后才能clone。

---

## 第二步：部署云端服务器到Railway

```bash
# 安装Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 在项目根目录
railway init
railway up

# 设置环境变量
railway variables set ADMIN_SECRET="your-strong-secret-here"
railway variables set JOURNAL_DIR="./assets/journal_requirements"
```

部署完成后Railway会给你一个URL，例如：
`https://therasik-production.railway.app`

把这个URL更新到 `mcp-roadmap.md` 和客户文档里。

---

## 第三步：生成客户Key对（用admin_cli.py）

```powershell
# 设置环境变量
$env:THERASIK_API_URL = "https://therasik-production.railway.app"
$env:THERASIK_ADMIN_SECRET = "your-strong-secret-here"

# 创建一个客户的Key对
python admin_cli.py create `
  --email "pi@university.edu" `
  --name "Prof. Zhang" `
  --days 365 `
  --quota 500

# 查看所有客户
python admin_cli.py list

# 撤销某个Key
python admin_cli.py revoke --mcp-key THERASIK-MCP-XXXXX

# 给Agent Key充值配额
python admin_cli.py topup --agent-key THERASIK-AGT-XXXXX --units 200
```

---

## 第四步：发给客户的安装说明

客户收到邀请后，运行：

```powershell
# 1. Clone仓库
git clone https://github.com/你的账号/therasik-suite.git
cd therasik-suite

# 2. 安装依赖
pip install -r requirements-mcp.txt

# 3. 设置License Key（你邮件发给他们的）
# 在项目根目录创建 .env 文件：
# THERASIK_MCP_KEY=THERASIK-MCP-XXXXX
# THERASIK_AGENT_KEY=THERASIK-AGT-XXXXX
# THERASIK_LICENSE_API=https://therasik-production.railway.app

# 4. 验证安装
python scripts/validate_basic_skill.py .

# 5. 配置到平台（见 references/mcp-roadmap.md）
```

---

## 环境变量说明

| 变量 | 说明 | 设置位置 |
|------|------|----------|
| `THERASIK_MCP_KEY` | 客户的MCP时效Key | 客户本地 .env |
| `THERASIK_AGENT_KEY` | 客户的Agent用量Key | 客户本地 .env |
| `THERASIK_LICENSE_API` | 你的云端服务器URL | 客户本地 .env |
| `ADMIN_SECRET` | 管理员密钥 | Railway环境变量 |
| `JOURNAL_DIR` | 期刊数据库路径 | Railway环境变量 |

---

## 客户Key对说明

| Key类型 | 控制维度 | 续费方式 |
|---------|----------|----------|
| MCP Key | 时间（365天） | 年费续订，Key延期 |
| Agent Key | 用量（N次操作） | 随时充值，不重置时间 |

两个Key必须配对使用，缺一不可。
你的主控权：随时通过 `admin_cli.py revoke` 撤销任意客户。
