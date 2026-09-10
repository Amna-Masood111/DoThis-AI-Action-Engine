import os
import sys
import requests

from dotenv import load_dotenv


load_dotenv()


N8N_BASE_URL = os.getenv(
    "N8N_BASE_URL",
    ""
).rstrip("/")

N8N_API_KEY = os.getenv(
    "N8N_API_KEY"
)


if not N8N_BASE_URL:
    raise RuntimeError(
        "N8N_BASE_URL missing from .env"
    )


if not N8N_API_KEY:
    raise RuntimeError(
        "N8N_API_KEY missing from .env"
    )


HEADERS = {
    "X-N8N-API-KEY": N8N_API_KEY,
    "Content-Type": "application/json",
}


# ----------------------------------------------------------
# FIND EXISTING GMAIL CREDENTIAL
# ----------------------------------------------------------

def find_gmail_credential():

    response = requests.get(
        f"{N8N_BASE_URL}/api/v1/workflows",
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    workflows = response.json().get(
        "data",
        []
    )


    for workflow in workflows:

        workflow_id = workflow["id"]

        detail = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=HEADERS,
            timeout=30,
        )

        detail.raise_for_status()

        data = detail.json()


        for node in data.get(
            "nodes",
            []
        ):

            if (
                node.get("type")
                == "n8n-nodes-base.gmail"
            ):

                credentials = node.get(
                    "credentials",
                    {}
                )

                gmail = credentials.get(
                    "gmailOAuth2"
                )

                if gmail:

                    print(
                        "Found Gmail credential:",
                        gmail.get("name")
                    )

                    return gmail


    return None


gmail_credential = (
    find_gmail_credential()
)


if not gmail_credential:

    print(
        "\nCould not find your Gmail credential."
    )

    print(
        "Save the Gmail test workflow in n8n "
        "with the connected Gmail account, "
        "then run this script again."
    )

    sys.exit(1)


# ----------------------------------------------------------
# WORKFLOW
# ----------------------------------------------------------

