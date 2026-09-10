import re

from datetime import datetime
from typing import Any, Dict, List


VALID_TYPES = {
    "task",
    "event",
    "preparation",
    "submission",
    "reminder",
}

VALID_PRIORITIES = {
    "low",
    "medium",
    "high",
}


def extract_explicit_years(text: str) -> set[str]:

    return set(
        re.findall(
            r"\b(20\d{2})\b",
            text
        )
    )


def normalize_deadline(
    deadline: str | None,
    original_text: str
) -> str | None:

    if not deadline:
        return None

    deadline = str(deadline).strip()

    user_years = extract_explicit_years(
        original_text
    )

    ai_year = re.search(
        r"\b(20\d{2})\b",
        deadline
    )

    if ai_year:

        year = ai_year.group(1)

        if year not in user_years:

            iso_match = re.fullmatch(
                r"(20\d{2})-(\d{2})-(\d{2})",
                deadline
            )

            if iso_match:

                month = int(
                    iso_match.group(2)
                )

                day = int(
                    iso_match.group(3)
                )

                try:

                    temp_date = datetime(
                        2000,
                        month,
                        day
                    )

                    return (
                        temp_date
                        .strftime("%B %d")
                        .replace(" 0", " ")
                    )

                except ValueError:
                    return None

            deadline = re.sub(
                r"\b20\d{2}\b[-/,\s]*",
                "",
                deadline
            ).strip()

    return deadline or None


def clean_required_items(
    items: List[Any]
) -> List[str]:

    result = []
    seen = set()

    for item in items:

        item = str(item).strip()

        if not item:
            continue

        normalized = item.lower()

        if normalized not in seen:

            seen.add(normalized)
            result.append(item)

    return result


def normalize_confidence(
    value: Any
) -> float:

    try:
        confidence = float(value)

    except (TypeError, ValueError):
        return 0.5

    return round(
        max(
            0.0,
            min(1.0, confidence)
        ),
        2
    )


def normalize_priority(
    value: Any
) -> str:

    value = str(
        value or "medium"
    ).lower().strip()

    if value not in VALID_PRIORITIES:
        return "medium"

    return value


def normalize_type(
    value: Any
) -> str:

    value = str(
        value or "task"
    ).lower().strip()

    if value not in VALID_TYPES:
        return "task"

    return value


def normalize_actions(
    actions: List[Dict[str, Any]],
    original_text: str
) -> List[Dict[str, Any]]:

    cleaned = []

    old_to_new = {}

    for new_id, action in enumerate(
        actions,
        start=1
    ):

        if not isinstance(action, dict):
            continue

        old_id = action.get("id")

        if isinstance(old_id, int):
            old_to_new[old_id] = new_id

        cleaned.append({
            "id": new_id,

            "title": str(
                action.get(
                    "title",
                    "Unnamed action"
                )
            ).strip(),

            "type": normalize_type(
                action.get("type")
            ),

            "deadline":
                normalize_deadline(
                    action.get("deadline"),
                    original_text
                ),

            "priority":
                normalize_priority(
                    action.get("priority")
                ),

            "confidence":
                normalize_confidence(
                    action.get("confidence")
                ),

            "status": "pending",

            "needs_confirmation": bool(
                action.get(
                    "needs_confirmation",
                    False
                )
            ),

            "reason": str(
                action.get(
                    "reason",
                    ""
                )
            ).strip(),

            "_dependencies":
                action.get(
                    "depends_on",
                    []
                ),
        })

    valid_ids = set(
        range(
            1,
            len(cleaned) + 1
        )
    )

    for action in cleaned:

        raw_dependencies = action.pop(
            "_dependencies",
            []
        )

        if not isinstance(
            raw_dependencies,
            list
        ):
            raw_dependencies = []

        dependencies = []

        for dependency in raw_dependencies:

            if dependency in old_to_new:
                dependency = (
                    old_to_new[dependency]
                )

            if (
                isinstance(dependency, int)
                and dependency in valid_ids
                and dependency != action["id"]
                and dependency not in dependencies
            ):
                dependencies.append(
                    dependency
                )

        action["depends_on"] = dependencies

    return cleaned


def validate_outcome(
    data: Dict[str, Any],
    original_text: str
) -> Dict[str, Any]:

    if not isinstance(data, dict):

        raise ValueError(
            "AI response must be a JSON object."
        )

    required_items = data.get(
        "required_items",
        []
    )

    actions = data.get(
        "actions",
        []
    )

    if not isinstance(
        required_items,
        list
    ):
        required_items = []

    if not isinstance(
        actions,
        list
    ):
        actions = []

    return {

        "goal": str(
            data.get(
                "goal",
                "Complete the requested outcome"
            )
        ).strip(),

        "summary": str(
            data.get(
                "summary",
                ""
            )
        ).strip(),

        "required_items":
            clean_required_items(
                required_items
            ),

        "actions":
            normalize_actions(
                actions,
                original_text
            ),
    }