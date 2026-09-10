import json
import os
import io
from pathlib import Path

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    UploadFile,
    File,
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from fastapi.responses import (
    RedirectResponse
)

from dotenv import load_dotenv

from pydantic import (
    BaseModel,
    Field,
)

from typing import (
    List,
    Optional,
)


from ai_engine import (
    analyze_with_ai
)

from validator import (
    validate_outcome
)


from database import (
    save_plan,
    get_user_from_token,
    get_user_plans,
    get_plan_by_id,
    update_action_status,

    create_reminder,
    get_action_reminders,
    delete_reminder,

    save_google_connection,
    get_google_connection,
    delete_google_connection,
     get_action_for_user,
)


from pypdf import PdfReader
from docx import Document
from PIL import Image

from google_calendar import (
    create_google_flow,
    generate_pkce,
    oauth_requests,
    create_calendar_event,
)


load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

app = FastAPI(
    title="DoThis API",
    description=(
        "Turn information into "
        "structured outcomes."
    ),
    version="1.2.0",
)


app.add_middleware(
    CORSMiddleware,

    allow_origins=list({
        FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }),

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# MODELS
# ============================================================

class ActionRequest(
    BaseModel
):
    text: str


class ActionItem(
    BaseModel
):
    id: int

    title: str

    type: str = "task"

    deadline: Optional[str] = None

    depends_on: List[int] = Field(
        default_factory=list
    )

    priority: str = "medium"

    confidence: float = 0.5

    status: str = "pending"

    needs_confirmation: bool = False

    reason: str = ""


class OutcomeResult(
    BaseModel
):
    goal: str

    summary: str = ""

    required_items: List[str] = Field(
        default_factory=list
    )

    actions: List[ActionItem] = Field(
        default_factory=list
    )


class SavePlanRequest(
    BaseModel
):
    original_text: str

    outcome: OutcomeResult


class UpdateActionStatusRequest(
    BaseModel
):
    status: str


class CreateReminderRequest(
    BaseModel
):
    remind_at: str

class CreateCalendarEventRequest(BaseModel):
    start_datetime: str
    duration_minutes: int = 60
    timezone: str = "Asia/Karachi"
# ============================================================
# AUTH HELPERS
# ============================================================

def extract_bearer_token(
    authorization: str | None
) -> str:

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail=(
                "Authentication required."
            )
        )


    if not authorization.startswith(
        "Bearer "
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid authentication header."
            )
        )


    return authorization.replace(
        "Bearer ",
        "",
        1
    )


def get_authenticated_user(
    authorization: str | None
):

    token = extract_bearer_token(
        authorization
    )


    user = get_user_from_token(
        token
    )


    return user


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def home():

    return {
        "app":
            "DoThis",

        "version":
            "1.2.0",

        "status":
            "running",
    }


@app.get("/health")
def health():

    return {
        "status":
            "healthy"
    }


# ============================================================
# AI ANALYSIS
# ============================================================

@app.post(
    "/analyze",
    response_model=OutcomeResult
)
def analyze(
    request: ActionRequest
):

    clean_text = (
        request.text.strip()
    )


    if not clean_text:

        raise HTTPException(
            status_code=400,
            detail=(
                "Please provide some "
                "information to analyze."
            )
        )


    if len(clean_text) > 15000:

        raise HTTPException(
            status_code=400,
            detail=(
                "Input is too long "
                "for the current MVP."
            )
        )


    try:

        ai_response = (
            analyze_with_ai(
                clean_text
            )
        )


        print(
            "\n--- RAW AI RESPONSE ---"
        )

        print(
            ai_response
        )

        print(
            "-----------------------\n"
        )


        data = json.loads(
            ai_response
        )


        validated_data = (
            validate_outcome(
                data,
                clean_text
            )
        )


        return OutcomeResult(
            **validated_data
        )


    except json.JSONDecodeError:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI returned invalid JSON. "
                "Please try again."
            )
        )


    except ValueError as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    except Exception as error:

        print(
            "AI ERROR:",
            repr(error)
        )


        raise HTTPException(
            status_code=500,
            detail=(
                f"AI analysis failed: "
                f"{str(error)}"
            )
        )


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
                "Image OCR is not available on this server yet. Install Tesseract OCR, "
                "then restart the backend. PDF, DOCX and text uploads already work."
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
def create_plan(
    request: SavePlanRequest,

    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        return save_plan(
            user_id=user.id,

            original_text=
                request.original_text,

            outcome=
                request.outcome.model_dump()
        )


    except HTTPException:
        raise


    except Exception as error:

        print(
            "DATABASE ERROR:",
            repr(error)
        )


        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not save plan: "
                f"{str(error)}"
            )
        )


