# Writing-Memory · Self-VPS Deployment Guide

This guide stands up `write.insynbio.com` on a small Linux VPS
(2 vCPU / 4 GB RAM is enough for MVP traffic — the Claude / OpenAI heavy
lifting happens on Anthropic/OpenAI servers).

The deployment uses **one server-side Claude key shared by all anonymous
third-party visitors**, with per-IP daily quota:

| class  | endpoints                                                                                 | default |
|--------|-------------------------------------------------------------------------------------------|---------|
| plan   | `/plan_paper`, `/recommend_journal`                                                       | 2 / day |
| draft  | `/draft_section`, `/draft_figure_legend`, `/describe_figure`, `/parse_table`              | 6 / day |
| polish | `/rewrite`, `/claim_check`, `/reduce_ai_tone`, `/reviewer_sim`, `/find_references`, `/verify_pmid`, `/insert_citations`, `/similar` | 10 / day |

Override with `WM_QUOTA_PLAN` / `WM_QUOTA_DRAFT` / `WM_QUOTA_POLISH`
environment variables.

---

## A. Docker (recommended)

```bash
# 1. Provision a Linux box with Docker + Docker Compose installed.
git clone https://github.com/<owner>/<repo>.git
cd <repo>/services/writing_memory

# 2. Drop the secrets file (NEVER commit this).
cp .env.example .env
# Edit .env — fill in:
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...
#   NCBI_API_KEY=... (optional, raises PubMed rate from 3 to 10 req/s)
#   CROSSREF_EMAIL=ops@insynbio.com

# 3. Build the image and start.
docker compose up -d --build

# 4. Verify locally on the box.
curl -s http://127.0.0.1:8100/health
curl -s http://127.0.0.1:8100/quota
```

The container exposes **127.0.0.1:8100 only**.  TLS, rate limiting, and
public DNS are handled by nginx (next section).

To upgrade later:

```bash
cd <repo>/services/writing_memory
git pull
docker compose up -d --build      # rebuild only on code change
docker compose logs -f             # tail
```

---

## B. nginx + Let's Encrypt

```bash
# 1. Install nginx and certbot.
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx

# 2. Drop the proxy config.
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/writing-memory.conf
sudo ln -s /etc/nginx/sites-available/writing-memory.conf /etc/nginx/sites-enabled/

# 3. Issue the TLS cert. DNS for write.insynbio.com must already point here.
sudo certbot --nginx -d write.insynbio.com --redirect --agree-tos -m ops@insynbio.com

# 4. Reload.
sudo nginx -t && sudo systemctl reload nginx
```

The example nginx config also enforces:

- HTTPS-only (HTTP → HTTPS redirect)
- Per-IP rate limit: writes 10/min, reads 60/min
- Upload size cap: 8 MB (covers 5 MB images + headers)
- Security headers: `X-Frame-Options DENY`, `X-Robots-Tag noindex`,
  `X-Content-Type-Options nosniff`, `Referrer-Policy strict-origin-when-cross-origin`
- `X-Forwarded-For` is set so the quota middleware sees real client IPs

---

## C. Non-Docker (systemd) — for bare-metal installs

```bash
# Create unprivileged service user
sudo useradd --system --create-home --shell /bin/bash insynbio

# Copy code under /srv (or wherever)
sudo mkdir -p /srv/writing-memory
sudo rsync -a services/writing_memory/ /srv/writing-memory/
sudo chown -R insynbio:insynbio /srv/writing-memory

# Create venv and install deps
sudo -u insynbio python3.11 -m venv /srv/writing-memory/.venv
sudo -u insynbio /srv/writing-memory/.venv/bin/pip install -r /srv/writing-memory/requirements.txt

# Drop the systemd unit
sudo cp services/writing_memory/deploy/writing-memory.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now writing-memory.service
sudo systemctl status writing-memory.service
```

Logs: `journalctl -u writing-memory -f`

---

## D. Hardening checklist (before opening to third parties)

| Item | Status | Where to set |
|------|--------|--------------|
| HTTPS only (Let's Encrypt) | ☐ | `nginx.conf.example` |
| `X-Robots-Tag: noindex` | ☐ | `nginx.conf.example` |
| Per-IP rate limit at nginx layer | ☐ | `nginx.conf.example` |
| Per-IP daily quota at app layer | ☑ | `quota.py` (built-in) |
| `client_max_body_size 8m` | ☐ | `nginx.conf.example` |
| Anthropic budget alert ($X / month) | ☐ | Anthropic console |
| OpenAI budget alert | ☐ | OpenAI console |
| Bind uvicorn to 127.0.0.1 (not 0.0.0.0) | ☑ | `docker-compose.yml` |
| Run as unprivileged user | ☑ | Dockerfile + systemd unit |
| Persisted `data/quota.db` volume | ☑ | `docker-compose.yml` |
| Container restart=unless-stopped | ☑ | `docker-compose.yml` |
| Fail2ban on nginx 429 / 5xx | ☐ | optional |

---

## E. Operating the quota

```bash
# View today's counters for all IPs (admin-only — protect with a firewall ACL
# or a basic-auth nginx location block before exposing).
sqlite3 data/quota.db "SELECT * FROM usage WHERE date = strftime('%Y-%m-%d','now') ORDER BY n DESC LIMIT 50;"

# Reset one IP today (Python shell)
docker compose exec writing-memory python -c \
  "from quota import reset_ip; print(reset_ip('203.0.113.7'))"

# Raise limits without rebuilding (edit docker-compose.yml env, then):
docker compose up -d
```

If a third party complains about hitting the limit, just `reset_ip` for
them or temporarily bump `WM_QUOTA_*`.

---

## F. Cost ceiling (worst case)

With MEDIUM defaults (2 plan + 6 draft + 10 polish per IP per day):

- plan_paper        ≈ 16k input + 8k output  →  ≈ $0.18
- draft_section     ≈  8k input + 4k output  →  ≈ $0.09
- polish (rewrite)  ≈  2k input + 1k output  →  ≈ $0.02

Per IP per day worst case: `2*$0.18 + 6*$0.09 + 10*$0.02 ≈ $1.10`

For 100 daily unique visitors: ≈ **$110 / day** Claude spend.  Cap with
Anthropic budget alerts and revisit limits weekly.

---

## G. Smoke test the live deployment

```bash
HOST=https://write.insynbio.com

curl -s $HOST/health | jq .
curl -s $HOST/quota  | jq .

# Should return 429 after the 11th polish call.
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST $HOST/rewrite \
    -H 'Content-Type: application/json' \
    -d '{"paragraph":"Our results suggest the method works.","target_journal":"elife","section":"discussion"}'
done
```
