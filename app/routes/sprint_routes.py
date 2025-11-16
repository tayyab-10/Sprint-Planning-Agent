from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

from app.core.planner_engine import plan_single_sprint
from app.core.data_loader import DataLoader

router = APIRouter()

# ---------------------------------------------------------
# Helper: extract Authorization + Cookie headers
# ---------------------------------------------------------
def _build_forward_headers(request: Request) -> Dict[str, str]:
    headers = {}

    if "authorization" in request.headers:
        headers["Authorization"] = request.headers.get("authorization")

    if "cookie" in request.headers:
        headers["Cookie"] = request.headers.get("cookie")

    # Optional custom headers (good practice)
    if "x-user-id" in request.headers:
        headers["X-User-Id"] = request.headers.get("x-user-id")

    return headers


# ---------------------------------------------------------
# Request models (Standardized for '_id' property access)
# ---------------------------------------------------------
class MemberModel(BaseModel):
    # Use 'id' internally, but accept '_id' from incoming JSON payload
    id: str = Field(..., alias="_id") 
    
    name: Optional[str] = None
    role: Optional[str] = None
    availabilityPct: float = 1.0
    hourlyCapacity: float = 40.0
    velocity: Optional[int] = 0
    reliability: Optional[float] = 0.5
    # Optional client-provided cap for max tasks this member may take
    effective_max_tasks: Optional[int] = None
    
    # This property ensures that the planner_engine (which uses m._id) can still access the ID.
    @property
    def _id(self) -> str:
        return self.id

    class Config:
        # Allows Pydantic to accept `_id` in the input and map it to the `id` field
        allow_population_by_field_name = True 
        # Allows the @property `_id` to be accessed without generating a validation error
        ignored_properties = ["_id"]


class SprintPlanRequest(BaseModel):
    duration: int = 7
    members: List[MemberModel]
    # NEW: Maximum number of tasks to assign per member (optional limit)
    maxTasksPerMember: Optional[int] = None 


# ---------------------------------------------------------
# POST /api/sprint/plan/{project_id}
# ---------------------------------------------------------
@router.post("/plan/{project_id}")
async def generate_sprint_plan(project_id: str, req: SprintPlanRequest, request: Request):
    try:
        # 1. Forward headers to Node backend
        incoming = _build_forward_headers(request)
        
        # FIX: Check for debug query parameter
        debug_mode = request.query_params.get("debug", "false").lower() == "true"

        # 2. Load all project tasks from Node
        loader = DataLoader(project_id, incoming_headers=incoming)
        tasks = await loader.fetch_project_tasks()

        if not tasks:
            raise HTTPException(400, "No tasks available for sprint planning")

        if not req.members:
            raise HTTPException(400, "No project members provided")

        # 3. Run the new AI single sprint planner
        sprint = await plan_single_sprint(
            project_id=project_id,
            members=req.members,
            tasks=tasks,
            sprint_duration=req.duration,
            max_tasks_per_member=req.maxTasksPerMember,
            debug_mode=debug_mode # Pass debug flag
        )

        # FIX: Wrap the single sprint object in an array as required by the contract
        return {
            "success": True,
            "projectId": project_id,
            "sprints": [sprint] 
        }

    except Exception as e:
        # Log the actual error for better debugging
        print(f"ERROR during sprint planning for project {project_id}: {e}")
        return {
            "success": False,
            "message": f"Sprint planning failed: {str(e)}"
        }