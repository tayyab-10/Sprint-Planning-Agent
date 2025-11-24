import httpx
import json
import logging
import traceback
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

# Assuming these imports are correct based on your project structure
from app.config import NODE_BASE_URL, NODE_API_KEY, NODE_API_KEY_HEADER, NODE_API_KEY_PREFIX, NODE_COOKIE
from app.models.project_member import ProjectMember
from app.models.task import Task 

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Hybrid Data Fetcher for Sprint Planner Agent.
    Fetches data securely from Node.js backend APIs and injects validated data into local models.
    """

    def __init__(self, project_id: str, incoming_headers: dict | None = None):
        self.project_id = project_id
        self.members: List[ProjectMember] = []
        self.tasks: List[Task] = []
        self.project_details: Dict[str, Any] = {}
        self.sprint_config: Dict[str, Any] = {}
        self.sprints: List[Dict[str, Any]] = []

        # Normalize incoming headers
        self.incoming_headers = {}
        if incoming_headers:
            for k, v in incoming_headers.items():
                if k.lower() == "authorization":
                    self.incoming_headers["Authorization"] = v
                elif k.lower() == "cookie":
                    self.incoming_headers["Cookie"] = v
                else:
                    self.incoming_headers[k] = v

        print(f"🟦 [INIT] DataLoader created for Project: {self.project_id}")

    # 🔹 Common function to build headers (merging env + incoming)
    def _build_headers(self):
        headers = dict(self.incoming_headers)

        if NODE_API_KEY and "Authorization" not in headers:
            headers[NODE_API_KEY_HEADER] = f"{NODE_API_KEY_PREFIX}{NODE_API_KEY}"

        if NODE_COOKIE and "Cookie" not in headers:
            headers["Cookie"] = NODE_COOKIE

        return headers

    def load_members_from_request_body(self, member_data: List[Dict[str, Any]]):
        """Loads member data provided directly in the request body."""
        try:
            parsed_members = []
            for m in member_data:
                m['_id'] = m.get('projectMemberId') or m.get('_id') 
                parsed_members.append(ProjectMember(**m))
            self.members = parsed_members
            print(f"✅ [MEMBERS LOAD] {len(self.members)} members loaded from request body.")
        except Exception as e:
            print(f"❌ [ERROR] Failed to load members from body: {e}")
            print(f"DEBUG: Failed member data sample: {member_data[:1]}") 
            self.members = []
        return self.members

    async def fetch_project_tasks(self):
        url = f"{NODE_BASE_URL}/tasks/{self.project_id}"
        headers = self._build_headers()
        print(f"🚀 Fetching Project Tasks from: {url}")

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=15.0, headers=headers)
                print(f"✅ [TASKS API RESPONSE] Status: {res.status_code}")
                res.raise_for_status()
                data = res.json()
                
            print(f"📦 [DEBUG RAW API] Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")

            if isinstance(data, str):
                data = json.loads(data)
            
            self.project_details = data.get('projectDetails', {})
            self.sprint_config = data.get('sprintConfiguration', {})
            self.sprints = data.get('sprints', [])

            # Extract tasks
            tasks_list = []
            if isinstance(data, dict):
                if "tasks" in data:
                    print("🔍 Found key: 'tasks'. Extracting list.")
                    tasks_list = data["tasks"]
                elif "data" in data and isinstance(data["data"], list):
                    print("🔍 Found key: 'data' (list). Extracting list.")
                    tasks_list = data["data"]
                elif data.get('_id') and data.get('title'):
                    print("🔍 Found a single task object.")
                    tasks_list = [data]
            
            if not isinstance(tasks_list, list):
                raise ValueError(f"Unexpected response structure for tasks: {type(tasks_list)}")

            print(f"📊 [DEBUG TASKS] Found {len(tasks_list)} raw task objects for processing.")

            normalized = []
            for t in tasks_list:
                tt = dict(t)
                tt['_id'] = tt.get('taskId') or tt.get('_id') 
                
                # Default assignee details
                assignee_details = None
                
                # --- START: Assignment ID and Details Logic ---
                
                # 1. Get the authoritative Project Member ID for the planner
                pm_id = tt.get('assignedPrimaryProjectMemberId')
                
                # 2. Preferentially capture User Details from the 'assignedTo' object (full user object)
                if isinstance(tt.get('assignedTo'), dict):
                    at = tt.get('assignedTo')
                    user_id = at.get('_id') or at.get('id')
                    
                    assignee_details = {
                        'projectMemberId': pm_id, # Use the authoritative PM ID
                        'userId': user_id, 
                        'name': at.get('name'),
                        'email': at.get('email'),
                        'role': at.get('role'),
                        'avatar': at.get('avatar')
                    }
                    print(f"   [DEBUG NORM] Task {tt['_id']}: Details captured from 'assignedTo' object.")

                # Fallback: Capture details from 'assignedPrimary' (which may be a duplicate user object)
                elif isinstance(tt.get('assignedPrimary'), dict):
                    ap = tt.get('assignedPrimary')
                    user_id = ap.get('_id') or ap.get('id')
                    
                    assignee_details = {
                        'projectMemberId': pm_id, 
                        'userId': user_id,
                        'name': ap.get('name'),
                        'email': ap.get('email'),
                        'role': ap.get('role'),
                        'avatar': ap.get('avatar')
                    }
                    print(f"   [DEBUG NORM] Task {tt['_id']}: Details captured from 'assignedPrimary'.")
                
                # Attach details to the task payload (requires Task model to have 'assigneeDetails')
                if assignee_details:
                    tt['assigneeDetails'] = assignee_details

                # Critical: Ensure the ProjectMemberId is explicitly set for the Task Pydantic model
                tt['assignedPrimaryProjectMemberId'] = pm_id
                
                # Log final decision
                print(f"   [DEBUG NORM] Task {tt['_id']} ('{tt.get('title', 'N/A')}'): Planner will use PM ID: {pm_id}")
                
                normalized.append(tt)

            # Use the updated Task model for validation and field flattening
            self.tasks = [Task(**t) for t in normalized]
            print(f"✅ [SUCCESS] {len(self.tasks)} tasks parsed and loaded.")

        except Exception as e:
            # --- Fallback tasks (used when API call fails) ---
            print(f"❌ [ERROR] Failed to fetch tasks: {e}")
            print(traceback.format_exc())
            
            fallback_date = date.today() + timedelta(days=5)
            self.tasks = [
                Task(_id="t1", title="Implement login API endpoint", priority="High", status="Backlog", 
                     assignedPrimaryProjectMemberId="m1", deadline=fallback_date, estimatedHours=8.0, 
                     dependencies=[]),
                Task(_id="t2", title="Write frontend login component", priority="High", status="Backlog", 
                     assignedPrimaryProjectMemberId="m2", deadline=fallback_date + timedelta(days=2), estimatedHours=6.0, 
                     dependencies=["t1"]),
                Task(_id="t3", title="Refactor legacy config service", priority="Medium", status="Backlog", 
                     assignedPrimaryProjectMemberId=None, deadline=fallback_date + timedelta(days=15), estimatedHours=12.0, 
                     dependencies=[]),
            ]
            print(f"⚠️ Using fallback demo tasks.")
            
        return self.tasks

    async def get_project_data(self):
        """Fetches all necessary project data: members, tasks, and configuration."""
        if not self.members:
             self.members = [
                 ProjectMember(projectMemberId="m1", role="backend", baseWeeklyHours=40, availabilityFactor=1.0, reliabilityScore=0.9),
                 ProjectMember(projectMemberId="m2", role="frontend", baseWeeklyHours=40, availabilityFactor=1.0, reliabilityScore=0.9),
             ]
             print("⚠️ Using dummy members as none were loaded.")

        print("🔄 Fetching full project data (tasks + config)...")
        tasks = await self.fetch_project_tasks()
        
        print(f"DEBUG: Final Loaded Members (First): {self.members[0].model_dump() if self.members else 'None'}")
        print(f"DEBUG: Final Loaded Tasks (First): {self.tasks[0].model_dump() if self.tasks else 'None'}")
        
        print(f"📊 Project Data Summary: {len(self.members)} members | {len(tasks)} tasks")
        
        return {
            "members": self.members, 
            "tasks": tasks,
            "project_details": self.project_details,
            "sprint_config": self.sprint_config,
            "sprints": self.sprints
        }