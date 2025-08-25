# agents/prioritizer.py
from datetime import datetime
from typing import List

PRIORITY_MAP = {"High": 1.0, "Medium": 0.6, "Low": 0.3}

def days_until(deadline):
    if not deadline:
        return 365.0
    if isinstance(deadline, str):
        try:
            deadline = datetime.fromisoformat(deadline)
        except Exception:
            return 365.0
    delta = (deadline - datetime.utcnow()).total_seconds() / 86400.0
    return max(delta, 0.0)

def score_task(task: dict, sprint_keywords: List[str]) -> float:
    """
    Score considers:
    - Relevance to sprint keywords (40%)
    - Deadline urgency (30%)
    - Declared priority (20%)
    - Size smallness (10%)
    """
    ttype = (task.get("type") or "").lower()
    title = (task.get("title") or "").lower()
    relevance = 1.0 if any(k in ttype or k in title for k in sprint_keywords) else 0.5

    dl = task.get("deadline")
    d_days = days_until(dl)
    deadline_score = 1.0 / (1.0 + d_days)

    priority_score = PRIORITY_MAP.get(task.get("priority", "Medium"), 0.6)

    est = float(task.get("estimatedHours") or 1.0)
    size_score = 1.0 / (1.0 + est / 8.0)

    return 0.40*relevance + 0.30*deadline_score + 0.20*priority_score + 0.10*size_score
