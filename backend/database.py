import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL was not found in .env")
if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY was not found in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_user_from_token(token: str):
    response = supabase.auth.get_user(token)
    if not response.user:
        raise RuntimeError("Invalid authentication token.")
    return response.user


def save_plan(user_id: str, original_text: str, outcome: dict):
    plan_response = (
        supabase.table("plans")
        .insert(
            {
                "user_id": user_id,
                "original_text": original_text,
                "goal": outcome["goal"],
                "summary": outcome.get("summary", ""),
            }
        )
        .execute()
    )
    if not plan_response.data:
        raise RuntimeError("Could not save plan.")

    plan_id = plan_response.data[0]["id"]

    required_items = outcome.get("required_items", [])
    if required_items:
        supabase.table("required_items").insert(
            [{"plan_id": plan_id, "item": item} for item in required_items]
        ).execute()

    actions = outcome.get("actions", [])
    if actions:
        rows = []
        for action in actions:
            rows.append(
                {
                    "plan_id": plan_id,
                    "action_number": action["id"],
                    "title": action["title"],
                    "type": action.get("type", "task"),
                    "deadline": action.get("deadline"),
                    "priority": action.get("priority", "medium"),
                    "confidence": action.get("confidence", 0.5),
                    "status": action.get("status", "pending"),
                    "needs_confirmation": action.get("needs_confirmation", False),
                    "reason": action.get("reason", ""),
                    "depends_on": action.get("depends_on", []),
                }
            )
        supabase.table("actions").insert(rows).execute()

    return {"plan_id": plan_id, "message": "Plan saved successfully"}


def get_user_plans(user_id: str):
    response = (
        supabase.table("plans")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    results = []
    for plan in response.data or []:
        action_response = (
            supabase.table("actions")
            .select("id,status")
            .eq("plan_id", plan["id"])
            .execute()
        )
        actions = action_response.data or []
        results.append(
            {
                "id": plan["id"],
                "goal": plan["goal"],
                "summary": plan.get("summary", ""),
                "created_at": plan.get("created_at"),
                "total_actions": len(actions),
                "completed_actions": sum(
                    1 for action in actions if action.get("status") == "completed"
                ),
            }
        )
    return results


def get_plan_by_id(user_id: str, plan_id: str):
    plan_response = (
        supabase.table("plans")
        .select("*")
        .eq("id", plan_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not plan_response.data:
        raise RuntimeError("Plan not found.")
    plan = plan_response.data[0]

    actions_response = (
        supabase.table("actions")
        .select("*")
        .eq("plan_id", plan_id)
        .order("action_number")
        .execute()
    )
    items_response = (
        supabase.table("required_items")
        .select("*")
        .eq("plan_id", plan_id)
        .execute()
    )

    return {
        "id": plan["id"],
        "goal": plan["goal"],
        "summary": plan.get("summary", ""),
        "original_text": plan.get("original_text", ""),
        "created_at": plan.get("created_at"),
        "required_items": [item["item"] for item in (items_response.data or [])],
        "actions": actions_response.data or [],
    }


def _get_action_owned_by_user(user_id: str, action_id: str):
    action_response = (
        supabase.table("actions").select("*").eq("id", action_id).execute()
    )
    if not action_response.data:
        raise RuntimeError("Action not found.")
    action = action_response.data[0]

    plan_response = (
        supabase.table("plans")
        .select("id,goal")
        .eq("id", action["plan_id"])
        .eq("user_id", user_id)
        .execute()
    )
    if not plan_response.data:
        raise RuntimeError("Unauthorized action.")
    return action, plan_response.data[0]


def update_action_status(user_id: str, action_id: str, status: str):
    _get_action_owned_by_user(user_id, action_id)
    response = (
        supabase.table("actions")
        .update({"status": status})
        .eq("id", action_id)
        .execute()
    )
    if not response.data:
        raise RuntimeError("Could not update action status.")
    return response.data[0]


def create_reminder(user_id: str, action_id: str, remind_at: str):
    _get_action_owned_by_user(user_id, action_id)
    response = (
        supabase.table("reminders")
        .insert(
            {
                "user_id": user_id,
                "action_id": action_id,
                "remind_at": remind_at,
                "status": "pending",
            }
        )
        .execute()
    )
    if not response.data:
        raise RuntimeError("Could not create reminder.")
    return response.data[0]


def get_action_reminders(user_id: str, action_id: str):
    _get_action_owned_by_user(user_id, action_id)
    response = (
        supabase.table("reminders")
        .select("*")
        .eq("user_id", user_id)
        .eq("action_id", action_id)
        .order("remind_at")
        .execute()
    )
    return response.data or []


def delete_reminder(user_id: str, reminder_id: str):
    response = (
        supabase.table("reminders")
        .delete()
        .eq("id", reminder_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        raise RuntimeError("Reminder not found.")
    return response.data[0]


def save_google_connection(user_id: str, refresh_token: str, scopes: str = ""):
    response = (
        supabase.table("google_connections")
        .upsert(
            {"user_id": user_id, "refresh_token": refresh_token, "scopes": scopes},
            on_conflict="user_id",
        )
        .execute()
    )
    if not response.data:
        raise RuntimeError("Could not save Google connection.")
    return response.data[0]


def get_google_connection(user_id: str):
    response = (
        supabase.table("google_connections")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return response.data[0] if response.data else None


def delete_google_connection(user_id: str):
    supabase.table("google_connections").delete().eq("user_id", user_id).execute()
    return {"disconnected": True}


def get_action_for_user(user_id: str, action_id: str):
    action, plan = _get_action_owned_by_user(user_id, action_id)
    return {"action": action, "plan": plan}


def mark_action_auto_scheduled(
    user_id: str,
    action_id: str,
    scheduled_start: str,
    duration_minutes: int,
    calendar_event_id: str | None,
    calendar_event_link: str | None,
):
    _get_action_owned_by_user(user_id, action_id)
    response = (
        supabase.table("actions")
        .update(
            {
                "scheduled_start": scheduled_start,
                "duration_minutes": duration_minutes,
                "calendar_event_id": calendar_event_id,
                "calendar_event_link": calendar_event_link,
                "auto_scheduled": True,
            }
        )
        .eq("id", action_id)
        .execute()
    )
    if not response.data:
        raise RuntimeError("Could not mark action as scheduled.")
    return response.data[0]
