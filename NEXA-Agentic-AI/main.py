# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.sprint_agent import build_plan, apply_plan
from db.mongo import ensure_indexes, tasks_col, notifications_col
from bson import ObjectId
import uvicorn

app = FastAPI(title="NEXA Sprint Planner API", version="1.0.0")

class SprintPayload(BaseModel):
    sprintId: str

@app.on_event("startup")
async def startup():
    await ensure_indexes()

@app.post("/planner/preview")
async def planner_preview(payload: SprintPayload):
    try:
        plan = await build_plan(payload.sprintId)
        return plan
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/planner/apply")
async def planner_apply(payload: SprintPayload):
    try:
        plan = await build_plan(payload.sprintId)
        result = await apply_plan(payload.sprintId, plan)
        return {"plan": plan, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/sprints/{sprint_id}/tasks")
async def get_sprint_tasks(sprint_id: str):
    s_oid = ObjectId(sprint_id)
    cursor = tasks_col.find({"sprintId": s_oid})
    rows = await cursor.to_list(length=None)
    for r in rows:
        r["_id"] = str(r["_id"])
        if r.get("assignee"): r["assignee"] = str(r["assignee"])
        if r.get("sprintId"): r["sprintId"] = str(r["sprintId"])
    return {"tasks": rows}

@app.get("/notifications/{user_id}")
async def get_notifications(user_id: str):
    cursor = notifications_col.find({"userId": ObjectId(user_id)})
    rows = await cursor.to_list(length=None)
    for r in rows:
        r["_id"] = str(r["_id"])
        r["userId"] = str(r["userId"]) if r.get("userId") else None
    return {"notifications": rows}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
