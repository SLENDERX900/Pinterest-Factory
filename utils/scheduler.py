"""
Enhanced Pinterest scheduling + Notion status sync for Pinterest Factory
"""

from __future__ import annotations

import os
import json
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple

import requests

PINTEREST_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARD_ID = os.getenv("PINTEREST_BOARD_ID", "")
PINTEREST_API_BASE = "https://api.pinterest.com/v5"

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_API_VERSION = "2022-06-28"
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")


def build_optimized_schedule_slots(count: int, start_dt: datetime | None = None) -> list[datetime]:
    """
    Build optimized schedule slots with better timing for Pinterest engagement
    """
    base = start_dt or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    # Optimal posting times for Pinterest (based on engagement data)
    optimal_times = [
        timedelta(hours=8),   # 8 AM
        timedelta(hours=12),  # 12 PM (lunch break)
        timedelta(hours=15),  # 3 PM (afternoon)
        timedelta(hours=20),  # 8 PM (evening)
    ]
    
    schedule_slots = []
    for i in range(count):
        # Rotate through optimal times
        day_offset = i // len(optimal_times)
        time_offset = optimal_times[i % len(optimal_times)]
        
        slot_time = base + timedelta(days=day_offset) + time_offset
        
        # Skip times in the past
        if slot_time > datetime.now(timezone.utc):
            schedule_slots.append(slot_time)
    
    return schedule_slots[:count]


def schedule_pinterest_factory_batch(recipe_data: Dict, generated_pins: List[Dict]) -> Dict:
    """
    Schedule a complete Pinterest Factory batch (5 pins with different angles)
    """
    print(f"📅 Scheduling Pinterest Factory batch for: {recipe_data.get('name', 'Unknown recipe')}")
    
    if not PINTEREST_TOKEN or not PINTEREST_BOARD_ID:
        return {"success": False, "error": "Pinterest credentials missing"}
    
    # Build schedule slots
    schedule_slots = build_optimized_schedule_slots(len(generated_pins))
    
    scheduled_pins = []
    failed_pins = []
    
    for i, (pin_data, schedule_time) in enumerate(zip(generated_pins, schedule_slots)):
        print(f"📌 Scheduling pin {i+1}/{len(generated_pins)} for {schedule_time.strftime('%Y-%m-%d %H:%M')}")
        
        # Prepare pin data
        hook = pin_data.get('hook', '')
        description = pin_data.get('description', '')
        vibe_prompt = pin_data.get('vibe_prompt', '')
        
        # Create compelling title
        title = f"{hook} - {recipe_data.get('name', 'Recipe')}"
        
        # Get image URL (could be base64 or URL)
        image_url = pin_data.get('image_url', '')
        if pin_data.get('image_base64'):
            # For base64 images, we'd need to upload to a hosting service first
            # For now, use original recipe image as fallback
            image_url = recipe_data.get('image_url', '')
        
        # Create enhanced description
        enhanced_description = f"{description}\n\n{vibe_prompt}"
        
        # Schedule the pin
        success, result = schedule_pin(
            title=title,
            description=enhanced_description,
            link=recipe_data.get('url', ''),
            image_url=image_url,
            publish_at=schedule_time
        )
        
        pin_info = {
            "index": i + 1,
            "hook": hook,
            "angle": pin_data.get('angle', 'Unknown'),
            "scheduled_time": schedule_time.isoformat(),
            "title": title
        }
        
        if success:
            pin_info.update({
                "pinterest_pin_id": result,
                "status": "scheduled"
            })
            scheduled_pins.append(pin_info)
            print(f"✅ Pin {i+1} scheduled successfully (ID: {result})")
        else:
            pin_info.update({
                "error": result,
                "status": "failed"
            })
            failed_pins.append(pin_info)
            print(f"❌ Pin {i+1} failed to schedule: {result}")
        
        # Rate limiting
        time.sleep(1)
    
    # Update Notion with batch results
    notion_results = update_notion_batch_status(recipe_data, scheduled_pins, failed_pins)
    
    return {
        "success": len(scheduled_pins) > 0,
        "recipe_name": recipe_data.get('name', 'Unknown'),
        "total_pins": len(generated_pins),
        "scheduled_pins": scheduled_pins,
        "failed_pins": failed_pins,
        "notion_updates": notion_results,
        "schedule_summary": {
            "first_pin": schedule_slots[0].isoformat() if schedule_slots else None,
            "last_pin": schedule_slots[-1].isoformat() if schedule_slots else None,
            "success_rate": len(scheduled_pins) / len(generated_pins)
        }
    }


def schedule_pin(title: str, description: str, link: str, image_url: str, publish_at: datetime) -> tuple[bool, str]:
    """
    Enhanced pin scheduling with better error handling
    """
    if not PINTEREST_TOKEN or not PINTEREST_BOARD_ID:
        return False, "Pinterest credentials missing"
    
    # Validate publish time (must be in future)
    if publish_at <= datetime.now(timezone.utc):
        return False, "Publish time must be in the future"
    
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
        print(f"📤 Sending to Pinterest API: {title[:50]}...")
        resp = requests.post(f"{PINTEREST_API_BASE}/pins", headers=headers, json=body, timeout=30)
        
        if resp.status_code in (200, 201):
            pin_data = resp.json()
            pin_id = pin_data.get("id", "scheduled")
            print(f"✅ Pin scheduled successfully: {pin_id}")
            return True, pin_id
        else:
            error_msg = f"Pinterest API {resp.status_code}: {resp.text[:200]}"
            print(f"❌ Pinterest API error: {error_msg}")
            return False, error_msg
            
    except requests.exceptions.RequestException as exc:
        error_msg = f"Network error: {str(exc)}"
        print(f"❌ Network error: {error_msg}")
        return False, error_msg
    except Exception as exc:
        error_msg = f"Unexpected error: {str(exc)}"
        print(f"❌ Unexpected error: {error_msg}")
        return False, error_msg


