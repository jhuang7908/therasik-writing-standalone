# Trial login (username + numeric PIN)

SQLite DB: `api/.data/insynbio_auth.db` (gitignored).

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` | New user; receives trial credits |
| POST | `/auth/login` | Returns `access_token` (Bearer) |
| GET | `/auth/me` | Credits + role |
| POST | `/auth/debit` | Deduct credits (Console calls after a successful run) |
| GET | `/auth/ledger` | Recent debit rows |

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `INSYNBIO_TRIAL_CREDITS` | `500` | Credits for **self-service Register** (trial role) |
| `INSYNBIO_OWNER_CREDITS` | `1000000` | Display balance for bootstrapped owner (not reduced if unlimited) |
| `INSYNBIO_OWNER_UNLIMITED` | `1` | If `1`/`true`, **owner** accounts from bootstrap get **unlimited** credits (usage still logged; `debited` = 0) |
| `INSYNBIO_AUTH_SECRET` | *(dev placeholder)* | HMAC key for session tokens — **set in production** |
| `INSYNBIO_ALLOW_REGISTER` | `1` | Set `0` to disable `/auth/register` |
| `INSYNBIO_BOOTSTRAP_OWNER` | — | `username:pin` creates an **owner** once if username missing |

### Why do I still see 500 credits?

You logged in as a **trial** user created via **Register** — that role uses `INSYNBIO_TRIAL_CREDITS` (default 500).  
Use an **owner** account (bootstrap env) or set `credits_unlimited` / top up credits in the DB (see below).

### Unlimited (owner)

- New **bootstrap** owners get `credits_unlimited=1` when `INSYNBIO_OWNER_UNLIMITED` is on (default).
- Existing DB row:  
  `UPDATE users SET credits_unlimited = 1 WHERE username = 'YourOwnerName';`

There is no mathematical “infinity” in the DB; unlimited means **no deduction**, balance field unchanged, ledger records `credits=0` with `waived` in `extra_json`.

Example (PowerShell):

```text
$env:INSYNBIO_BOOTSTRAP_OWNER="owner:123456"
$env:INSYNBIO_AUTH_SECRET="your-long-random-secret"
conda run -n anarcii uvicorn api.main:app --reload --port 8000
```

## Next steps (SMS)

Replace or wrap `POST /auth/login` with OTP: issue short-lived token after SMS verify; keep PIN as backup or remove.
