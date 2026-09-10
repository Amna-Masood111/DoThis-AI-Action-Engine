import os
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
import secrets
import hashlib
import base64
from datetime import datetime, timedelta

from dotenv import load_dotenv

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


load_dotenv()


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


if not GOOGLE_CLIENT_ID:
    raise RuntimeError("GOOGLE_CLIENT_ID missing from .env")

if not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("GOOGLE_CLIENT_SECRET missing from .env")

if not GOOGLE_REDIRECT_URI:
    raise RuntimeError("GOOGLE_REDIRECT_URI missing from .env")


SCOPES = [
    "https://www.googleapis.com/auth/calendar.events"
]


oauth_requests = {}


def create_google_flow(
    code_verifier: str | None = None
):
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri":
                "https://accounts.google.com/o/oauth2/auth",
            "token_uri":
                "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                GOOGLE_REDIRECT_URI
            ],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        code_verifier=code_verifier,
        autogenerate_code_verifier=False,
    )

    flow.redirect_uri = GOOGLE_REDIRECT_URI

    return flow


def generate_pkce():
    code_verifier = secrets.token_urlsafe(64)

    digest = hashlib.sha256(
        code_verifier.encode("utf-8")
    ).digest()

    code_challenge = (
        base64.urlsafe_b64encode(digest)
        .decode("utf-8")
        .rstrip("=")
    )

    return code_verifier, code_challenge


def create_google_credentials(
    refresh_token: str
):
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=
            "https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )


def create_calendar_service(
    refresh_token: str
):
    credentials = create_google_credentials(
        refresh_token
    )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def create_calendar_event(
    refresh_token: str,
    title: str,
    start_datetime: str,
    duration_minutes: int = 60,
    description: str = "",
    timezone: str = "Asia/Karachi",
):

    service = create_calendar_service(
        refresh_token
    )

    start_dt = datetime.fromisoformat(
        start_datetime
    )

    end_dt = start_dt + timedelta(
        minutes=duration_minutes
    )

    event_body = {
        "summary": title,

        "description": description,

        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": timezone,
        },

        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": timezone,
        },
    }

    event = (
        service.events()
        .insert(
            calendarId="primary",
            body=event_body,
        )
        .execute()
    )

    return {
        "id": event.get("id"),
        "html_link": event.get("htmlLink"),
        "status": event.get("status"),
    }