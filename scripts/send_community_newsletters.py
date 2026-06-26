#!/usr/bin/env python3
"""scripts/send_community_newsletters.py  —  Send personalized, staggered newsletters to subscribers.

Handles:
- Personalization: Filters events by subscriber interests.
- Staggered Sending: Limits daily sends to stay under Brevo's free tier limit (e.g., 250/day).
- Campaign tracking: Prevents duplicate sending in the same campaign cycle.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.send_email as _se

# Paths
DATA_DIR = ROOT / "data" / "community_events"
SUBS_FILE = DATA_DIR / "subscriptions.json"
HUB_INDEX_FILE = ROOT / "insynbio-web-source" / "hub_search_index.json"

# Interest channel mapping (for display labels)
INTEREST_DISPLAY = {
    "benefits_gov": "福利·政务 🏛️",
    "education_lang": "语言·教育 📚",
    "health_medical": "医疗·健康 🏥",
    "transit_travel": "交通·出行 🚇",
    "culture_festival": "文化·节庆 🎉",
    "housing_living": "住房·安居 🏠",
    "deals_savings": "省钱·羊毛 💰",
}

# Keyword mapping to match records from hub_search_index.json
INTEREST_KEYWORDS = {
    "benefits_gov": ["福利", "政务", "政府", "法律", "市民卡", "IDNYC"],
    "education_lang": ["语言", "教育", "学校", "英语", "免费课", "读书"],
    "health_medical": ["医疗", "健康", "医生", "看病", "体检", "诊所", "疫苗"],
    "transit_travel": ["交通", "出行", "地铁", "巴士", "轮渡", "封路", "停车"],
    "culture_festival": ["文化", "节庆", "活动", "亲子", "公园", "游乐场", "派对", "音乐会", "游行"],
    "housing_living": ["住房", "安居", "平价房", "租房", "房东", "房客", "水电", "减免"],
    "deals_savings": ["省钱", "羊毛", "折扣", "促销", "免费领", "派送", "特价"],
}


def load_subscriptions() -> list[dict[str, Any]]:
    if not SUBS_FILE.exists():
        return []
    try:
        with open(SUBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading subscriptions: {e}", file=sys.stderr)
        return []


def save_subscriptions(subs: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(SUBS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
        print("Successfully saved subscriptions database.")
    except Exception as e:
        print(f"Error saving subscriptions: {e}", file=sys.stderr)


def load_events() -> list[dict[str, Any]]:
    if not HUB_INDEX_FILE.exists():
        print(f"Warning: {HUB_INDEX_FILE} not found.", file=sys.stderr)
        return []
    try:
        with open(HUB_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("records", [])
    except Exception as e:
        print(f"Error loading events: {e}", file=sys.stderr)
        return []


def filter_events_for_interests(events: list[dict[str, Any]], interests: list[str]) -> list[dict[str, Any]]:
    """Filter and group events based on subscriber interests."""
    if not interests:
        # If no specific interests, subscribe to all channels
        interests = list(INTEREST_KEYWORDS.keys())

    matched_events = []
    seen_ids = set()

    # We want to match events where the event's module or title contains keywords for the subscribed interests
    for event in events:
        event_id = event.get("id")
        if event_id in seen_ids:
            continue

        module = event.get("module", "")
        title = event.get("title_zh", "")
        summary = event.get("summary_zh", "")

        # Check if this event matches any of the subscriber's interests
        matches_interest = False
        event_interests = []
        for interest in interests:
            keywords = INTEREST_KEYWORDS.get(interest, [])
            # Match if module name or title/summary contains any keyword
            if any(kw in module or kw in title or kw in summary for kw in keywords):
                matches_interest = True
                event_interests.append(interest)

        if matches_interest:
            # Store the matched interests on the event copy for rendering
            event_copy = dict(event)
            event_copy["matched_interests"] = event_interests
            matched_events.append(event_copy)
            seen_ids.add(event_id)

    # Sort matched_events by priority:
    # 1. Freshness (Indexed within last 3 days -> Priority 0, last 7 days -> Priority 1, older -> Priority 2)
    # 2. Event Date Relevance (Upcoming/Evergreen -> Group 0, Past -> Group 1)
    # 3. Freshness timestamp descending (newest first)
    today = datetime.now()
    
    def get_priority_key(ev: dict[str, Any]) -> tuple[int, int, float]:
        # Priority group based on first_indexed_at
        first_indexed_str = ev.get("first_indexed_at") or ""
        first_indexed_dt = None
        if first_indexed_str:
            try:
                first_indexed_dt = datetime.strptime(first_indexed_str[:10], "%Y-%m-%d")
            except Exception:
                pass
                
        if first_indexed_dt:
            delta_days = (today - first_indexed_dt).days
            if delta_days <= 3:
                priority_group = 0  # 近三天
            elif delta_days <= 7:
                priority_group = 1  # 本周
            else:
                priority_group = 2  # 更早
        else:
            priority_group = 2
            
        # Date group based on event_date
        event_date_str = ev.get("event_date") or ""
        date_group = 0  # Upcoming or evergreen
        if event_date_str:
            try:
                event_date_dt = datetime.strptime(event_date_str[:10], "%Y-%m-%d")
                today_date = datetime(today.year, today.month, today.day)
                if event_date_dt < today_date:
                    date_group = 1  # Past event
            except Exception:
                pass
                
        # Freshness timestamp descending
        indexed_timestamp = 0.0
        if first_indexed_str:
            try:
                if len(first_indexed_str) >= 19:
                    dt = datetime.strptime(first_indexed_str[:19], "%Y-%m-%d %H:%M:%S")
                else:
                    dt = datetime.strptime(first_indexed_str[:10], "%Y-%m-%d")
                indexed_timestamp = dt.timestamp()
            except Exception:
                pass
                
        return (priority_group, date_group, -indexed_timestamp)

    matched_events.sort(key=get_priority_key)
    return matched_events


def build_personalized_html(email: str, matched_events: list[dict[str, Any]], interests: list[str], campaign_id: str) -> str:
    """Build a beautiful, personalized newsletter HTML."""
    # Group events by interest for nice rendering
    grouped: dict[str, list[dict[str, Any]]] = {}
    for interest in (interests or INTEREST_DISPLAY.keys()):
        grouped[interest] = []

    for event in matched_events:
        for interest in event.get("matched_interests", []):
            if interest in grouped:
                grouped[interest].append(event)

    # Filter out empty groups
    grouped = {k: v for k, v in grouped.items() if v}

    # Format interest labels for header
    interest_labels = [INTEREST_DISPLAY.get(i, i) for i in interests]
    if not interest_labels:
        interest_labels = ["全部频道 🌟"]
    interests_str = "、".join(interest_labels)

    # Build events HTML blocks
    blocks = []
    if not grouped:
        blocks.append("""
        <div style="text-align: center; padding: 30px; background-color: #f8fafc; border-radius: 12px; border: 1px dashed #cbd5e1; margin: 20px 0;">
            <p style="margin: 0; color: #64748b; font-size: 14px;">📬 本期您的订阅频道暂无新事件更新。</p>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 12px;">我们将在有最新消息时第一时间为您推送！您也可以随时访问官网查看历史汇总。</p>
        </div>
        """)
    else:
        for interest, items in grouped.items():
            label = INTEREST_DISPLAY.get(interest, interest)
            blocks.append(f"""
            <div style="margin-top: 24px; margin-bottom: 16px;">
                <h3 style="color: #c2410c; border-left: 4px solid #ea580c; padding-left: 10px; margin: 0 0 12px 0; font-size: 16px; font-weight: 700;">{label}</h3>
                <div style="margin: 0;">
            """)
            
            # Show up to 5 items per interest to keep email concise
            for item in items[:5]:
                title = item.get("title_zh", "").strip()
                area = item.get("area_zh", "").strip()
                date_str = item.get("event_date", "").strip()
                url = item.get("url", "").strip()
                summary = item.get("summary_zh", "").strip()
                
                # Clean up source types from summary
                if "（来源类型：" in summary:
                    summary = summary.split("（来源类型：")[0].strip()
                elif "(来源类型：" in summary:
                    summary = summary.split("(来源类型：")[0].strip()
                
                meta_parts = []
                if area:
                    meta_parts.append(area)
                if date_str:
                    meta_parts.append(date_str)
                meta = f"（{' · '.join(meta_parts)}）" if meta_parts else ""
                
                link_html = f'<a href="{url}" style="color: #ea580c; text-decoration: none; font-weight: 600; font-size: 13px;">详情&gt;</a>' if url else ""
                
                summary_html = f'<div style="color: #475569; font-size: 13px; margin: 4px 0 6px 0; line-height: 1.5; padding-left: 8px; border-left: 2px solid #e2e8f0;">{summary}</div>' if summary else ""
                
                blocks.append(f"""
                    <div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #f1f5f9;">
                        <div style="color: #0f172a; font-size: 14.5px; font-weight: 700; line-height: 1.4;">{title}<span style="color: #64748b; font-size: 12.5px; font-weight: 400;">{meta}</span></div>
                        {summary_html}
                        <div style="margin-top: 4px;">{link_html}</div>
                    </div>
                """)
            
            if len(items) > 5:
                blocks.append(f"""
                    <div style="margin-top: 12px; margin-bottom: 8px; color: #64748b; font-size: 13px;">
                        <i>👉 更多 {len(items) - 5} 条该频道更新，请前往官网 <a href="https://uslifehub.org" style="color: #ea580c; text-decoration: none; font-weight: 600;">uslifehub.org</a> 查看全部...</i>
                    </div>
                """)
                
            blocks.append("</div></div>")

    events_html = "".join(blocks)

    # Full HTML template
    html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #333333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8fafc;">
  <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 36px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.05);">
    
    <!-- Header -->
    <div style="text-align: center; margin-bottom: 24px;">
      <h1 style="color: #ea580c; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">美东华人生活圈</h1>
      <p style="color: #64748b; margin: 4px 0 0 0; font-size: 13px; font-weight: 500;">官方民生信息汇总 · 纯净省心 · uslifehub.org</p>
    </div>
    
    <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 16px 0;">
    
    <!-- Greeting -->
    <p style="font-size: 15px; color: #334155; margin-top: 0;">您好！这是为您量身定制的<b>美东民生与福利动态精选周报</b>。</p>
    <p style="font-size: 13.5px; color: #64748b; margin-top: -8px;">我们根据您订阅的频道，为您筛选了纽约及美东地区最新、最实用的民生政务、医疗健康与省钱折扣信息。</p>
    
    <!-- Personalized Events Section -->
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 8px 20px; margin: 20px 0;">
        {events_html}
    </div>
    
    <!-- Quick CTA -->
    <div style="background-color: #fff7ed; border: 1px solid #ffedd5; border-radius: 12px; padding: 16px; margin: 24px 0; text-align: center;">
      <p style="margin: 0 0 8px 0; font-weight: 700; color: #c2410c; font-size: 14px;">📱 强烈建议：储存到手机桌面，一键直达</p>
      <p style="margin: 0; color: #9a3412; font-size: 12.5px; line-height: 1.5;">
        将 <b>uslifehub.org</b> 收藏并“添加到手机主屏幕”，在手机上就像使用 App 一样方便，长辈也能一键轻松查阅！
      </p>
    </div>
    
    <!-- Footer Signature -->
    <p style="font-size: 13.5px; color: #64748b; margin: 24px 0 0 0; text-align: right; line-height: 1.6;">
      <b>美东华人生活圈 团队</b> 敬上<br>
      官方网站：<a href="https://uslifehub.org" style="color: #ea580c; text-decoration: none; font-weight: 600;">uslifehub.org</a>
    </p>
    
    <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 24px 0 20px 0;">
    
    <!-- Unsubscribe Footer -->
    <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0; line-height: 1.6;">
      本邮件由美东华人生活圈系统为您自动发送。<br>
      您当前订阅的频道为：<span style="color: #475569; font-weight: 500;">{interests_str}</span>。<br>
      如需调整订阅频道或退订，请点击 <a href="https://uslifehub.org/api/community-hub/unsubscribe?email={email}" style="color: #ea580c; text-decoration: underline; font-weight: 500;">一键退订</a>，或回复本邮件联系 <a href="mailto:info@uslifehub.org" style="color: #ea580c; text-decoration: none;">info@uslifehub.org</a>。
    </p>
  </div>
</body>
</html>"""
    return html


