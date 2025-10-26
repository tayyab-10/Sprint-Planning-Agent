from datetime import datetime, date, timedelta


def compute_task_score(task):
    """Compute a numeric score for a Task.

    Urgency is derived from `dueDate` (ISO date string) if present. If not,
    fall back to a legacy `deadlineDays` numeric field when available. If
    neither is present we assume a default of 5 days (low urgency).
    """
    priority_map = {"Low": 1, "Medium": 2, "High": 3, "Critical": 5}
    pr = priority_map.get(getattr(task, "priority", None), 2)

    # Determine days until due
    days_until = None
    due = getattr(task, "dueDate", None)
    if due:
        # try parse ISO date/time or a plain integer string
        try:
            dt = datetime.fromisoformat(due)
            days_until = (dt.date() - date.today()).days
        except Exception:
            try:
                # maybe the API sent a simple integer (days)
                days_until = int(due)
            except Exception:
                days_until = None

    # legacy fallback if model still has deadlineDays attr
    if days_until is None and hasattr(task, "deadlineDays"):
        try:
            days_until = int(getattr(task, "deadlineDays") or 5)
        except Exception:
            days_until = None

    if days_until is None:
        days_until = 5

    urgency = 5 - min(5, max(0, days_until))

    value = getattr(task, "businessValue", 1) or 1
    effort = max(1, getattr(task, "estimatedHours", 4.0) / 4)
    return (pr * 2) + value + urgency - effort
