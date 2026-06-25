# AbEngineCore SaaS Deployment Guide

## Quick Start（5 ）

### 

- VPS （Hetzner /  / Vultr...）— Ubuntu 20.04+  Debian 11+
- ，** VPS IP**（DNS A ）
- SSH （root  sudo）
- GitHub Token（ GHCR；）

### 

```bash
# SSH  VPS
ssh root@<VPS_IP>

# 
cd /tmp
wget https://raw.githubusercontent.com/jhuang7908/InSynBio-AI-Research/main/Antibody_Engineer_Suite/deploy-saas.sh
chmod +x deploy-saas.sh

# 
ADMIN_PIN= bash deploy-saas.sh your-domain.com jhuang7908

#  GitHub Token
ADMIN_PIN= GITHUB_TOKEN=ghp_xxx bash deploy-saas.sh your-domain.com jhuang7908
```

， **https://your-domain.com** 。

---

## 

### 

```bash
cd /opt/abenginecore
bash ops.sh status
```

### 

```bash
bash ops.sh logs 100
```

### 

```bash
bash ops.sh pull
```

### 

```bash
#  30 
bash ops.sh clean-jobs 30

#  7 
bash ops.sh clean-jobs 7
```

### 

```bash
bash ops.sh backup /backups
# ：abenginecore_backup_20260421_143000.tar.gz
```

### 

```bash
bash ops.sh stats
```

---

## 

### 1. ？

```
1. apt update && apt upgrade                    — 
2.  Docker + Docker Compose                 — 
3. docker login ghcr.io                         — 
4. mkdir -p /opt/abenginecore/{jobs,auth,caddy} — 
5.  docker-compose.yml + Caddyfile          — 
6. docker-compose up -d                         — 
   ├─ Caddy（:80,:443 → TLS + ）
   └─ AbEngineCore（:8000 ）
7.  SQLite auth DB， admin       — 
```

### 2. 

|  |  |
|------|------|
| `https://your-domain.com` | **** |
| `https://your-domain.com/docs` | FastAPI  |
| `https://your-domain.com/health` |  |

### 3. 

```
/opt/abenginecore/
├── docker-compose.yml          # 
├── Caddyfile                   # 
├── jobs/                       # （ GB ）
├── auth/                       # SQLite auth DB
├── caddy_data/                 # Caddy  + 
└── caddy_config/               # Caddy 
```

### 4. 

 VPS shell ，：

```bash
# 
export ADMIN_PIN=""

#  owner
export GHCR_OWNER="other-org"

# GitHub  Token
export GITHUB_TOKEN="ghp_xxx"

# （ /opt/abenginecore）
export DATA_ROOT="/mnt/data/abenginecore"

bash deploy-saas.sh your-domain.com
```

---

## 

### 1. 

****： `https://your-domain.com` 

****：
```bash
# DNS 
nslookup your-domain.com

# 
docker-compose ps

# Caddy 
docker-compose logs caddy | tail -50

#  80/443
sudo ufw status
sudo ufw allow 80/443/tcp
```

### 2. 

****：`docker pull ghcr.io/... : unauthorized`

****：Token 

****：
```bash
# 
echo "$GITHUB_TOKEN" | docker login ghcr.io -u USERNAME --password-stdin

# 
docker pull ghcr.io/library/python:3.11
```

### 3.  5 

****： hang

****：
- VPS （1C2G ）
-  bug

****：
```bash
#  VPS 
# ，
```

---

## 

|  | （/） |
|----|-----------|
| VPS 1C2G | €3–5/ |
|  | $10–12/ |
| SSL  | $0（Let's Encrypt） |
| （100GB/） |  |
| **** | **€3–5/** |

> /， VPS（2C4G €10/）（>$100/）

---

## 

- ****： Prometheus + Grafana
- ****： `bash ops.sh backup /backups`  OSS
- ****： Kubernetes 
- **CDN**：， CDN 
- ****： AbEngineCore  + （Redis）

---

## 

：
- `docs/operations/PRIVATE_SAAS_DOCKER.md` — 
- `docker-compose.yml` — 
- VPS 