@app.get("/plans")
def list_plans(
    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        return {
            "plans":
                get_user_plans(
                    user.id
                )
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load plans: "
                f"{str(error)}"
            )
        )


@app.get(
    "/plans/{plan_id}"
)
def read_plan(
    plan_id: str,

    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        return get_plan_by_id(
            user.id,
            plan_id
        )


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load plan: "
                f"{str(error)}"
            )
        )


# ============================================================
# ACTION STATUS
# ============================================================

@app.patch(
    "/actions/{action_id}/status"
)
def change_action_status(
    action_id: str,

    request:
        UpdateActionStatusRequest,

    authorization: str | None = Header(
        default=None
    )
):

    allowed_statuses = {
        "pending",
        "in_progress",
        "completed",
    }


    if (
        request.status
        not in allowed_statuses
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid action status."
            )
        )


    try:

        user = get_authenticated_user(
            authorization
        )


        action = (
            update_action_status(
                user_id=user.id,
                action_id=action_id,
                status=request.status
            )
        )


        return {
            "action":
                action
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not update action: "
                f"{str(error)}"
            )
        )


# ============================================================
# REMINDERS
# ============================================================

@app.post(
    "/actions/{action_id}/reminders"
)
def add_reminder(
    action_id: str,

    request:
        CreateReminderRequest,

    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        reminder = (
            create_reminder(
                user_id=user.id,

                action_id=
                    action_id,

                remind_at=
                    request.remind_at
            )
        )


        return {
            "reminder":
                reminder
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not create reminder: "
                f"{str(error)}"
            )
        )


@app.get(
    "/actions/{action_id}/reminders"
)
def list_reminders(
    action_id: str,

    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        return {
            "reminders":
                get_action_reminders(
                    user_id=user.id,
                    action_id=action_id
                )
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load reminders: "
                f"{str(error)}"
            )
        )


@app.delete(
    "/reminders/{reminder_id}"
)
def remove_reminder(
    reminder_id: str,

    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        return {
            "reminder":
                delete_reminder(
                    user_id=user.id,
                    reminder_id=reminder_id
                )
        }


    except HTTPException:
        raise


    except Exception as error:

     if str(error) == "Reminder not found.":
        raise HTTPException(
            status_code=404,
            detail="Reminder not found."
        )

    raise HTTPException(
        status_code=500,
        detail=f"Could not delete reminder: {str(error)}"
    )


# ============================================================
# GOOGLE CALENDAR STATUS
# ============================================================

@app.get(
    "/google/status"
)
def google_status(
    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        connection = (
            get_google_connection(
                user.id
            )
        )


        return {
            "connected":
                connection is not None
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not check Google "
                f"connection: {str(error)}"
            )
        )


# ============================================================
# GOOGLE CONNECT
# ============================================================

@app.get(
    "/google/connect"
)
def google_connect(
    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        (
            code_verifier,
            code_challenge
        ) = generate_pkce()


        flow = create_google_flow(
            code_verifier=
                code_verifier
        )


        (
            authorization_url,
            state
        ) = flow.authorization_url(

            access_type="offline",
            
            prompt="consent",

            code_challenge=
                code_challenge,

            code_challenge_method=
                "S256",
        )


        oauth_requests[state] = {
            "user_id":
                user.id,

            "code_verifier":
                code_verifier,
        }


        return {
            "authorization_url":
                authorization_url
        }


    except HTTPException:
        raise


    except Exception as error:

        print(
            "GOOGLE CONNECT ERROR:",
            repr(error)
        )


        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not start Google OAuth: "
                f"{str(error)}"
            )
        )


