# DoThis – AI Action Engine

> **DoThis turns unstructured schedules, deadlines, notes, and documents into actionable plans, then helps users execute them with progress tracking, automated email reminders, and Google Calendar integration.**
> 

---

## What is DoThis?

**DoThis** is an AI-powered execution platform designed to bridge the gap between text generation and real-world task completion. Instead of acting like a traditional chatbot that only produces conversational text, DoThis parses raw, scattered inputs—such as emails, briefs, hand-written notes, images, or PDFs—and transforms them into structured execution workflows.

The application extracts critical goals, actionable steps, explicit deadlines, priorities, and dependencies. It then validates the output, stores it under authenticated user accounts, creates realistic schedules, and executes external actions—such as creating Google Calendar events and dispatching automated Gmail notifications via n8n—all while requiring explicit human approval before making external changes.

---

## Pipeline & Workflow

DoThis follows a human-in-the-loop Agentic AI execution pipeline:

```text
[ Unstructured Input / File Upload / Image OCR ]
                       │
                       ▼
        [ FastAPI + AI Validation Layer ]
                       │
                       ▼
    [ Qwen 2.5 7B AI Plan & Schedule Engine ]
                       │
                       ▼
         [ Supabase Storage & Tracking ]
                       │
                       ▼
     [ Smart Schedule & Human Approval Step ]
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
[ Google Calendar API ]    [ n8n Automation Engine ]
                                      │
                                      ▼
                             [ Gmail Notifications ]

```

### The Execution Loop

1. **Understand & Extract:** Upload documents/images or paste raw text. Tesseract OCR parses images, while text extractors parse PDF, DOCX, TXT, CSV, and Markdown files.


2. **Plan Generation:** The backend sends the text to the `Qwen/Qwen2.5-7B-Instruct` model, which converts it into structured JSON containing goals, requirements, task priorities, and dependencies.


3. **Validate & Store:** Responses pass through a validation layer to normalize fields before being saved per user in Supabase.


4. **Smart Schedule:** AI calculates realistic time slots, task durations, and non-overlapping schedules based on local time and dependencies.


5. **Human Approval:** The user reviews and explicitly approves the generated schedule before any external system is modified.


6. **Execute & Remind:** Approved tasks sync directly with Google Calendar via OAuth. n8n checks for due reminders and dispatches email notifications via Gmail.



---

## Tech Stack & Architecture

* **Frontend:** Next.js, React, TypeScript, Tailwind CSS (Hosted on Vercel)


* **Backend:** FastAPI, Python, Uvicorn (Hosted on Azure/Docker)


* **Database & Authentication:** Supabase (User auth, RLS privacy, relational storage)


* **AI Engine:** `Qwen/Qwen2.5-7B-Instruct` via Hugging Face / Featherless AI


* **OCR Module:** Tesseract OCR for image text extraction


* **Automation Layer:** n8n workflow engine for scheduled reminder processing


* **Integrations:** Google Calendar API (OAuth PKCE) & Gmail API



---

## Project Structure

```text
dothis/
├── backend/                  # FastAPI backend server
│   ├── app/                  # Core application modules
│   │   ├── api/              # API endpoints (plans, schedule, auth, uploads)
│   │   ├── core/             # AI prompts, validators, and config setup
│   │   ├── services/         # Integrations (Qwen LLM, Tesseract OCR, Google APIs)
│   │   └── models/           # Pydantic schemas and database models
│   ├── .env.example          # Backend environment variables template
│   ├── main.py               # FastAPI entry point
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Next.js web client
│   ├── src/
│   │   ├── app/              # Next.js App Router pages (Dashboard, Plans, Auth)
│   │   ├── components/       # UI components and action cards
│   │   └── lib/              # Supabase & API client configurations
│   ├── .env.local.example    # Frontend environment variables template
│   └── package.json          # Node dependencies
└── README.md                 # Project documentation

```

---

## How to Use (Local Setup)

### Prerequisites

* **Python 3.10+**
* **Node.js 18+**
* **Tesseract OCR** installed on system PATH (for image parsing)



### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Copy environment template
cp .env.example .env
# Fill in your private keys (Supabase, Hugging Face/Featherless AI, Google OAuth)

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload

```

The backend API will run on `http://localhost:8000`.

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Copy environment template
cp .env.local.example .env.local
# Fill in public Supabase keys (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY)

# Install dependencies
npm install

# Start development server
npm run dev

```

Open `http://localhost:3000` in your browser.

> **Security Note:** Never commit `.env`, `.env.local`, `.venv`, or sensitive credentials (service-role keys, OAuth secrets) to GitHub.
> 
> 

---

## Key API Endpoints

* **`POST /api/v1/plans/generate`** — Processes raw input/files, executes Qwen AI extraction, and passes data through the validation layer.


* **`GET /api/v1/plans`** — Fetches saved outcomes and action plans for the authenticated user.


* **`PATCH /api/v1/actions/{id}`** — Updates specific task status (Pending, In Progress, Completed).


* **`POST /api/v1/schedule/generate`** — Computes a Smart Schedule based on open tasks, deadlines, and dependencies.


* **`POST /api/v1/calendar/sync`** — Syncs user-approved schedule items into Google Calendar.


* **`POST /api/v1/reminders`** — Registers reminder instances consumed by n8n automated cron jobs.



---

## Built At

Built for the **Generative & Agentic AI Hackathon (September 2026)**.
