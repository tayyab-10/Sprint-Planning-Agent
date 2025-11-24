from app.models.task import Task
from typing import Any

# ------------------------------------------------------
# CONFIG CONSTANTS for Scoring
# ------------------------------------------------------

# Weights for scoring calculation
PRIORITY_WEIGHTS = {
    "Critical": 4.0,
    "High": 3.0,
    "Medium": 2.0,
    "Low": 1.0,
    "Trivial": 0.5,
}

# Value based on task type (e.g., core features over minor fixes)
TYPE_VALUE = {
    "Feature": 1.5,
    "Bug": 1.2,
    "Refactor": 1.0,
    "Documentation": 0.8,
    "Other": 1.0,
}

# ------------------------------------------------------
# Core Scoring Function
# ------------------------------------------------------

def compute_task_score(task: Any) -> float:
    """
    Calculates a composite prioritization score for a task.
    Accepts either a Pydantic Task-like object or a plain dict.
    Score = (Priority Weight * Type Value * Urgency Boost) / Effort Factor
    Returns a scaled score (0..~40) depending on inputs.
    """

    # Support dicts and objects
    if isinstance(task, dict):
        priority_str = task.get('priority', 'Medium')
        task_type = task.get('type', 'Other')
        raw_effort = task.get('estimatedHours', 8.0)
        title = (task.get('title') or '').lower()
    else:
        priority_str = getattr(task, 'priority', 'Medium')
        task_type = getattr(task, 'type', 'Other')
        raw_effort = getattr(task, 'estimatedHours', 8.0)
        title = (getattr(task, 'title', '') or '').lower()

    # 1. Effort Factor (Use a minimum of 1.0 to avoid division-by-zero)
    try:
        effort_factor = max(float(raw_effort) if raw_effort is not None else 1.0, 1.0)
    except Exception:
        effort_factor = 8.0

    # 2. Priority Weight
    priority_weight = PRIORITY_WEIGHTS.get(priority_str, 1.0)

    # 3. Type Value
    type_value = TYPE_VALUE.get(task_type, 1.0)

    # 4. Urgency Boost
    urgency_boost = 1.0
    if "urgent" in title or "critical" in title:
        urgency_boost = 1.25

    # Composite Score
    score = (priority_weight * type_value * urgency_boost) / effort_factor

    # Scale into a more visible range
    return round(score * 10, 2)