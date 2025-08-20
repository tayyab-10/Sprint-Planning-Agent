from fastapi import FastAPI
from db.mongo import tasks_col, users_col
from bson import ObjectId

app = FastAPI()

# --- helper serializer ---
def serialize(doc):
    doc["_id"] = str(doc["_id"])
    return doc


# ✅ Auto-Prioritization Endpoint
@app.get("/agent/auto-prioritize")
async def auto_prioritize():
    """
    Fetch tasks and return sorted backlog.
    Criteria: status → priority → deadline
    """
    tasks = await tasks_col.find({}).to_list(length=None)

    status_order = {"todo": 0, "in-progress": 1, "done": 2}

    prioritized = sorted(
        tasks,
        key=lambda t: (
            status_order.get(t.get("status", "todo"), 99),
            t.get("priority", 5),
            t.get("deadline", "9999-12-31"),
        ),
    )

    return {"prioritized_backlog": [serialize(t) for t in prioritized]}


# 🚧 Blocker Detection Endpoint
@app.get("/agent/blockers")
async def detect_blockers():
    """
    Find tasks marked as 'blocked'.
    """
    blockers = await tasks_col.find({"status": "blocked"}).to_list(length=None)

    return {
        "blockers": [
            {"_id": str(t["_id"]), "title": t["title"], "reason": t.get("blocker_reason", "Not specified")}
            for t in blockers
        ]
    }


# 💤 Idle Contributor Detection Endpoint
@app.get("/agent/idle-contributors")
async def idle_contributors():
    """
    Detect contributors with no assigned tasks in progress.
    """
    users = await users_col.find({}).to_list(length=None)
    tasks = await tasks_col.find({}).to_list(length=None)

    busy_users = {t.get("assignee") for t in tasks if t.get("status") in ["todo", "in-progress"]}
    idle = [u for u in users if u["name"] not in busy_users]

    return {"idle_contributors": [serialize(u) for u in idle]}
