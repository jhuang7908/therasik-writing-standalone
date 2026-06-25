"""
admin_cli.py
============
Command-line tool for managing TheraSIK license key pairs.

Usage:
  python admin_cli.py create --email user@lab.edu --name "Dr. Wang" --days 365 --quota 500
  python admin_cli.py list
  python admin_cli.py revoke --mcp-key THERASIK-MCP-XXXXX
  python admin_cli.py topup --agent-key THERASIK-AGT-XXXXX --units 200
  python admin_cli.py status --mcp-key THERASIK-MCP-XXXXX

Set environment variables:
  THERASIK_API_URL    https://your-app.railway.app
  THERASIK_ADMIN_SECRET  your-admin-secret
"""

from __future__ import annotations
import argparse
import json
import os
import urllib.request
import urllib.error

API_URL = os.environ.get("THERASIK_API_URL", "http://localhost:8000")
ADMIN_SECRET = os.environ.get("THERASIK_ADMIN_SECRET", "change-this-secret")


def _call(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Content-Type": "application/json",
            "X-Admin-Secret": ADMIN_SECRET,
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def cmd_create(args):
    result = _call("POST", "/admin/create-pair", {
        "customer_email": args.email,
        "customer_name": args.name,
        "plan": args.plan,
        "mcp_days": args.days,
        "agent_quota": args.quota,
        "notes": args.notes,
    })
    print("\n=== NEW LICENSE KEY PAIR ===")
    print(f"Customer:    {result.get('customer_email')}")
    print(f"MCP Key:     {result.get('mcp_key')}")
    print(f"Agent Key:   {result.get('agent_key')}")
    print(f"Expires:     {result.get('mcp_expires_at')}")
    print(f"Quota:       {result.get('agent_quota')} operations")
    print(f"\n--- Send to customer ---")
    print(result.get("instructions", ""))


def cmd_list(args):
    result = _call("GET", f"/admin/pairs?status={args.status}")
    pairs = result.get("pairs", [])
    print(f"\n{'Email':<30} {'MCP Key':<30} {'Expires':<12} {'Used/Total':<12} {'Status'}")
    print("-" * 100)
    for p in pairs:
        used = p.get('agent_used', 0)
        total = p.get('agent_quota', 0)
        print(f"{p.get('customer_email',''):<30} "
              f"{p.get('mcp_key',''):<30} "
              f"{p.get('mcp_expires_at','')[:10]:<12} "
              f"{used}/{total:<10} "
              f"{p.get('status','')}")
    print(f"\nTotal: {result.get('count', 0)}")


def cmd_revoke(args):
    body = {}
    if args.mcp_key:
        body["mcp_key"] = args.mcp_key
    elif args.agent_key:
        body["agent_key"] = args.agent_key
    result = _call("POST", "/admin/revoke", body)
    print(f"Result: {result}")


def cmd_topup(args):
    result = _call("POST", "/admin/topup", {
        "agent_key": args.agent_key,
        "units": args.units,
    })
    print(f"Topped up {args.units} units")
    print(f"New quota: {result.get('new_quota')} total, "
          f"{result.get('quota_remaining')} remaining")


def main():
    parser = argparse.ArgumentParser(description="TheraSIK License Admin CLI")
    sub = parser.add_subparsers(dest="cmd")

    # create
    p = sub.add_parser("create", help="Create a new key pair")
    p.add_argument("--email", required=True)
    p.add_argument("--name", default="")
    p.add_argument("--plan", default="standard")
    p.add_argument("--days", type=int, default=365, help="MCP Key validity in days")
    p.add_argument("--quota", type=int, default=500, help="Agent Key operation quota")
    p.add_argument("--notes", default="")

    # list
    p = sub.add_parser("list", help="List key pairs")
    p.add_argument("--status", default="active")

    # revoke
    p = sub.add_parser("revoke", help="Revoke a key pair")
    p.add_argument("--mcp-key", default=None)
    p.add_argument("--agent-key", default=None)

    # topup
    p = sub.add_parser("topup", help="Add quota to Agent Key")
    p.add_argument("--agent-key", required=True)
    p.add_argument("--units", type=int, required=True)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    {"create": cmd_create, "list": cmd_list,
     "revoke": cmd_revoke, "topup": cmd_topup}[args.cmd](args)


if __name__ == "__main__":
    main()
