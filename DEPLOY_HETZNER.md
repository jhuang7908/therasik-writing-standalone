# TheraSIK MCP — Hetzner Deployment Guide

**Port assignment (permanent):**

| Port | Service | Unit |
|------|---------|------|
| 8000 | InSynBio AbEngineCore (main API) | `abenginecore-api.service` — **DO NOT TOUCH** |
| 8001 | TheraSIK MCP Writing Suite | `therasik-mcp.service` ← this guide |

---

## 1. Clone / Update Code

```bash
# First time
git clone https://github.com/jhuang7908/therasik-writing-standalone.git /opt/therasik-mcp

# Upgrade
cd /opt/therasik-mcp && git pull
```

## 2. Run deploy.sh

```bash
cd /opt/therasik-mcp
bash deploy/deploy.sh            # first install
bash deploy/deploy.sh --upgrade  # after git pull
```

The script:
- Installs Python venv at `/opt/therasik-mcp/venv`
- Creates Postgres DB `therasik_mcp` + schema
- Creates `/etc/therasik-mcp/env` from `.env.example` (first install only)
- Installs and enables `therasik-mcp.service` on port **8001**
- Configures Nginx reverse proxy for `mcp.therasik.com`
- Runs a health check smoke test

## 3. Fill in Secrets

```bash
nano /etc/therasik-mcp/env
```

Required keys (see `.env.example` for all):

```
DATABASE_URL=postgresql+asyncpg://therasik:YOURPASS@localhost/therasik_mcp
REDIS_URL=redis://localhost:6379/1
THERASIK_MASTER_KEY=<32-char random>
GEMINI_API_KEY=<from GCP console>
```

Then:
```bash
systemctl restart therasik-mcp
```

## 4. Issue TLS Certificate

```bash
certbot --nginx -d mcp.therasik.com
```

## 5. Create First API Key

```bash
cd /opt/therasik-mcp
source venv/bin/activate
python scripts/admin_cli.py keygen --email admin@insynbio.com --plan pro --quota 100000
```

## 6. Verify End-to-End

```bash
# Health
curl https://mcp.therasik.com/health

# Authenticated MCP call
API_KEY=<from step 5>
curl -H "X-API-Key: $API_KEY" \
     "https://mcp.therasik.com/v1/usage/me"
```

## 7. Monitoring

```bash
# Live logs
journalctl -u therasik-mcp -f

# Port check (must see 8000 AND 8001, never conflict)
ss -tlnp | grep -E '8000|8001'

# Status
systemctl status therasik-mcp
systemctl status abenginecore   # unchanged
```

## 8. Rollback

```bash
cd /opt/therasik-mcp
git log --oneline -5
git checkout <previous-hash>
systemctl restart therasik-mcp
```

---

## Repository Layout

```
github.com/jhuang7908/therasik-writing-standalone   ← public MCP client + skills
github.com/jhuang7908/Antibody-Engineer-Suite-MVP   ← InSynBio core (DO NOT mix)
```

Server path: `/opt/therasik-mcp`  
Env secrets: `/etc/therasik-mcp/env` (root-owned, 0600)
