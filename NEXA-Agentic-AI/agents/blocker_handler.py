# agents/blocker_handler.py
from datetime import datetime, timedelta
from bson import ObjectId
from db.mongo import tasks_col, assignments_col, notifications_col, users_col

async def handle_blocked_tasks(sprint_id: str, hours_threshold: int = 12, reassignment_roles: list = None):
    """
    Reassign blocked tasks older than threshold or escalate via notification.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours_threshold)
    sprint_oid = ObjectId(sprint_id)

    cursor = tasks_col.find({
        "sprintId": sprint_oid,
        "status": "blocked",
        "blockedAt": {"$lt": cutoff}
    })

    results = []
    async for t in cursor:
        # candidate users (optional role filter)
        query = {}
        if reassignment_roles:
            query["role"] = {"$in": reassignment_roles}
        candidates = users_col.find(query)

        best_user = None
        lowest_load = float("inf")
        async for u in candidates:
            pipeline = [
                {"$match": {"assignee": u["_id"], "status": {"$in": ["open", "in-progress"]}}},
                {"$group": {"_id": None, "sum": {"$sum": "$estimatedHours"}}}
            ]
            agg = await tasks_col.aggregate(pipeline).to_list(length=1)
            load = agg[0]["sum"] if agg else 0
            if load < lowest_load:
                lowest_load = load
                best_user = u

        if best_user:
            await tasks_col.update_one(
                {"_id": t["_id"]},
                {"$set": {"assignee": best_user["_id"], "status": "in-progress", "reassignedAt": datetime.utcnow()}}
            )
            await assignments_col.insert_one({
                "taskId": t["_id"],
                "userId": best_user["_id"],
                "assignedAt": datetime.utcnow(),
                "role": best_user.get("role"),
                "status": "assigned"
            })
            await notifications_col.insert_one({
                "userId": best_user["_id"],
                "message": f"You have been reassigned a previously blocked task: {t.get('title')}",
                "createdAt": datetime.utcnow(),
                "read": False,
                "meta": {"taskId": t["_id"], "type": "reassignment"}
            })
            results.append({"taskId": str(t["_id"]), "newAssignee": str(best_user["_id"])})
        else:
            await notifications_col.insert_one({
                "userId": None,
                "message": f"Blocked task needs manual attention: {t.get('title')}",
                "createdAt": datetime.utcnow(),
                "read": False,
                "meta": {"taskId": t["_id"], "type": "escalation"}
            })
            results.append({"taskId": str(t["_id"]), "escalated": True})

    return results
