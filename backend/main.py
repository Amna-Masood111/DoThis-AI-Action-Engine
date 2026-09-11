import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo

from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from PIL import Image
from pydantic import BaseModel, Field
from pypdf import PdfReader

from ai_engine import analyze_with_ai, build_execution_schedule_with_ai
from database import (
    create_reminder,
    delete_google_connection,
    delete_reminder,
    get_action_for_user,
    get_action_reminders,
    get_google_connection,
    get_plan_by_id,
    get_user_from_token,
    get_user_plans,
    mark_action_auto_scheduled,
    save_google_connection,
    save_plan,
    update_action_status,
)
from google_calendar import (
    create_calendar_event,
    create_google_flow,
    generate_pkce,
    oauth_requests,
)
from validator import validate_outcome

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

app = FastAPI(
    title="DoThis API",
    description="Turn information into structured outcomes and execute them.",
    version="1.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        {
            FRONTEND_URL,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODELS
# ============================================================

class ActionRequest(BaseModel):
    text: str


class ActionItem(BaseModel):
    id: int
    title: str
    type: str = "task"
    deadline: Optional[str] = None
    depends_on: List[int] = Field(default_factory=list)
    priority: str = "medium"
    confidence: float = 0.5
    status: str = "pending"
    needs_confirmation: bool = False
    reason: str = ""


class OutcomeResult(BaseModel):
    goal: str
    summary: str = ""
    required_items: List[str] = Field(default_factory=list)
    actions: List[ActionItem] = Field(default_factory=list)


class SavePlanRequest(BaseModel):
    original_text: str
    outcome: OutcomeResult


class UpdateActionStatusRequest(BaseModel):
    status: str


class CreateReminderRequest(BaseModel):
    remind_at: str


class CreateCalendarEventRequest(BaseModel):
    start_datetime: str
    duration_minutes: int = 60
    timezone: str = "Asia/Karachi"


class SchedulePreviewRequest(BaseModel):
    timezone: str = "Asia/Karachi"


class ScheduleItemRequest(BaseModel):
    action_id: str
    action_number: int
    scheduled_start: str
    duration_minutes: int
    reminder_minutes_before: int
    rationale: str = ""


class ApproveScheduleRequest(BaseModel):
    timezone: str = "Asia/Karachi"
    schedule: List[ScheduleItemRequest]


# ============================================================
# AUTH HELPERS
# ============================================================

def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication header.")
    return authorization.replace("Bearer ", "", 1)


def get_authenticated_user(authorization: str | None):
    return get_user_from_token(extract_bearer_token(authorization))


def _get_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception as error:
        raise HTTPException(status_code=400, detail="Invalid timezone.") from error


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def home():
    return {"app": "DoThis", "version": "1.3.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


# ============================================================
# AI ANALYSIS
# ============================================================

@app.post("/analyze", response_model=OutcomeResult)
def analyze(request: ActionRequest):
    clean_text = request.text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Please provide information to analyze.")
    if len(clean_text) > 15000:
        raise HTTPException(status_code=400, detail="Input is too long for the current MVP.")

    try:
        data = json.loads(analyze_with_ai(clean_text))
        return OutcomeResult(**validate_outcome(data, clean_text))
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=500, detail="AI returned invalid JSON. Please try again.") from error
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        print("AI ERROR:", repr(error))
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(error)}") from error


# ============================================================
# FILE / SCREENSHOT TEXT EXTRACTION
# ============================================================

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _extract_upload_text(filename: str, content_type: str, raw: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()

    if suffix in {".txt", ".md", ".csv"} or content_type.startswith("text/"):
        return raw.decode("utf-8", errors="ignore").strip()

    if suffix == ".pdf" or content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()

    if suffix == ".docx" or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        document = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in document.paragraphs if p.text.strip()).strip()

    if content_type.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            import pytesseract
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            return pytesseract.image_to_string(image).strip()
        except Exception as error:
            raise RuntimeError(
                "Image OCR is not available on this server yet. Install Tesseract OCR, then restart the backend."
            ) from error

    raise RuntimeError("Unsupported file type. Use PDF, DOCX, TXT, MD, CSV, PNG, JPG or WEBP.")


