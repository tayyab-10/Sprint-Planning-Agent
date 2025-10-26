from fastapi import APIRouter, Request
from app.core.data_loader import DataLoader
from app.core.planner_engine import plan_multiple_sprints
from app.core.summarizer import generate_sprint_summary

router = APIRouter()

@router.get("/plan/{project_id}")
async def plan_sprint_for_project(project_id: str, request: Request):
    print(f"🚀 Sprint planning initiated for Project: {project_id}")

    try:
        # Forward authorization headers if provided
        incoming = {}
        if "authorization" in request.headers:
            incoming["Authorization"] = request.headers.get("authorization")
        if "cookie" in request.headers:
            incoming["Cookie"] = request.headers.get("cookie")

        # Fetch data from Node backend
        loader = DataLoader(project_id, incoming_headers=incoming)
        data = await loader.get_project_data()
        members, tasks = data["members"], data["tasks"]

        print(f"📊 Loaded {len(members)} members and {len(tasks)} tasks.")

        # --- PLAN MULTIPLE SPRINTS ---
        sprints = plan_multiple_sprints(project_id, members, tasks)

        # --- AI SUMMARY GENERATION ---
        try:
            summary = await generate_sprint_summary(tasks)
            if isinstance(sprints, list) and sprints:
                # attach summary only to last sprint
                sprints[-1].update(summary)
            print("🤖 AI summary added successfully.")
        except Exception as ai_err:
            print(f"⚠️ AI summary failed (non-blocking): {ai_err}")
            if sprints:
                sprints[-1]["aiSummary"] = "AI summary failed."
                sprints[-1]["aiConfidence"] = 0.0

        print(f"🏁 Successfully generated {len(sprints)} sprints.")
        return {"success": True, "projectId": project_id, "sprints": sprints}

    except Exception as e:
        print(f"❌ Route error: {e}")
        return {"success": False, "error": str(e)}
