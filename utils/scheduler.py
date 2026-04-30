"""
Pinterest scheduling + Notion status sync helpers.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

PINTEREST_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARD_ID = os.getenv("PINTEREST_BOARD_ID", "")
PINTEREST_API_BASE = "https://api.pinterest.com/v5"

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_API_VERSION = "2022-06-28"


def build_schedule_slots(count: int, start_dt: datetime | None = None) -> list[datetime]:
    base = start_dt or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    return [base + timedelta(days=i) for i in range(count)]


def schedule_pin(title: str, description: str, link: str, image_url: str, publish_at: datetime) -> tuple[bool, str]:
    if not PINTEREST_TOKEN or not PINTEREST_BOARD_ID:
        return False, "Pinterest credentials missing"
    body = {
        "board_id": PINTEREST_BOARD_ID,
        "title": title[:100],
        "description": description[:800],
        "link": link,
        "media_source": {"source_type": "image_url", "url": image_url},
        "publish_at": publish_at.isoformat(),
    }
    headers = {"Authorization": f"Bearer {PINTEREST_TOKEN}", "Content-Type": "application/json"}
    try:
        resp = requests.post(f"{PINTEREST_API_BASE}/pins", headers=headers, json=body, timeout=30)
        if resp.status_code in (200, 201):
            return True, resp.json().get("id", "scheduled")
        return False, f"{resp.status_code}: {resp.text[:200]}"
    except Exception as exc:
        return False, str(exc)


def update_notion_item_scheduled(page_id: str, scheduled_ts: datetime) -> tuple[bool, str]:
    if not NOTION_TOKEN:
        return False, "Notion token missing"
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }
    payload = {
        "properties": {
            "Status": {"select": {"name": "Scheduled"}},
            "Scheduled At": {"date": {"start": scheduled_ts.isoformat()}},
        }
    }
    try:
        resp = requests.patch(url, headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            return True, "updated"
        return False, f"{resp.status_code}: {resp.text[:200]}"
    except Exception as exc:
        return False, str(exc)
