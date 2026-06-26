"""
Scheduled literature radar — watch topics, periodic OpenAlex scans, reports + email.

Used by:
  - POST /intelligence/radar/* API routes in app.py
  - scripts/run_intelligence_radar_cron.py (systemd timer / cron on VPS)
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Callable

from . import intelligence_store, openalex_client

_INTEL_RADAR_SYSTEM = (
    "You are a biomedical literature-radar analyst. The user runs a recurring "
    "watch on a research topic. You receive ONLY **new** papers since the last "
    "run (title, year, DOI, optional abstract snippet). Produce concise Markdown:\n"
    "(1) Executive summary (2-4 sentences),\n"
    "(2) 3-6 bullet themes/hotspots,\n"
    "(3) **New publications** — numbered list with title, year, DOI, and one "
    "sentence why it matters,\n"
    "(4) Gaps or follow-ups. Use ONLY listed papers. Never invent DOIs or findings. "
    "Tag inferred trends [inferred]. Under ~500 words."
)

_CADENCE_DAYS = {"weekly": 7, "monthly": 30}


def cadence_days(cadence: str) -> int:
    return _CADENCE_DAYS.get((cadence or "").strip().lower(), 7)


def work_openalex_id(work: dict[str, Any]) -> str:
    oid = work.get("openalex_id") or work.get("id") or ""
    s = str(oid).strip()
    if "openalex.org/" in s:
        s = s.rstrip("/").split("/")[-1]
    if not s and work.get("doi"):
        s = f"doi:{work['doi']}"
    if not s and work.get("title"):
        s = "title:" + " ".join(str(work["title"]).lower().split())[:120]
    return s


def smtp_configured() -> bool:
    return bool((os.environ.get("LAB_SMTP_HOST") or "").strip())


def send_radar_email(*, to: str, subject: str, body_text: str, body_html: str | None = None) -> dict[str, Any]:
    """Send notification using LAB_SMTP_* (same as Lab module)."""
    host = (os.environ.get("LAB_SMTP_HOST") or "").strip()
    if not host:
        return {"sent": False, "reason": "LAB_SMTP_HOST not configured"}
    port = int((os.environ.get("LAB_SMTP_PORT") or "587").strip() or "587")
    user = (os.environ.get("LAB_SMTP_USER") or "").strip()
    password = (os.environ.get("LAB_SMTP_PASSWORD") or "").strip()
    use_tls = (os.environ.get("LAB_SMTP_TLS") or "1").strip().lower() not in ("0", "false", "no")
    from_addr = (os.environ.get("LAB_SMTP_FROM") or user or "").strip()
    if not from_addr:
        return {"sent": False, "reason": "LAB_SMTP_FROM not configured"}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, [to], msg.as_string())
        return {"sent": True, "to": to, "via": "smtp"}
    except Exception as exc:
        return {"sent": False, "reason": str(exc)}


def _format_works_block(works: list[dict[str, Any]], *, heading: str) -> str:
    if not works:
        return ""
    lines = [f"## {heading}\n"]
    for i, w in enumerate(works, 1):
        title = w.get("title") or "Untitled"
        yr = w.get("year") or "n.d."
        doi = w.get("doi")
        authors = w.get("authors") or ""
        ab = (w.get("abstract") or "")[:280]
        line = f"{i}. **{title}** ({yr})"
        if authors:
            line += f" — {authors}"
        if doi:
            line += f" · DOI:{doi}"
        if w.get("oa_url"):
            line += f" · [OA]({w['oa_url']})"
        lines.append(line)
        if ab:
            lines.append(f"   - {ab}…" if len((w.get("abstract") or "")) > 280 else f"   - {ab}")
    return "\n".join(lines) + "\n\n"


def build_radar_report(
    *,
    watch: dict[str, Any],
    works: list[dict[str, Any]],
    new_works: list[dict[str, Any]],
    from_date: str,
    llm_complete: Callable[..., tuple[str, Any]],
    digest_system: str,
) -> str:
    label = (watch.get("label") or watch.get("query") or "Topic").strip()
    cadence = watch.get("cadence") or "weekly"
    days = cadence_days(cadence)

    header = (
        f"# Literature Radar — {label}\n\n"
        f"*Project:* `{watch.get('project_id')}` · *Cadence:* {cadence} "
        f"({days}d window) · *Window since:* {from_date}\n"
        f"*OpenAlex hits:* {len(works)} · **New since last run:** {len(new_works)}\n\n"
    )

    if not new_works:
        return (
            header
            + "_No new publications identified in this period (all hits were seen in a prior run)._"
        )

    items = "\n".join(
        f"- {w.get('title') or 'Untitled'} ({w.get('year') or 'n.d.'})"
        + (f" DOI:{w['doi']}" if w.get("doi") else "")
        + (f"\n  Abstract: {(w.get('abstract') or '')[:400]}" if w.get("abstract") else "")
        for w in new_works
    )
    user = (
        f"Watch topic: {watch.get('query')}\nCadence: {cadence}\n"
        f"Window: since {from_date}\n\nNew papers ({len(new_works)}):\n{items}"
    )
    try:
        digest, _ = llm_complete(
            system=digest_system,
            user_content=user,
            max_tokens=1600,
            temperature=0.3,
        )
    except Exception:
        digest = None

    body = header
    if digest:
        body += digest.strip() + "\n\n"
    body += _format_works_block(new_works, heading="New publications (full list)")
    return body


def run_watch(
    watch_id: int,
    *,
    project_id: str | None = None,
    force: bool = False,
    llm_complete: Callable[..., tuple[str, Any]],
    digest_system: str = _INTEL_RADAR_SYSTEM,
    send_email: bool = True,
    skip_empty_email: bool = True,
) -> dict[str, Any]:
    """Execute one radar watch: fetch, dedupe, report, optional email + library save."""
    watch = intelligence_store.get_radar_watch(watch_id, project_id=project_id)
    if not watch:
        return {"ok": False, "error": "watch not found"}
    if not watch.get("enabled") and not force:
        return {"ok": False, "error": "watch disabled", "watch_id": watch_id}

    pid = watch["project_id"]
    cadence = watch.get("cadence") or "weekly"
    days = cadence_days(cadence)
    from_date = (date.today() - timedelta(days=days)).isoformat()
    per_page = int(watch.get("per_page") or 15)
    per_page = max(5, min(per_page, 25))

    found = openalex_client.search_works(
        watch["query"],
        per_page=per_page,
        from_publication_date=from_date,
        sort="publication_date:desc",
    )
    works = found.get("works") or []

    seen: set[str] = set(watch.get("last_seen_ids") or [])
    new_works: list[dict[str, Any]] = []
    for w in works:
        wid = work_openalex_id(w)
        if wid and wid not in seen:
            new_works.append(w)

    report_md = build_radar_report(
        watch=watch,
        works=works,
        new_works=new_works,
        from_date=from_date,
        llm_complete=llm_complete,
        digest_system=digest_system,
    )

    saved_lib = 0
    if watch.get("auto_save_library") and new_works:
        sub_db = (watch.get("label") or "").strip()[:120] or None
        for w in new_works:
            try:
                item = dict(w)
                if sub_db:
                    item["subproject"] = sub_db
                intelligence_store.save_document(pid, "openalex", item)
                saved_lib += 1
            except Exception:
                pass

    meta = {
        "radar": True,
        "watch_id": watch_id,
        "cadence": cadence,
        "from_date": from_date,
        "total_hits": len(works),
        "new_count": len(new_works),
        "label": watch.get("label"),
    }
    saved = intelligence_store.save_report(
        pid, "radar", watch.get("query"), report_md, meta=meta,
    )

    all_ids = list(seen)
    for w in works:
        wid = work_openalex_id(w)
        if wid and wid not in all_ids:
            all_ids.append(wid)
    intelligence_store.mark_radar_watch_run(watch_id, pid, all_ids)

    email_result: dict[str, Any] = {"sent": False, "skipped": True}
    notify = (watch.get("notify_email") or "").strip()
    if send_email and notify:
        if skip_empty_email and not new_works:
            email_result = {"sent": False, "skipped": True, "reason": "no new papers"}
        else:
            label = watch.get("label") or watch.get("query")
            subj = f"[InSynBio Radar] {pid} · {label} · {len(new_works)} new"
            ide = (os.environ.get("INTELLIGENCE_PUBLIC_URL") or "https://write.insynbio.com/intelligence").rstrip("/")
            link = f"{ide}?project={pid}"
            plain = report_md[:8000] + f"\n\n---\nOpen in Intelligence IDE: {link}\n"
            html = (
                f"<pre style='font-family:system-ui;font-size:13px'>{_html_escape(report_md[:6000])}</pre>"
                f"<p><a href='{_html_escape(link)}'>Open Intelligence IDE</a></p>"
            )
            email_result = send_radar_email(
                to=notify, subject=subj, body_text=plain, body_html=html,
            )

    return {
        "ok": True,
        "watch_id": watch_id,
        "project_id": pid,
        "report_id": saved.get("id"),
        "new_count": len(new_works),
        "total_hits": len(works),
        "saved_to_library": saved_lib,
        "email": email_result,
        "report_md": report_md,
    }


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def run_due_watches(
    *,
    project_id: str | None = None,
    llm_complete: Callable[..., tuple[str, Any]],
    digest_system: str = _INTEL_RADAR_SYSTEM,
) -> dict[str, Any]:
    due = intelligence_store.list_due_radar_watches(project_id=project_id)
    results: list[dict[str, Any]] = []
    for w in due:
        try:
            results.append(
                run_watch(
                    int(w["id"]),
                    project_id=w.get("project_id"),
                    force=False,
                    llm_complete=llm_complete,
                    digest_system=digest_system,
                )
            )
        except Exception as exc:
            results.append({"ok": False, "watch_id": w.get("id"), "error": str(exc)})
    return {
        "ok": True,
        "due_count": len(due),
        "ran": len(results),
        "results": results,
    }