workflow = {

    "name":
        "DoThis - Automatic Reminders",

    "nodes": [

        # --------------------------------------------------
        # EVERY MINUTE
        # --------------------------------------------------

        {
            "parameters": {
                "rule": {
                    "interval": [
                        {
                            "field": "minutes",
                            "minutesInterval": 1
                        }
                    ]
                }
            },

            "id": "schedule-trigger",

            "name": "Check Every Minute",

            "type":
                "n8n-nodes-base.scheduleTrigger",

            "typeVersion": 1.2,

            "position": [
                0,
                0
            ],
        },


        # --------------------------------------------------
        # GET DUE REMINDERS
        # --------------------------------------------------

        {
            "parameters": {

                "url":
                    "={{$env.SUPABASE_URL + "
                    "'/rest/v1/reminders'"
                    "}}",

                "sendQuery": True,

                "queryParameters": {
                    "parameters": [

                        {
                            "name": "select",
                            "value":
                                "id,user_id,"
                                "action_id,"
                                "remind_at,status,"
                                "actions(title)"
                        },

                        {
                            "name": "status",
                            "value": "eq.pending"
                        },

                        {
                            "name": "remind_at",
                            "value":
                                "={{'lte.' + $now.toISO()}}"
                        }
                    ]
                },

                "sendHeaders": True,

                "headerParameters": {
                    "parameters": [

                        {
                            "name": "apikey",
                            "value":
                                "={{$env.SUPABASE_SERVICE_KEY}}"
                        },

                        {
                            "name": "Authorization",
                            "value":
                                "={{'Bearer ' + "
                                "$env.SUPABASE_SERVICE_KEY}}"
                        }
                    ]
                },

                "options": {}
            },

            "id": "get-reminders",

            "name": "Get Due Reminders",

            "type":
                "n8n-nodes-base.httpRequest",

            "typeVersion": 4.2,

            "position": [
                260,
                0
            ],
        },


        # --------------------------------------------------
        # GET USER FROM SUPABASE AUTH
        # --------------------------------------------------

        {
            "parameters": {

                "url":
                    "={{$env.SUPABASE_URL + "
                    "'/auth/v1/admin/users/' + "
                    "$json.user_id}}",

                "sendHeaders": True,

                "headerParameters": {
                    "parameters": [

                        {
                            "name": "apikey",
                            "value":
                                "={{$env.SUPABASE_SERVICE_KEY}}"
                        },

                        {
                            "name": "Authorization",
                            "value":
                                "={{'Bearer ' + "
                                "$env.SUPABASE_SERVICE_KEY}}"
                        }
                    ]
                },

                "options": {}
            },

            "id": "get-user",

            "name": "Get User Email",

            "type":
                "n8n-nodes-base.httpRequest",

            "typeVersion": 4.2,

            "position": [
                520,
                0
            ],
        },


        # --------------------------------------------------
        # SEND EMAIL
        # --------------------------------------------------

        {
            "parameters": {

                "sendTo":
                    "={{$json.email}}",

                "subject":
                    "=DoThis Reminder: "
                    "{{ $('Get Due Reminders').item.json.actions.title }}",

                "message":
                    "=<h2>DoThis Reminder</h2>"
                    "<p>This task is due or needs your attention:</p>"
                    "<p><strong>"
                    "{{ $('Get Due Reminders').item.json.actions.title }}"
                    "</strong></p>"
                    "<p>Open DoThis to review your action plan.</p>",

                "options": {
                    "appendAttribution":
                        False
                }
            },

            "id": "send-gmail",

            "name": "Send Reminder Email",

            "type":
                "n8n-nodes-base.gmail",

            "typeVersion": 2.1,

            "position": [
                780,
                0
            ],

            "credentials": {
                "gmailOAuth2":
                    gmail_credential
            },
        },


        # --------------------------------------------------
        # MARK REMINDER SENT
        # --------------------------------------------------

        {
            "parameters": {

                "method": "PATCH",

                "url":
                    "={{$env.SUPABASE_URL + "
                    "'/rest/v1/reminders?id=eq.' + "
                    "$('Get Due Reminders').item.json.id}}",

                "sendHeaders": True,

                "headerParameters": {
                    "parameters": [

                        {
                            "name": "apikey",
                            "value":
                                "={{$env.SUPABASE_SERVICE_KEY}}"
                        },

                        {
                            "name": "Authorization",
                            "value":
                                "={{'Bearer ' + "
                                "$env.SUPABASE_SERVICE_KEY}}"
                        },

                        {
                            "name": "Content-Type",
                            "value":
                                "application/json"
                        },

                        {
                            "name": "Prefer",
                            "value":
                                "return=representation"
                        }
                    ]
                },

                "sendBody": True,

                "contentType":
                    "raw",

                "rawContentType":
                    "application/json",

                "body":
                    '{"status":"sent"}',

                "options": {}
            },

            "id": "mark-sent",

            "name": "Mark Reminder Sent",

            "type":
                "n8n-nodes-base.httpRequest",

            "typeVersion": 4.2,

            "position": [
                1040,
                0
            ],
        },
    ],


    "connections": {

        "Check Every Minute": {
            "main": [
                [
                    {
                        "node":
                            "Get Due Reminders",

                        "type":
                            "main",

                        "index":
                            0
                    }
                ]
            ]
        },


        "Get Due Reminders": {
            "main": [
                [
                    {
                        "node":
                            "Get User Email",

                        "type":
                            "main",

                        "index":
                            0
                    }
                ]
            ]
        },


        "Get User Email": {
            "main": [
                [
                    {
                        "node":
                            "Send Reminder Email",

                        "type":
                            "main",

                        "index":
                            0
                    }
                ]
            ]
        },


        "Send Reminder Email": {
            "main": [
                [
                    {
                        "node":
                            "Mark Reminder Sent",

                        "type":
                            "main",

                        "index":
                            0
                    }
                ]
            ]
        },
    },


    "settings": {
        "executionOrder":
            "v1"
    },
}


# ----------------------------------------------------------
# CREATE WORKFLOW
# ----------------------------------------------------------

print(
    "\nCreating DoThis reminder workflow..."
)


response = requests.post(
    f"{N8N_BASE_URL}/api/v1/workflows",
    headers=HEADERS,
    json=workflow,
    timeout=30,
)


if not response.ok:

    print(
        "Creation failed:"
    )

    print(
        response.status_code
    )

    print(
        response.text
    )

    sys.exit(1)


created = response.json()

workflow_id = created["id"]


print(
    "Workflow created."
)

print(
    "Workflow ID:",
    workflow_id
)


# ----------------------------------------------------------
# ACTIVATE
# ----------------------------------------------------------

activate = requests.post(
    (
        f"{N8N_BASE_URL}"
        f"/api/v1/workflows/"
        f"{workflow_id}/activate"
    ),
    headers=HEADERS,
    timeout=30,
)


if activate.ok:

    print(
        "\nSUCCESS!"
    )

    print(
        "DoThis automatic reminders "
        "workflow is ACTIVE."
    )

else:

    print(
        "\nWorkflow created, but automatic "
        "activation failed."
    )

    print(
        "Open n8n and activate it manually."
    )

    print(
        activate.text
    )