# ============================================================
# GOOGLE CALLBACK
# ============================================================

@app.get(
    "/google/callback"
)
def google_callback(
    code: str,
    state: str
):

    try:

        request_data = (
            oauth_requests.pop(
                state,
                None
            )
        )


        if not request_data:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Google OAuth session "
                    "expired or is invalid."
                )
            )


        user_id = (
            request_data[
                "user_id"
            ]
        )


        code_verifier = (
            request_data[
                "code_verifier"
            ]
        )


        flow = create_google_flow(
            code_verifier=
                code_verifier
        )


        flow.fetch_token(
            code=code
        )


        credentials = (
            flow.credentials
        )


        refresh_token = (
            credentials.refresh_token
        )


        # Sometimes Google may not return another
        # refresh token if the user previously granted
        # access. Preserve an existing token if present.

        if not refresh_token:

            existing = (
                get_google_connection(
                    user_id
                )
            )

            if existing:

                refresh_token = (
                    existing[
                        "refresh_token"
                    ]
                )


        if not refresh_token:

            raise RuntimeError(
                "Google did not return "
                "a refresh token."
            )


        scopes = " ".join(
            credentials.scopes
            or []
        )


        save_google_connection(
            user_id=user_id,

            refresh_token=
                refresh_token,

            scopes=scopes
        )


        print(
            "Google Calendar connected "
            "for DoThis user:",
            user_id
        )


        return RedirectResponse(
            url=f"{FRONTEND_URL}/plans?google=connected"
        )


    except HTTPException:
        raise


    except Exception as error:

        print(
            "GOOGLE CALLBACK ERROR:",
            repr(error)
        )


        raise HTTPException(
            status_code=500,
            detail=(
                f"Google OAuth failed: "
                f"{str(error)}"
            )
        )


# ============================================================
# GOOGLE DISCONNECT
# ============================================================

@app.delete(
    "/google/disconnect"
)
def google_disconnect(
    authorization: str | None = Header(
        default=None
    )
):

    try:

        user = get_authenticated_user(
            authorization
        )


        delete_google_connection(
            user.id
        )


        return {
            "connected":
                False,

            "message":
                "Google Calendar disconnected."
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not disconnect Google: "
                f"{str(error)}"
            )
        )
@app.post(
    "/actions/{action_id}/calendar"
)
def add_action_to_calendar(
    action_id: str,
    request: CreateCalendarEventRequest,
    authorization: str | None = Header(
        default=None
    )
):
    try:
        user = get_authenticated_user(
            authorization
        )

        connection = get_google_connection(
            user.id
        )

        if not connection:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Google Calendar is not connected."
                )
            )

        action_data = get_action_for_user(
            user_id=user.id,
            action_id=action_id
        )

        action = action_data["action"]
        plan = action_data["plan"]

        description = (
            f"DoThis action\n\n"
            f"Plan: {plan.get('goal', '')}\n"
            f"Reason: {action.get('reason', '')}"
        )

        event = create_calendar_event(
            refresh_token=
                connection["refresh_token"],

            title=
                action["title"],

            start_datetime=
                request.start_datetime,

            duration_minutes=
                request.duration_minutes,

            description=
                description,

            timezone=
                request.timezone,
        )

        return {
            "message":
                "Calendar event created successfully.",

            "event":
                event
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "CALENDAR EVENT ERROR:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not create calendar event: "
                f"{str(error)}"
            )
        )