@app.post("/extract-file")
async def extract_file(file: UploadFile = File(...)):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File is too large. Maximum size is 10 MB.")
    try:
        text = _extract_upload_text(file.filename or "upload", file.content_type or "", raw)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not text.strip():
        raise HTTPException(status_code=400, detail="No readable text was found in this file.")
    return {"filename": file.filename, "text": text[:15000]}


# ============================================================
# PLANS
# ============================================================

@app.post("/plans")
def create_plan(request: SavePlanRequest, authorization: str | None = Header(default=None)):
    try:
        user = get_authenticated_user(authorization)
        return save_plan(user.id, request.original_text, request.outcome.model_dump())
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not save plan: {str(error)}") from error


@app.get("/plans")
def list_plans(authorization: str | None = Header(default=None)):
    try:
        user = get_authenticated_user(authorization)
        return {"plans": get_user_plans(user.id)}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not load plans: {str(error)}") from error


@app.get("/plans/{plan_id}")
def read_plan(plan_id: str, authorization: str | None = Header(default=None)):
    try:
        user = get_authenticated_user(authorization)
        return get_plan_by_id(user.id, plan_id)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not load plan: {str(error)}") from error


# ============================================================
# SMART EXECUTION SCHEDULING
# ============================================================

def _fallback_schedule(actions: list[dict], local_now: datetime) -> list[dict]:
    unscheduled = [
        a for a in actions
        if a.get("status") != "completed" and not a.get("auto_scheduled", False)
    ]
    if not unscheduled:
        return []

    # Simple dependency-aware ordering by repeatedly taking actions whose prerequisites
    # have already been placed. Falls back to action number if input is inconsistent.
    remaining = {int(a.get("action_number", 0)): a for a in unscheduled}
    ordered = []
    completed_numbers: set[int] = set()
    guard = 0
    while remaining and guard < len(remaining) * 3 + 10:
        guard += 1
        ready = []
        for number, action in remaining.items():
            deps = [int(x) for x in (action.get("depends_on") or []) if isinstance(x, int)]
            if all(dep in completed_numbers or dep not in remaining for dep in deps):
                ready.append((number, action))
        if not ready:
            ready = [min(remaining.items(), key=lambda pair: pair[0])]
        ready.sort(key=lambda pair: (0 if pair[1].get("priority") == "high" else 1, pair[0]))
        number, action = ready[0]
        ordered.append(action)
        completed_numbers.add(number)
        remaining.pop(number, None)

    cursor = local_now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    if cursor.hour >= 18:
        cursor = (cursor + timedelta(days=1)).replace(hour=9)
    elif cursor.hour < 9:
        cursor = cursor.replace(hour=9)

    schedule = []
    for action in ordered:
        if cursor.hour >= 17:
            cursor = (cursor + timedelta(days=1)).replace(hour=9)
        duration = 60 if action.get("priority") != "low" else 45
        reminder = 180 if action.get("priority") == "high" else 60
        schedule.append(
            {
                "action_number": int(action.get("action_number", 0)),
                "scheduled_start": cursor.replace(tzinfo=None).isoformat(timespec="seconds"),
                "duration_minutes": duration,
                "reminder_minutes_before": reminder,
                "rationale": "Suggested automatically from priority and dependency order.",
            }
        )
        cursor += timedelta(minutes=duration + 30)
    return schedule


