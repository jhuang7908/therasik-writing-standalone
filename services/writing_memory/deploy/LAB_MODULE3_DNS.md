# Module 3 — lab.insynbio.com (eLabFTW)

protocols.io is already live on write (`PROTOCOLSIO_*` in `.env`). eLabFTW adds ELN + reagent inventory at **lab.insynbio.com**.

## 1. DNS

At your DNS provider (same zone as `insynbio.com`):

| Type | Name | Value |
|------|------|--------|
| A | `lab` | `157.180.91.72` |

Wait for propagation (`dig lab.insynbio.com` should return the VPS IP).

## Why lab.insynbio.com showed console

DNS was correct, but **nginx had no `lab.insynbio.com` vhost** — HTTPS fell through to `console.insynbio.com`. Fix: enable `sites-available/lab.insynbio.com` (proxy to `127.0.0.1:4430`) and `certbot --nginx -d lab.insynbio.com`.

## Why https://127.0.0.1:4430 does not open on your PC

`127.0.0.1:4430` listens **only on the VPS**, not on your laptop. Use either:

- **Public:** https://lab.insynbio.com (after nginx + cert above)
- **SSH tunnel from Windows:**
  ```powershell
  ssh -i $env:USERPROFILE\.ssh\id_ed25519 -L 4430:127.0.0.1:4430 root@157.180.91.72
  ```
  Then open https://127.0.0.1:4430/ (accept certificate warning if any).

## eLabFTW API key (not a separate “registration site”)

1. Open **https://lab.insynbio.com** and complete the **first-time setup wizard** (admin account).
2. Log in → top right **avatar / username** → **User settings** (or **Settings**).
3. Open the **API** tab → **Create API key** (or “Generate key”) → copy the token once.
4. On VPS, add to `/srv/services/writing_memory/.env`:
   ```bash
   ELABFTW_BASE_URL=https://lab.insynbio.com
   ELABFTW_PUBLIC_URL=https://lab.insynbio.com
   ELABFTW_API_TOKEN=paste_key_here
   ```
5. `systemctl restart writing-memory` — then **write.insynbio.com** Plan → **From eLabFTW**.

Official docs: https://doc.elabftw.net/api.html

### “Your account is not validated”

A **Team Admin** or **Sysadmin** must validate the account:

- **UI:** Log in as `admin@insynbio.com` → **Admin panel** → validate pending users, **or**
- **Sysadmin:** https://lab.insynbio.com → **Sysadmin** → Users

### “Error decrypting key”

API keys are **bound to the instance URL**. This appears if the key was created when the site URL was wrong (e.g. `localhost`) or the key was truncated.

**Fix:**

1. Log in only at **https://lab.insynbio.com** (not console, not `127.0.0.1` unless via tunnel).
2. **User settings → API** → delete old keys → **Create API key** (copy full string, format `1-…` or `3-…`).
3. VPS `.env` — no quotes, no spaces:
   ```bash
   ELABFTW_BASE_URL=https://lab.insynbio.com
   ELABFTW_API_TOKEN=1-your-full-key-here
   ```
4. `systemctl restart writing-memory`

Test: `curl -H "Authorization: YOUR_KEY" https://lab.insynbio.com/api/v2/items?limit=1`

## 2. Install eLabFTW on VPS

From repo root (Windows):

```powershell
powershell -File services/writing_memory/deploy/install-elabftw-on-vps.ps1
```

On VPS after DNS + nginx:

```bash
certbot --nginx -d lab.insynbio.com
```

Complete the eLabFTW web setup wizard → **Settings → API** → create API key.

## 3. Wire write.insynbio.com

Append to `/srv/services/writing_memory/.env` (see `deploy/elabftw.env.example`):

```bash
ELABFTW_BASE_URL=https://lab.insynbio.com
ELABFTW_PUBLIC_URL=https://lab.insynbio.com
ELABFTW_API_TOKEN=your_elabftw_api_key
```

For customer Labs, keep the internal token as the fallback only. Use a server-only tenant file:

```bash
cp /srv/services/writing_memory/deploy/elabftw_tenants.example.json /srv/services/writing_memory/lab_tenants.json
chmod 600 /srv/services/writing_memory/lab_tenants.json
```

Then add token env vars, one per customer Team/service account:

```bash
ELABFTW_TENANTS_FILE=/srv/services/writing_memory/lab_tenants.json
ELABFTW_TOKEN_CUSTOMER_A=customer_a_service_account_api_key
```

`lab_tenants.json` maps `project_id` / `customer_id` to `base_url`, `public_url`, and `api_token_env`. Do not put customer API tokens in git-tracked JSON or browser code.

```bash
systemctl restart writing-memory
curl -s https://write.insynbio.com/lab/config
```

Expect `"elabftw": { "configured": true, ... }`.

## 4. In the UI

- Portal: `https://write.insynbio.com/?entry=lab`
- Plan panel: protocols.io search + **From eLabFTW** (after configured)

Module 3 portal status will show eLabFTW when `/lab/config` reports configured.
