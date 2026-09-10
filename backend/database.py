import os

from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL was not found in .env"
    )


if not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_KEY was not found in .env"
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# AUTH
# ============================================================

def get_user_from_token(token: str):

    response = supabase.auth.get_user(token)

    if not response.user:
        raise RuntimeError(
            "Invalid authentication token."
        )

    return response.user


# ============================================================
# SAVE PLAN
# ============================================================

def save_plan(
    user_id: str,
    original_text: str,
    outcome: dict
):

    plan_response = (
        supabase
        .table("plans")
        .insert({
            "user_id": user_id,
            "original_text": original_text,
            "goal": outcome["goal"],
            "summary": outcome.get(
                "summary",
                ""
            ),
        })
        .execute()
    )

    if not plan_response.data:
        raise RuntimeError(
            "Could not save plan."
        )

    plan_id = plan_response.data[0]["id"]


    # --------------------------------------------------------
    # REQUIRED ITEMS
    # --------------------------------------------------------

    required_items = outcome.get(
        "required_items",
        []
    )

    if required_items:

        rows = [
            {
                "plan_id": plan_id,
                "item": item,
            }
            for item in required_items
        ]

        (
            supabase
            .table("required_items")
            .insert(rows)
            .execute()
        )


    # --------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------

    actions = outcome.get(
        "actions",
        []
    )

    if actions:

        rows = []

        for action in actions:

            rows.append({
                "plan_id":
                    plan_id,

                "action_number":
                    action["id"],

                "title":
                    action["title"],

                "type":
                    action.get(
                        "type",
                        "task"
                    ),

                "deadline":
                    action.get(
                        "deadline"
                    ),

                "priority":
                    action.get(
                        "priority",
                        "medium"
                    ),

                "confidence":
                    action.get(
                        "confidence",
                        0.5
                    ),

                "status":
                    action.get(
                        "status",
                        "pending"
                    ),

                "needs_confirmation":
                    action.get(
                        "needs_confirmation",
                        False
                    ),

                "reason":
                    action.get(
                        "reason",
                        ""
                    ),

                "depends_on":
                    action.get(
                        "depends_on",
                        []
                    ),
            })


        (
            supabase
            .table("actions")
            .insert(rows)
            .execute()
        )


    return {
        "plan_id": plan_id,
        "message": "Plan saved successfully"
    }


# ============================================================
# LIST USER PLANS
# ============================================================