def _normalize_schedule(plan: dict, raw_schedule: list[dict], local_now: datetime) -> list[dict]:
    action_by_number = {
        int(a["action_number"]): a
        for a in plan.get("actions", [])
        if a.get("action_number") is not None
    }
    valid_durations = {30, 45, 60, 90, 120}
    valid_reminders = {30, 60, 180, 720, 1440}
    result = []
    used_numbers: set[int] = set()

    for item in raw_schedule:
        try:
            number = int(item.get("action_number"))
        except (TypeError, ValueError):
            continue
        action = action_by_number.get(number)
        if not action or action.get("status") == "completed" or action.get("auto_scheduled") or number in used_numbers:
            continue
        try:
            start = datetime.fromisoformat(str(item.get("scheduled_start")))
        except (TypeError, ValueError):
            continue
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)
        if start <= local_now.replace(tzinfo=None) + timedelta(minutes=5):
            continue

        duration = int(item.get("duration_minutes", 60))
        reminder = int(item.get("reminder_minutes_before", 60))
        if duration not in valid_durations:
            duration = 60
        if reminder not in valid_reminders:
            reminder = 60

        result.append(
            {
                "action_id": str(action["id"]),
                "action_number": number,
                "title": action.get("title", "Action"),
                "scheduled_start": start.isoformat(timespec="seconds"),
                "duration_minutes": duration,
                "reminder_minutes_before": reminder,
                "rationale": str(item.get("rationale", "")).strip(),
            }
        )
        used_numbers.add(number)

    # Fill any missing actions with a deterministic fallback so the feature is reliable
    # even if the model omits an item.
    missing_actions = [
        a for number, a in action_by_number.items()
        if number not in used_numbers and a.get("status") != "completed" and not a.get("auto_scheduled")
    ]
    if missing_actions:
        fallback = _fallback_schedule(missing_actions, local_now)
        latest = max(
            [datetime.fromisoformat(x["scheduled_start"]) for x in result],
            default=local_now.replace(tzinfo=None),
        )
        for item in fallback:
            action = action_by_number.get(int(item["action_number"]))
            if not action:
                continue
            start = datetime.fromisoformat(item["scheduled_start"])
            if start <= latest:
                start = latest + timedelta(minutes=90)
                if start.hour >= 18:
                    start = (start + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            latest = start
            result.append(
                {
                    "action_id": str(action["id"]),
                    "action_number": int(item["action_number"]),
                    "title": action.get("title", "Action"),
                    "scheduled_start": start.isoformat(timespec="seconds"),
                    "duration_minutes": item["duration_minutes"],
                    "reminder_minutes_before": item["reminder_minutes_before"],
                    "rationale": item["rationale"],
                }
            )

    result.sort(key=lambda x: x["scheduled_start"])
    return result


@app.post("/plans/{plan_id}/schedule-preview")
def schedule_preview(
    plan_id: str,
    request: SchedulePreviewRequest,
    authorization: str | None = Header(default=None),
):
    try:
        user = get_authenticated_user(authorization)
        tz = _get_timezone(request.timezone)
        local_now = datetime.now(tz)
        plan = get_plan_by_id(user.id, plan_id)

        remaining = [
            a for a in plan.get("actions", [])
            if a.get("status") != "completed" and not a.get("auto_scheduled", False)
        ]
        if not remaining:
            return {"schedule": [], "notes": ["All actions are already completed or scheduled."]}

        try:
            ai_raw = json.loads(
                build_execution_schedule_with_ai(
                    plan,
                    request.timezone,
                    local_now.isoformat(timespec="seconds"),
                )
            )
            raw_schedule = ai_raw.get("schedule", []) if isinstance(ai_raw, dict) else []
            notes = ai_raw.get("notes", []) if isinstance(ai_raw, dict) else []
        except Exception as error:
            print("SCHEDULE AI FALLBACK:", repr(error))
            raw_schedule = _fallback_schedule(remaining, local_now)
            notes = ["AI scheduling fallback was used. Review the times before approving."]

        normalized = _normalize_schedule(plan, raw_schedule, local_now)
        return {"schedule": normalized, "notes": notes}

    except HTTPException:
        raise
    except Exception as error:
        print("SCHEDULE PREVIEW ERROR:", repr(error))
        raise HTTPException(status_code=500, detail=f"Could not build smart schedule: {str(error)}") from error


@app.post("/plans/{plan_id}/approve-schedule")
def approve_schedule(
    plan_id: str,
    request: ApproveScheduleRequest,
    authorization: str | None = Header(default=None),
):
    try:
        user = get_authenticated_user(authorization)
        tz = _get_timezone(request.timezone)
        now_utc = datetime.now(timezone.utc)
        plan = get_plan_by_id(user.id, plan_id)
        connection = get_google_connection(user.id)
        if not connection:
            raise HTTPException(
                status_code=400,
                detail="Connect Google Calendar before approving the smart schedule.",
            )

        action_by_id = {str(a["id"]): a for a in plan.get("actions", [])}
        created = []
        skipped = []

        for item in request.schedule:
            action = action_by_id.get(item.action_id)
            if not action:
                raise HTTPException(status_code=400, detail="Schedule contains an action that does not belong to this plan.")
            if action.get("status") == "completed" or action.get("auto_scheduled", False):
                skipped.append({"action_id": item.action_id, "title": action.get("title")})
                continue

            start_local = datetime.fromisoformat(item.scheduled_start)
            if start_local.tzinfo is None:
                start_local = start_local.replace(tzinfo=tz)
            else:
                start_local = start_local.astimezone(tz)
            start_utc = start_local.astimezone(timezone.utc)
            if start_utc <= now_utc + timedelta(minutes=2):
                raise HTTPException(status_code=400, detail=f"'{action.get('title')}' is scheduled too close to or before the current time. Generate the schedule again.")

            description = (
                "Scheduled by DoThis Smart Execution\n\n"
                f"Plan: {plan.get('goal', '')}\n"
                f"Reason: {action.get('reason', '')}"
            )
            event = create_calendar_event(
                refresh_token=connection["refresh_token"],
                title=action.get("title", "DoThis action"),
                start_datetime=start_local.replace(tzinfo=None).isoformat(timespec="seconds"),
                duration_minutes=item.duration_minutes,
                description=description,
                timezone=request.timezone,
            )

            reminder_time = start_utc - timedelta(minutes=item.reminder_minutes_before)
            if reminder_time <= now_utc:
                # The schedule may be close to the current time. Send a near-immediate
                # reminder, but keep it before the scheduled action.
                reminder_time = now_utc + timedelta(minutes=1)
                if reminder_time >= start_utc:
                    reminder_time = start_utc - timedelta(minutes=1)
            reminder = create_reminder(
                user.id,
                item.action_id,
                reminder_time.isoformat(),
            )

            updated_action = mark_action_auto_scheduled(
                user_id=user.id,
                action_id=item.action_id,
                scheduled_start=start_utc.isoformat(),
                duration_minutes=item.duration_minutes,
                calendar_event_id=event.get("id"),
                calendar_event_link=event.get("html_link"),
            )

            created.append(
                {
                    "action_id": item.action_id,
                    "title": action.get("title"),
                    "calendar_event": event,
                    "reminder": reminder,
                    "action": updated_action,
                }
            )

        return {
            "message": f"Scheduled {len(created)} action(s).",
            "created": created,
            "skipped": skipped,
        }

    except HTTPException:
        raise
    except Exception as error:
        print("APPROVE SCHEDULE ERROR:", repr(error))
        raise HTTPException(status_code=500, detail=f"Could not approve schedule: {str(error)}") from error


# ============================================================
# ACTION STATUS
# ============================================================

@app.patch("/actions/{action_id}/status")
def change_action_status(
    action_id: str,
    request: UpdateActionStatusRequest,
    authorization: str | None = Header(default=None),
):
    if request.status not in {"pending", "in_progress", "completed"}:
        raise HTTPException(status_code=400, detail="Invalid action status.")
    try:
        user = get_authenticated_user(authorization)
        return {"action": update_action_status(user.id, action_id, request.status)}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not update action: {str(error)}") from error


# ============================================================
# REMINDERS
# ============================================================

@app.post("/actions/{action_id}/reminders")
def add_reminder(
    action_id: str,
    request: CreateReminderRequest,
    authorization: str | None = Header(default=None),
):
    try:
        user = get_authenticated_user(authorization)
        return {"reminder": create_reminder(user.id, action_id, request.remind_at)}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not create reminder: {str(error)}") from error


@app.get("/actions/{action_id}/reminders")
def list_reminders(action_id: str, authorization: str | None = Header(default=None)):
    try:
        user = get_authenticated_user(authorization)
        return {"reminders": get_action_reminders(user.id, action_id)}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not load reminders: {str(error)}") from error


@app.delete("/reminders/{reminder_id}")
def remove_reminder(reminder_id: str, authorization: str | None = Header(default=None)):
    try:
        user = get_authenticated_user(authorization)
        return {"reminder": delete_reminder(user.id, reminder_id)}
    except HTTPException:
        raise
    except Exception as error:
        if str(error) == "Reminder not found.":
            raise HTTPException(status_code=404, detail="Reminder not found.") from error
        raise HTTPException(status_code=500, detail=f"Could not delete reminder: {str(error)}") from error


# ============================================================
# GOOGLE CALENDAR
# ============================================================

@app.get("/google/status")
def google_status(authorization: str | None = Header(default=None)):
    try:
        user = get_authenticated_user(authorization)
        return {"connected": get_google_connection(user.id) is not None}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not check Google connection: {str(error)}") from error


@app.get("/google/connect")
def google_connect(authorization: str | None = Header(default=None)):
    try:
        user = get_authenticated_user(authorization)
        code_verifier, code_challenge = generate_pkce()
        flow = create_google_flow(code_verifier=code_verifier)
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        oauth_requests[state] = {"user_id": user.id, "code_verifier": code_verifier}
        return {"authorization_url": authorization_url}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not start Google OAuth: {str(error)}") from error


@app.get("/google/callback")
def google_callback(code: str, state: str):
    try:
        request_data = oauth_requests.pop(state, None)
        if not request_data:
            raise HTTPException(status_code=400, detail="Google OAuth session expired or is invalid.")

        user_id = request_data["user_id"]
        flow = create_google_flow(code_verifier=request_data["code_verifier"])
        flow.fetch_token(code=code)
        credentials = flow.credentials
        refresh_token = credentials.refresh_token

        if not refresh_token:
            existing = get_google_connection(user_id)
            if existing:
                refresh_token = existing["refresh_token"]
        if not refresh_token:
            raise RuntimeError("Google did not return a refresh token.")

        save_google_connection(
            user_id=user_id,
            refresh_token=refresh_token,
            scopes=" ".join(credentials.scopes or []),
        )
        return RedirectResponse(url=f"{FRONTEND_URL}/plans?google=connected")

    except HTTPException:
        raise
    except Exception as error:
        print("GOOGLE CALLBACK ERROR:", repr(error))
        raise HTTPException(status_code=500, detail=f"Google OAuth failed: {str(error)}") from error


@app.delete("/google/disconnect")
def google_disconnect(authorization: str | None = Header(default=None)):
    try:
        user = get_authenticated_user(authorization)
        delete_google_connection(user.id)
        return {"connected": False, "message": "Google Calendar disconnected."}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not disconnect Google: {str(error)}") from error


@app.post("/actions/{action_id}/calendar")
def add_action_to_calendar(
    action_id: str,
    request: CreateCalendarEventRequest,
    authorization: str | None = Header(default=None),
):
    try:
        user = get_authenticated_user(authorization)
        connection = get_google_connection(user.id)
        if not connection:
            raise HTTPException(status_code=400, detail="Google Calendar is not connected.")

        action_data = get_action_for_user(user.id, action_id)
        action = action_data["action"]
        plan = action_data["plan"]
        event = create_calendar_event(
            refresh_token=connection["refresh_token"],
            title=action["title"],
            start_datetime=request.start_datetime,
            duration_minutes=request.duration_minutes,
            description=(
                f"DoThis action\n\nPlan: {plan.get('goal', '')}\nReason: {action.get('reason', '')}"
            ),
            timezone=request.timezone,
        )
        return {"message": "Calendar event created successfully.", "event": event}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not create calendar event: {str(error)}") from error
