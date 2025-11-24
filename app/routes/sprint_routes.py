from fastapi import APIRouter, HTTPException, Request, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# Import the new, comprehensive models and the planner function
from app.models.project_member import ProjectMember
from app.models.sprint import SprintPlanOutput
from app.core.planner_engine import plan_single_sprint
from app.core.data_loader import DataLoader

router = APIRouter()

# ---------------------------------------------------------
# Helper: extract Authorization + Cookie headers
# ---------------------------------------------------------
def _build_forward_headers(request: Request) -> Dict[str, str]:
    """Extracts Authorization and Cookie headers to forward to the Node backend."""
    headers = {}

    # Normalize keys to lowercase for robust lookup
    req_headers = {k.lower(): v for k, v in request.headers.items()}

    if "authorization" in req_headers:
        headers["Authorization"] = req_headers["authorization"]

    if "cookie" in req_headers:
        headers["Cookie"] = req_headers["cookie"]

    if "x-user-id" in req_headers:
        headers["X-User-Id"] = req_headers["x-user-id"]

    return headers


# ---------------------------------------------------------
# Request Models (Using the rich ProjectMember model)
# ---------------------------------------------------------

class SprintPlanningRequest(BaseModel):
    """
    Input model matching the necessary data required by the Sprint Planner Agent.
    """
    # Use the comprehensive Pydantic model for member validation
    members: List[ProjectMember] = Field(..., description="List of all project members with capacity and reliability metrics.")
    
    # NEW: Pass the full sprint configuration (length, goals, etc.)
    sprint_config: Dict[str, Any] = Field(..., description="Details like sprintLengthDays, workHoursPerDay, fixedDeadlineConstraints.")
    
    # Note: maxTasksPerMember is now ideally derived from capacity within the planner, 
    # but we can retain the field if the client must override it.
    maxTasksPerMember: Optional[int] = None 


# ---------------------------------------------------------
# POST /api/sprint/plan/{project_id}
# ---------------------------------------------------------
@router.post("/plan/{project_id}", response_model=SprintPlanOutput)
async def generate_sprint_plan(
    project_id: str,
    request: Request,
    req: SprintPlanningRequest = Body(...),
) -> SprintPlanOutput:
    try:
        # 1. Prepare Environment
        incoming_headers = _build_forward_headers(request)
        debug_mode = request.query_params.get("debug", "false").lower() == "true"
        
        loader = DataLoader(project_id, incoming_headers=incoming_headers)
        
        # 2. Load Data (Members from Body, Tasks/Config from API)
        
        # A. Load RICH Member data from the request body (crucial for capacity calculation)
        # `req.members` will be a list of Pydantic `ProjectMember` models; convert to dicts
        # so DataLoader can normalize and re-construct models as needed.
        loader.load_members_from_request_body([m.model_dump() for m in req.members])
        
        # B. Fetch Tasks, Project Details, and Fallback Config from the Node API
        project_data = await loader.get_project_data()
        
        # 3. Execute Planning Logic
        
        # Merge the config from the request body with any fallback config loaded from the API
        final_sprint_config = {
            **project_data.get("sprint_config", {}), # API fallback config
            **req.sprint_config                      # Client-provided/overriding config
        }
        
        # The new plan_single_sprint now takes the full sprint_config dictionary
        final_plan_data = await plan_single_sprint(
            project_id=project_id,
            members=project_data["members"],
            tasks=project_data["tasks"],
            sprint_config=final_sprint_config,
            debug_mode=debug_mode
        )

        # 4. Return the Final Plan
        # Return the validated SprintPlanOutput object directly. 
        # We do NOT wrap it in {"sprints": [sprint]} unless the client explicitly expects that wrapper.
        # The agent's contract only requires the SprintPlanOutput JSON.
        return SprintPlanOutput(**final_plan_data)

    except HTTPException:
        # Re-raise explicit HTTP exceptions (e.g., 400 No tasks available)
        raise
        
    except Exception as e:
        # Log the actual error for better debugging
        print(f"FATAL ERROR during sprint planning for project {project_id}: {e}")
        # Return the error in the required output format (success: False)
        raise HTTPException(
            status_code=500,
            detail=f"Sprint planning failed: {str(e)}",
            headers={"X-Failure-Reason": "Agent internal error"}
        )