def get_default_campaign_id() -> str:
    """Dynamically group runs into Mon-Wed (Mon campaign) and Thu-Sun (Thu campaign)."""
    now = datetime.now()
    year, week, weekday = now.isocalendar()
    if weekday in (1, 2, 3):  # Monday, Tuesday, Wednesday
        return f"{year}-W{week:02d}-Mon"
    else:  # Thursday, Friday, Saturday, Sunday
        return f"{year}-W{week:02d}-Thu"


def main() -> int:
    ap = argparse.ArgumentParser(description="Send personalized, staggered newsletters to subscribers.")
    ap.add_argument("--campaign-id", type=str, default=None,
                    help="Unique identifier for this campaign. If not provided, automatically groups into Mon/Thu campaigns.")
    ap.add_argument("--max-per-day", type=int, default=250,
                    help="Maximum number of emails to send in this run to stay under daily limits. Default: 250.")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be sent without actually sending.")
    args = ap.parse_args()

    campaign_id = args.campaign_id or get_default_campaign_id()

    print("==================================================")
    print("  Personalized Staggered Newsletter Campaign")
    print("==================================================")
    print(f"Campaign ID: {campaign_id}")
    print(f"Max Sends Today: {args.max_per_day}")
    print(f"Dry Run Mode: {args.dry_run}")
    print("--------------------------------------------------")

    # 1. Load subscriptions and events
    subs = load_subscriptions()
    events = load_events()

    if not subs:
        print("No subscribers found. Exiting.")
        return 0
    if not events:
        print("No events found in search index. Exiting.")
        return 0

    print(f"Loaded {len(subs)} total subscribers.")
    print(f"Loaded {len(events)} total events from search index.")

    # Filter events to only keep recent ones (e.g., updated in the last 7 days)
    # Since we don't have strict timestamps on all records, we'll use all records in the index,
    # as the index itself is already a rolling 30-day window maintained by the live update script.

    # 2. Identify pending subscribers for this campaign
    pending_subs = []
    for s in subs:
        email = s.get("email", "").strip().lower()
        if not email:
            continue
        
        last_campaign = s.get("last_campaign_sent", "")
        if last_campaign == campaign_id:
            # Already received this campaign
            continue
            
        pending_subs.append(s)

    print(f"Found {len(pending_subs)} subscribers pending for campaign '{campaign_id}'.")

    if not pending_subs:
        print("🎉 All subscribers have already received this campaign! Nothing to send.")
        return 0

    # 3. Select up to max_per_day subscribers to send to today
    to_send = pending_subs[:args.max_per_day]
    print(f"Selected {len(to_send)} subscribers for staggered sending today.")
    print("--------------------------------------------------")

    success_count = 0
    fail_count = 0

    # 4. Send personalized emails
    for s in to_send:
        email = s["email"].strip().lower()
        interests = s.get("interests", [])
        
        # Filter events matching this subscriber's interests
        matched = filter_events_for_interests(events, interests)
        
        # Build personalized HTML
        html = build_personalized_html(email, matched, interests, campaign_id)
        subject = f"【美东华人生活圈】您的专属民生福利与省钱动态精选周报 📬 ({campaign_id})"

        if args.dry_run:
            print(f"[Dry-Run] Would send to {email} with {len(matched)} matched events.")
            success_count += 1
            # Update subscription status in dry-run memory
            s["last_campaign_sent"] = campaign_id
            s["last_sent_at"] = datetime.now().isoformat()
        else:
            print(f"Sending personalized newsletter to {email} ({len(matched)} events)...", end="", flush=True)
            success = _se.send_community_email(
                recipient=email,
                subject=subject,
                html_content=html,
                sender_name="美东华人生活圈",
                sender_email="info@uslifehub.org"
            )
            if success:
                print(" ✅ Sent!")
                success_count += 1
                # Update subscription status
                s["last_campaign_sent"] = campaign_id
                s["last_sent_at"] = datetime.now().isoformat()
            else:
                print(" ❌ Failed.")
                fail_count += 1

    print("--------------------------------------------------")
    print(f"Sending complete. Success: {success_count}, Failed: {fail_count}")

    # 5. Save updated subscriptions database if any sent successfully
    if success_count > 0 and not args.dry_run:
        save_subscriptions(subs)
        print("Updated subscriptions database with campaign tracking.")

    # 6. Inform user of remaining queue
    remaining = len(pending_subs) - len(to_send)
    if remaining > 0:
        print(f"📢 Staggered sending active: {remaining} subscribers remain in queue for campaign '{campaign_id}'.")
        print("They will be processed in subsequent runs (e.g., tomorrow).")
    else:
        print("🎉 Campaign fully delivered to all pending subscribers!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