def update_notion_batch_status(recipe_data: Dict, scheduled_pins: List[Dict], failed_pins: List[Dict]) -> Dict:
    """
    Update Notion database with batch scheduling results
    """
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return {"success": False, "error": "Notion credentials missing"}
    
    print(f"📝 Updating Notion database with scheduling results...")
    
    # Create summary text for Notion
    total_pins = len(scheduled_pins) + len(failed_pins)
    success_rate = len(scheduled_pins) / total_pins if total_pins > 0 else 0
    
    # Build schedule times string
    if scheduled_pins:
        schedule_times = [pin['scheduled_time'][:16] for pin in scheduled_pins]  # Format: YYYY-MM-DD HH:MM
        schedule_summary = f"Scheduled: {', '.join(schedule_times)}"
    else:
        schedule_summary = "No pins scheduled"
    
    # Create or update Notion page for this recipe
    notion_result = create_or_update_notion_page(
        recipe_data=recipe_data,
        status="Scheduled" if scheduled_pins else "Failed",
        scheduled_count=len(scheduled_pins),
        failed_count=len(failed_pins),
        success_rate=success_rate,
        schedule_summary=schedule_summary,
        pin_details=scheduled_pins + failed_pins
    )
    
    return notion_result


def create_or_update_notion_page(recipe_data: Dict, status: str, scheduled_count: int, 
                               failed_count: int, success_rate: float, 
                               schedule_summary: str, pin_details: List[Dict]) -> Dict:
    """
    Create or update a Notion page with recipe scheduling information
    """
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }
    
    # Prepare page properties
    properties = {
        "Recipe Name": {"title": [{"text": {"content": recipe_data.get('name', 'Unknown')}}]},
        "Status": {"select": {"name": status}},
        "Scheduled Pins": {"number": scheduled_count},
        "Failed Pins": {"number": failed_count},
        "Success Rate": {"percent": success_rate},
        "Schedule Summary": {"rich_text": [{"text": {"content": schedule_summary}}]},
        "Cook Time": {"rich_text": [{"text": {"content": recipe_data.get('time', '')}}]},
        "Ingredient Count": {"number": int(recipe_data.get('ingredients', 0)) if recipe_data.get('ingredients', '').isdigit() else 0},
        "Benefit": {"select": {"name": recipe_data.get('benefit', 'Unknown')}},
        "Recipe URL": {"url": recipe_data.get('url', '')},
    }
    
    # Try to find existing page first
    existing_page_id = find_existing_notion_page(recipe_data.get('name', ''))
    
    try:
        if existing_page_id:
            # Update existing page
            url = f"https://api.notion.com/v1/pages/{existing_page_id}"
            resp = requests.patch(url, headers=headers, json={"properties": properties}, timeout=20)
        else:
            # Create new page
            url = f"https://api.notion.com/v1/pages"
            payload = {
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": properties
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
        
        if resp.status_code == 200:
            page_data = resp.json()
            page_id = page_data.get("id", "")
            
            # Add pin details as children blocks
            if pin_details:
                add_pin_details_to_page(page_id, pin_details)
            
            print(f"✅ Notion page {'updated' if existing_page_id else 'created'}: {page_id}")
            return {"success": True, "page_id": page_id, "action": "updated" if existing_page_id else "created"}
        else:
            error_msg = f"Notion API {resp.status_code}: {resp.text[:200]}"
            print(f"❌ Notion error: {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as exc:
        error_msg = f"Notion update error: {str(exc)}"
        print(f"❌ Notion error: {error_msg}")
        return {"success": False, "error": error_msg}


def find_existing_notion_page(recipe_name: str) -> Optional[str]:
    """
    Find existing Notion page for this recipe
    """
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return None
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }
    
    # Search for existing page
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "Recipe Name",
            "title": {"equals": recipe_name}
        }
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                return results[0].get("id")
    except Exception:
        pass
    
    return None


def add_pin_details_to_page(page_id: str, pin_details: List[Dict]) -> None:
    """
    Add detailed pin information as children blocks to Notion page
    """
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }
    
    # Create children blocks for pin details
    children = []
    
    # Add heading
    children.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"text": {"content": "📌 Pin Scheduling Details"}}]
        }
    })
    
    # Add each pin's details
    for pin in pin_details:
        status_emoji = "✅" if pin.get('status') == 'scheduled' else "❌"
        pin_text = f"{status_emoji} **{pin.get('hook', 'Unknown')}** ({pin.get('angle', 'Unknown')})"
        
        if pin.get('scheduled_time'):
            pin_text += f" - Scheduled: {pin.get('scheduled_time', '')[:16]}"
        if pin.get('error'):
            pin_text += f" - Error: {pin.get('error', 'Unknown error')}"
        
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"text": {"content": pin_text}}]
            }
        })
    
    # Add children to page
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    payload = {"children": children}
    
    try:
        requests.patch(url, headers=headers, json=payload, timeout=20)
    except Exception as e:
        print(f"⚠️ Could not add pin details to Notion: {e}")


def update_notion_item_scheduled(page_id: str, scheduled_ts: datetime) -> tuple[bool, str]:
    """
    Legacy function - maintained for backward compatibility
    """
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


def build_schedule_slots(count: int, start_dt: datetime | None = None) -> list[datetime]:
    """
    Legacy function - maintained for backward compatibility
    """
    return build_optimized_schedule_slots(count, start_dt)