def get_user_plans(
    user_id: str
):

    plan_response = (
        supabase
        .table("plans")
        .select("*")
        .eq(
            "user_id",
            user_id
        )
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    plans = (
        plan_response.data
        or []
    )

    results = []


    for plan in plans:

        plan_id = plan["id"]

        action_response = (
            supabase
            .table("actions")
            .select(
                "id,status"
            )
            .eq(
                "plan_id",
                plan_id
            )
            .execute()
        )

        actions = (
            action_response.data
            or []
        )

        total_actions = len(
            actions
        )

        completed_actions = len([
            action
            for action in actions
            if action.get(
                "status"
            ) == "completed"
        ])


        results.append({
            "id":
                plan["id"],

            "goal":
                plan["goal"],

            "summary":
                plan.get(
                    "summary",
                    ""
                ),

            "created_at":
                plan.get(
                    "created_at"
                ),

            "total_actions":
                total_actions,

            "completed_actions":
                completed_actions,
        })


    return results


# ============================================================
# GET SINGLE PLAN
# ============================================================

def get_plan_by_id(
    user_id: str,
    plan_id: str
):

    plan_response = (
        supabase
        .table("plans")
        .select("*")
        .eq(
            "id",
            plan_id
        )
        .eq(
            "user_id",
            user_id
        )
        .single()
        .execute()
    )

    plan = (
        plan_response.data
    )

    if not plan:
        raise RuntimeError(
            "Plan not found."
        )


    actions_response = (
        supabase
        .table("actions")
        .select("*")
        .eq(
            "plan_id",
            plan_id
        )
        .order(
            "action_number"
        )
        .execute()
    )


    items_response = (
        supabase
        .table("required_items")
        .select("*")
        .eq(
            "plan_id",
            plan_id
        )
        .execute()
    )


    return {
        "id":
            plan["id"],

        "goal":
            plan["goal"],

        "summary":
            plan.get(
                "summary",
                ""
            ),

        "original_text":
            plan.get(
                "original_text",
                ""
            ),

        "created_at":
            plan.get(
                "created_at"
            ),

        "required_items": [
            item["item"]
            for item in (
                items_response.data
                or []
            )
        ],

        "actions":
            actions_response.data
            or [],
    }


# ============================================================
# UPDATE ACTION STATUS
# ============================================================

def update_action_status(
    user_id: str,
    action_id: str,
    status: str
):

    action_response = (
        supabase
        .table("actions")
        .select(
            "id,plan_id"
        )
        .eq(
            "id",
            action_id
        )
        .single()
        .execute()
    )

    action = (
        action_response.data
    )

    if not action:
        raise RuntimeError(
            "Action not found."
        )


    plan_response = (
        supabase
        .table("plans")
        .select("id")
        .eq(
            "id",
            action["plan_id"]
        )
        .eq(
            "user_id",
            user_id
        )
        .single()
        .execute()
    )

    if not plan_response.data:
        raise RuntimeError(
            "Unauthorized action."
        )


    result = (
        supabase
        .table("actions")
        .update({
            "status": status
        })
        .eq(
            "id",
            action_id
        )
        .execute()
    )


    if not result.data:
        raise RuntimeError(
            "Could not update action status."
        )


    return result.data[0]


# ============================================================
# REMINDERS
# ============================================================

def create_reminder(
    user_id: str,
    action_id: str,
    remind_at: str
):

    action_response = (
        supabase
        .table("actions")
        .select(
            "id,plan_id"
        )
        .eq(
            "id",
            action_id
        )
        .single()
        .execute()
    )

    action = (
        action_response.data
    )

    if not action:
        raise RuntimeError(
            "Action not found."
        )


    plan_response = (
        supabase
        .table("plans")
        .select("id")
        .eq(
            "id",
            action["plan_id"]
        )
        .eq(
            "user_id",
            user_id
        )
        .single()
        .execute()
    )

    if not plan_response.data:
        raise RuntimeError(
            "Unauthorized action."
        )


    reminder_response = (
        supabase
        .table("reminders")
        .insert({
            "user_id":
                user_id,

            "action_id":
                action_id,

            "remind_at":
                remind_at,

            "status":
                "pending",
        })
        .execute()
    )


    if not reminder_response.data:
        raise RuntimeError(
            "Could not create reminder."
        )


    return (
        reminder_response
        .data[0]
    )


def get_action_reminders(
    user_id: str,
    action_id: str
):

    response = (
        supabase
        .table("reminders")
        .select("*")
        .eq(
            "user_id",
            user_id
        )
        .eq(
            "action_id",
            action_id
        )
        .order(
            "remind_at"
        )
        .execute()
    )


    return (
        response.data
        or []
    )


def delete_reminder(
    user_id: str,
    reminder_id: str
):

    response = (
        supabase
        .table("reminders")
        .delete()
        .eq(
            "id",
            reminder_id
        )
        .eq(
            "user_id",
            user_id
        )
        .execute()
    )


    if not response.data:
        raise RuntimeError(
            "Reminder not found."
        )


    return response.data[0]


# ============================================================
# GOOGLE CALENDAR CONNECTION
# ============================================================

def save_google_connection(
    user_id: str,
    refresh_token: str,
    scopes: str = ""
):

    response = (
        supabase
        .table(
            "google_connections"
        )
        .upsert(
            {
                "user_id":
                    user_id,

                "refresh_token":
                    refresh_token,

                "scopes":
                    scopes,
            },
            on_conflict="user_id"
        )
        .execute()
    )


    if not response.data:
        raise RuntimeError(
            "Could not save Google connection."
        )


    return response.data[0]


def get_google_connection(
    user_id: str
):

    response = (
        supabase
        .table(
            "google_connections"
        )
        .select("*")
        .eq(
            "user_id",
            user_id
        )
        .execute()
    )


    if not response.data:
        return None


    return response.data[0]


def delete_google_connection(
    user_id: str
):

    response = (
        supabase
        .table(
            "google_connections"
        )
        .delete()
        .eq(
            "user_id",
            user_id
        )
        .execute()
    )


    return {
        "disconnected": True
    }
def get_action_for_user(
    user_id: str,
    action_id: str
):
    action_response = (
        supabase
        .table("actions")
        .select("*")
        .eq("id", action_id)
        .single()
        .execute()
    )

    action = action_response.data

    if not action:
        raise RuntimeError(
            "Action not found."
        )

    plan_response = (
        supabase
        .table("plans")
        .select("id,goal")
        .eq("id", action["plan_id"])
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    plan = plan_response.data

    if not plan:
        raise RuntimeError(
            "Unauthorized action."
        )

    return {
        "action": action,
        "plan": plan,
    }