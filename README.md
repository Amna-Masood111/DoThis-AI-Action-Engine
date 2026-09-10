# DoThis MVP

DoThis turns unstructured schedules, deadlines, notes and documents into actionable plans, then helps users execute them with progress tracking, automated email reminders and Google Calendar.

## Local start

### Backend
1. Copy `backend/.env.example` to `backend/.env` and fill your private values.
2. Create a virtual environment: `python -m venv .venv`
3. Activate it and run `pip install -r requirements.txt`.
4. For screenshot/image OCR, install Tesseract OCR on the backend machine and ensure `tesseract` is on PATH.
5. Run: `uvicorn main:app --reload`

### Frontend
1. Copy `frontend/.env.local.example` to `frontend/.env.local` and fill the public Supabase values.
2. Run `npm install`.
3. Run `npm run dev`.
4. Open `http://localhost:3000`.

## Secrets / GitHub
Never commit `.env`, `.env.local`, `.venv`, `node_modules`, PEM keys, Supabase service-role keys, Google client secrets, Hugging Face tokens, or n8n API keys. The root `.gitignore` excludes them. Commit only the `.env.example` templates.

`NEXT_PUBLIC_*` values are intentionally browser-visible; use only Supabase's publishable/anon key there, never the service-role key.

## Current core flow
Input or upload → AI action plan → save per user → track actions → create reminders → n8n/Gmail notification → Google Calendar event.
