import os

from dotenv import load_dotenv
from huggingface_hub import InferenceClient


load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise RuntimeError(
        "HF_TOKEN was not found in the .env file."
    )


MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"


client = InferenceClient(
    provider="featherless-ai",
    token=HF_TOKEN,
)


def analyze_with_ai(text: str) -> str:

    system_prompt = """
You are the reasoning engine for DoThis.

DoThis converts unstructured information into a safe,
structured and practical outcome plan.

Determine:

1. The user's main goal.
2. Required items.
3. Actions needed.
4. Explicit deadlines.
5. Genuine dependencies.
6. Priority of each action.
7. Confidence that the action is supported by the input.
8. Whether user confirmation should be required.

Return ONLY valid JSON.

Use EXACTLY this structure:

{
  "goal": "main outcome",
  "summary": "short useful summary",
  "required_items": [
    "required item"
  ],
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

- Never invent dates.
- Never invent a year.
- Never invent requirements.
- Only use information supported by the user's input.
- Preserve explicit deadlines.
- Break complicated outcomes into practical actions.

DEPENDENCIES:
- Add a dependency only when one action genuinely
  requires another action to happen first.
- Do not make related actions dependent automatically.

PRIORITY:
- high = important deadline, submission, required event
  or something that can block the outcome.
- medium = important preparation.
- low = optional or non-urgent supporting action.

CONFIDENCE:
- Number between 0.0 and 1.0.
- 1.0 means explicitly supported by the user's input.
- Lower confidence when interpretation is required.
- Do not pretend to be certain when information is unclear.

CONFIRMATION:
Set needs_confirmation=true for actions that would later
cause an external change or communication, such as:
- sending something
- submitting something
- booking something
- adding/changing an external event
- contacting another person

Preparation or informational actions normally use false.

ACTION TYPES:
task
event
preparation
submission
reminder

If no deadline exists, return null.

Return JSON only.
No markdown.
No code fences.
"""

    response = client.chat_completion(
        model=MODEL_ID,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        max_tokens=1100,
        temperature=0.1,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "AI returned an empty response."
        )

    return content.strip()