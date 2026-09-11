import json
import os

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN was not found in the .env file.")

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

client = InferenceClient(
    provider="featherless-ai",
    token=HF_TOKEN,
)


def _chat_json(system_prompt: str, user_content: str, max_tokens: int = 1400) -> str:
    response = client.chat_completion(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("AI returned an empty response.")
    return content.strip()


def analyze_with_ai(text: str) -> str:
    system_prompt = """
You are the reasoning engine for DoThis.
DoThis converts unstructured information into a safe, structured and practical outcome plan.

Determine:
1. The user's main goal.
2. Required items.
3. Actions needed.
4. Explicit deadlines.
5. Genuine dependencies.
6. Priority of each action.
7. Confidence that the action is supported by the input.
8. Whether user confirmation should be required.

Return ONLY valid JSON using EXACTLY this structure:
{
  "goal": "main outcome",
  "summary": "short useful summary",
  "required_items": ["required item"],
  "actions": [
    {
      "id": 1,
      "title": "action title",
      "type": "task",
      "deadline": null,
      "depends_on": [],
      "priority": "medium",
      "confidence": 0.95,
      "needs_confirmation": false,
      "reason": "why this action is needed"
    }
  ]
}

RULES:
- Never invent factual deadlines, years, or requirements.
- Preserve explicit deadlines from the user's input.
- Break complicated outcomes into practical actions.
- Add a dependency only when one action genuinely requires another first.
- high priority = deadline/submission/blocker; medium = preparation; low = optional support.
- confidence must be 0.0 to 1.0.
- needs_confirmation=true for external changes such as sending, submitting, booking, contacting, or changing an external event.
- Action types: task, event, preparation, submission, reminder.
- If no factual deadline exists, return null.
- Return JSON only. No markdown or code fences.
"""
    return _chat_json(system_prompt, text, max_tokens=1100)


def build_execution_schedule_with_ai(plan: dict, timezone: str, local_now_iso: str) -> str:
    """Create a suggested execution schedule. These are recommendations, not factual deadlines."""
    compact_actions = [
        {
            "action_number": a.get("action_number"),
            "title": a.get("title"),
            "type": a.get("type"),
            "deadline": a.get("deadline"),
            "priority": a.get("priority"),
            "depends_on": a.get("depends_on", []),
            "reason": a.get("reason", ""),
            "status": a.get("status", "pending"),
            "auto_scheduled": bool(a.get("auto_scheduled", False)),
        }
        for a in plan.get("actions", [])
        if a.get("status") != "completed" and not a.get("auto_scheduled", False)
    ]

    payload = {
        "current_local_datetime": local_now_iso,
        "timezone": timezone,
        "goal": plan.get("goal", ""),
        "summary": plan.get("summary", ""),
        "description": plan.get("description", ""),
        "original_input": plan.get("original_text", ""),
        "actions": compact_actions,
    }

    system_prompt = """
You are the scheduling engine for DoThis. Convert an already-approved action plan into a PRACTICAL SUGGESTED execution schedule.

The dates you create are scheduling recommendations, not factual deadlines. Factual deadlines already appear in the action data and must be respected.

Return ONLY valid JSON with EXACTLY this shape:
{
  "schedule": [
    {
      "action_number": 1,
      "scheduled_start": "YYYY-MM-DDTHH:MM:SS",
      "duration_minutes": 60,
      "reminder_minutes_before": 60,
      "rationale": "short explanation"
    }
  ],
  "notes": ["optional concise scheduling note"]
}

RULES:
- Schedule every unscheduled, incomplete action exactly once.
- scheduled_start is LOCAL time in the supplied timezone and must NOT contain Z or a UTC offset.
- Never schedule anything in the past.
- Respect action dependencies: prerequisites must be scheduled before dependent actions.
- Respect explicit deadlines as hard upper bounds whenever they can reasonably be interpreted from the supplied plan/input.
- If a deadline is relative (for example "Friday" or "tomorrow"), interpret it using current_local_datetime.
- If an action has no explicit deadline, create a reasonable suggested time based on priority, dependencies, and the overall goal. Prefer the next 7 days rather than inventing a distant date.
- Prefer working hours 09:00-18:00 unless the source clearly implies another time.
- Avoid overlapping actions.
- duration_minutes must be one of 30, 45, 60, 90, 120.
- reminder_minutes_before must be one of 30, 60, 180, 720, 1440. Use more lead time for high-priority/deadline-sensitive actions.
- Do not include completed or already auto-scheduled actions.
- Return JSON only. No markdown or code fences.
"""

    return _chat_json(system_prompt, json.dumps(payload, ensure_ascii=False), max_tokens=1800)
