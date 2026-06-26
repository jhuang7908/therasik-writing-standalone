#!/usr/bin/env python3
"""Copy DEEPSEEK_API_KEY from insynbio-api into writing_memory .env (run on VPS as root)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

WM_ENV = Path("/srv/services/writing_memory/.env")
OVERRIDES = [
    Path("/etc/systemd/system/insynbio-api.service.d/deepseek.conf"),
    Path("/etc/systemd/system/abenginecore-api.service.d/deepseek.conf"),
]
SERVICE_NAMES = ("insynbio-api", "abenginecore-api")


def _key_from_override(path: Path) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'DEEPSEEK_API_KEY=(sk-[^\s"\'"]+)', text)
    return m.group(1) if m else ""


def _key_from_process(service: str) -> str:
    try:
        out = subprocess.check_output(
            ["systemctl", "show", "-p", "MainPID", "--value", f"{service}.service"],
            text=True,
        ).strip()
        pid = int(out or "0")
        if pid <= 0:
            return ""
        env_raw = Path(f"/proc/{pid}/environ").read_bytes()
        for item in env_raw.split(b"\0"):
            if item.startswith(b"DEEPSEEK_API_KEY="):
                return item.decode("utf-8", errors="replace").split("=", 1)[1]
    except (subprocess.CalledProcessError, OSError, ValueError):
        pass
    return ""


def main() -> int:
    key = ""
    for p in OVERRIDES:
        key = _key_from_override(p)
        if key:
            break
    if not key:
        for svc in SERVICE_NAMES:
            key = _key_from_process(svc)
            if key:
                break
    if not key:
        print("ERROR: DEEPSEEK_API_KEY not found", file=sys.stderr)
        return 1

    lines: list[str] = []
    if WM_ENV.is_file():
        skip = {
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_BASE_URL",
            "DEEPSEEK_MODEL",
            "WM_LLM_FALLBACK",
            "WM_LLM_PROVIDER",
        }
        for line in WM_ENV.read_text(encoding="utf-8").splitlines():
            if not any(line.startswith(f"{v}=") for v in skip):
                lines.append(line)
    lines.extend([
        f"DEEPSEEK_API_KEY={key}",
        "DEEPSEEK_BASE_URL=https://api.deepseek.com/v1",
        "DEEPSEEK_MODEL=deepseek-chat",
        "WM_LLM_FALLBACK=deepseek",
        "WM_LLM_PROVIDER=anthropic",
    ])
    WM_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(WM_ENV, 0o600)
    print(f"OK: DeepSeek wired (key length {len(key)})")

    subprocess.run(["systemctl", "restart", "writing-memory.service"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
