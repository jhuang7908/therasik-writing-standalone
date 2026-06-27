#!/usr/bin/env python3
"""Generate admin API key — matches actual DB schema."""
import secrets
import hashlib
import subprocess
from datetime import datetime, timezone, timedelta

salt = "dev_salt"
try:
    for line in open("/etc/therasik-mcp/env").read().splitlines():
        if line.startswith("SECRET_SALT="):
            salt = line.split("=", 1)[1].strip()
            break
except Exception:
    pass

raw = "THMCP-w0wcSR-stCJ1Jkwj1WKizGuChZW46V0nRKmReUTr5Zg"
hashed = hashlib.sha256((salt + raw).encode()).hexdigest()
prefix = raw[:8]  # "THMCP-w0"

sql = (
    f"INSERT INTO api_keys "
    f"(user_id, key_hash, key_prefix, tier, monthly_quota, valid_until, active, created_at) "
    f"SELECT id, '{hashed}', '{prefix}', 'enterprise', -1, "
    f"'2027-06-26 00:00:00+00', true, NOW() "
    f"FROM users WHERE email='admin@insynbio.com' "
    f"RETURNING id, tier, monthly_quota, valid_until;"
)

r = subprocess.run(
    ["sudo", "-u", "postgres", "psql", "-d", "therasik_mcp", "-c", sql],
    capture_output=True, text=True
)

print("=" * 64)
print("TheraSIK MCP — API Key Ready")
print("=" * 64)
print(f"KEY    : {raw}")
print(f"PREFIX : {prefix}")
print(f"TIER   : enterprise  |  QUOTA: unlimited  |  EXPIRES: 2027-06-26")
print("=" * 64)
print(r.stdout.strip() or r.stderr.strip())
