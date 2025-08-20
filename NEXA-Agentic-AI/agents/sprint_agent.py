# agents/sprint_agent.py
from db.mongo import tasks_col, sprints_col, assignments_col, notifications_col
from agents.prioritizer import score_task
from agents.blocker_handler import handle_blocked_tasks
from datetime import datetime
from bson import ObjectId
import re
from typing import List, Dict

def extract_keywords(text: str) -> List[str]:
    if not text:
        return []
    return [w.lower() for w in re.findall(r'\w+', text)]

async def _current_member_load(user_id):
    agg = await tasks_col.aggregate([
        {"$match": {"assignee": user_id, "status": {"$in": ["open", "in-progress"]}}},
        {"$group": {"_id": None, "sum": {"$sum": "$estimatedHours"}}}
    ]).to_list(length=1)
    return agg[0]["sum"] if agg else 0

async def build_plan(sprint_id: str) -> Dict:
    """Preview: compute plan without writing to DB."""
    s_oid = ObjectId(sprint_id)
    sprint = await sprints_col.find_one({"_id": s_oid})
    if not sprint:
        raise ValueError("Sprint not found")

    keywords = extract_keywords(sprint.get("description", ""))
    only_bug = any(k in ["bug", "fix", "bugfix", "bug-fix", "bugs"] for k in keywords)

    cursor = tasks_col.find({
        "status": {"$in": ["open", "in-progress"]},
        "sprintId": None
    })
    backlog = await cursor.to_list(length=None)

    if only_bug:
        backlog = [t for t in backlog if (t.get("type") or "").lower() == "bug"]

    # Score & sort
    for t in backlog:
        t["score"] = score_task(t, keywords)
    backlog.sort(key=lambda x: x["score"], reverse=True)

    team_members = sprint.get("teamMembers", []) or []
    member_loads = {}
    for m in team_members:
        member_loads[str(m)] = await _current_member_load(m)

    capacity = float(sprint.get("capacityHours", 0))
    remaining = capacity

    plan_assignments = []
    for t in backlog:
        if remaining <= 0:
            break
        est = float(t.get("estimatedHours") or 1.0)
        if est > remaining:
            continue
        # pick least-loaded member
        candidate = None
        min_load = float("inf")
        for m in team_members:
            load = member_loads.get(str(m), 0)
            if load < min_load:
                min_load = load
                candidate = m
        if not candidate:
            break

        plan_assignments.append({
            "taskId": str(t["_id"]),
            "title": t.get("title"),
            "assignee": str(candidate),
            "estimatedHours": est,
            "score": t["score"]
        })
        member_loads[str(candidate)] = member_loads.get(str(candidate), 0) + est
        remaining -= est

    # Idle nudges (preview)
    idle_threshold = 4
    nudges = []
    for m in team_members:
        load = member_loads.get(str(m), 0)
        if load < idle_threshold:
            top_titles = [x["title"] for x in backlog if str(x["_id"]) not in {a["taskId"] for a in plan_assignments}][:3]
            nudges.append({"userId": str(m), "suggest": top_titles})

    return {
        "sprintId": sprint_id,
        "capacityHours": capacity,
        "remainingCapacity": remaining,
        "assignments": plan_assignments,
        "nudges": nudges,
        "notes": "Preview plan (no DB writes)."
    }

async def apply_plan(sprint_id: str, plan: Dict) -> Dict:
    """Commit: write assignments + notifications + handle blockers."""
    s_oid = ObjectId(sprint_id)
    now = datetime.utcnow()

    # Apply assignments
    for a in plan.get("assignments", []):
        t_oid = ObjectId(a["taskId"])
        u_oid = ObjectId(a["assignee"])

        await tasks_col.update_one({"_id": t_oid}, {
            "$set": {
                "sprintId": s_oid,
                "assignee": u_oid,
                "status": "in-progress",
                "assignedAt": now
            }
        })
        await assignments_col.insert_one({
            "taskId": t_oid,
            "userId": u_oid,
            "assignedAt": now,
            "role": None,
            "status": "assigned"
        })
        await sprints_col.update_one({"_id": s_oid}, {"$addToSet": {"tasks": t_oid}})
        await notifications_col.insert_one({
            "userId": u_oid,
            "message": f"You have been assigned: {a['title']}",
            "createdAt": now,
            "read": False,
            "meta": {"taskId": t_oid, "type": "assignment"}
        })

    # Create nudges
    for n in plan.get("nudges", []):
        u_oid = ObjectId(n["userId"])
        await notifications_col.insert_one({
            "userId": u_oid,
            "message": f"You appear underloaded. Consider tasks: {n['suggest']}",
            "createdAt": now,
            "read": False,
            "meta": {"type": "nudge", "suggestions": n["suggest"]}
        })

    # Blocker handling
    blocked_results = await handle_blocked_tasks(sprint_id)

    return {
        "appliedAssignments": len(plan.get("assignments", [])),
        "nudgesCreated": len(plan.get("nudges", [])),
        "blockedActions": blocked_results
    }
