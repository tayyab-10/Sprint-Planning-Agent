import httpx
import json
import logging
from app.config import NODE_BASE_URL, NODE_API_KEY, NODE_API_KEY_HEADER, NODE_API_KEY_PREFIX, NODE_COOKIE
from app.models.project_member import ProjectMember
from app.models.task import Task

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Hybrid Data Fetcher for Sprint Planner Agent.
    Fetches data securely from Node.js backend APIs (via token or cookie)
    and injects validated data into local models.
    """

    def __init__(self, project_id: str, incoming_headers: dict | None = None):
        self.project_id = project_id
        self.members = []
        self.tasks = []

        # Normalize incoming headers (Authorization / Cookie)
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
        print(f"🧩 Incoming Headers: {self.incoming_headers}")

    # 🔹 Common function to build headers (merging env + incoming)
    def _build_headers(self):
        headers = dict(self.incoming_headers)

        # Prefer incoming Authorization
        if NODE_API_KEY and "Authorization" not in headers:
            headers[NODE_API_KEY_HEADER] = f"{NODE_API_KEY_PREFIX}{NODE_API_KEY}"

        # Add Cookie if available
        if NODE_COOKIE and "Cookie" not in headers:
            headers["Cookie"] = NODE_COOKIE

        print(f"🔑 [HEADERS BUILT] {headers}")
        return headers

    async def fetch_project_members(self):
        url = f"{NODE_BASE_URL}/projectMember/{self.project_id}"
        headers = self._build_headers()
        print(f"🚀 Fetching Project Members from: {url}")

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=15.0, headers=headers)
                print(f"✅ [MEMBERS API RESPONSE] Status: {res.status_code}")
                print(f"📦 Raw Response: {res.text[:300]}...")  # limit output size
                res.raise_for_status()
                data = res.json()

            # ✅ unwrap actual key "team"
            if isinstance(data, str):
                data = json.loads(data)
            if isinstance(data, dict):
                if "team" in data:
                    print("🔍 Found key: 'team'")
                    data = data["team"]
                elif "projectMembers" in data:
                    print("🔍 Found key: 'projectMembers'")
                    data = data["projectMembers"]
                elif "members" in data:
                    print("🔍 Found key: 'members'")
                    data = data["members"]
                elif "data" in data:
                    print("🔍 Found key: 'data'")
                    data = data["data"]

            if not isinstance(data, list):
                raise ValueError(f"Unexpected structure for members: {type(data)}")

            parsed_members = []
            for m in data:
                parsed_members.append({
                    "_id": m.get("id") or m.get("_id"),
                    "name": m.get("name"),
                    "role": m.get("role"),
                    "availabilityPct": 1.0,
                    "hourlyCapacity": 40.0,
                    "velocity": 5
                })

            self.members = [ProjectMember(**m) for m in parsed_members]
            print(f"✅ [SUCCESS] {len(self.members)} members parsed and loaded.")
        except Exception as e:
            print(f"❌ [ERROR] Failed to fetch members: {e}")
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
                print(f"📦 Raw Response: {res.text[:300]}...")  # preview
                res.raise_for_status()
                data = res.json()

            # 🔹 Handle different response shapes
            if isinstance(data, str):
                data = json.loads(data)
            if isinstance(data, dict):
                if "tasks" in data:
                    print("🔍 Found key: 'tasks'")
                    data = data["tasks"]
                elif "data" in data:
                    print("🔍 Found key: 'data'")
                    data = data["data"]

            if not isinstance(data, list):
                raise ValueError(f"Unexpected response structure for tasks: {type(data)}")

            from datetime import date, timedelta
            normalized = []
            for t in data:
                tt = dict(t)
                if "dueDate" not in tt and "deadlineDays" in tt:
                    try:
                        days = int(tt.get("deadlineDays") or 0)
                        due = (date.today() + timedelta(days=days)).isoformat()
                        tt["dueDate"] = due
                    except Exception:
                        pass
                normalized.append(tt)

            self.tasks = [Task(**t) for t in normalized]
            print(f"✅ [SUCCESS] {len(self.tasks)} tasks parsed and loaded.")
        except Exception as e:
            print(f"❌ [ERROR] Failed to fetch tasks: {e}")
            from datetime import date, timedelta
            fallback = [
                {
                    "_id": "t1",
                    "title": "Implement login",
                    "priority": "High",
                    "status": "Open",
                    "assignedTo": "m1",
                    "dueDate": (date.today() + timedelta(days=3)).isoformat(),
                    "estimatedHours": 8.0,
                    "queueOrder": 1,
                    "businessValue": 8,
                    "dependencies": [],
                },
                {
                    "_id": "t2",
                    "title": "Write unit tests",
                    "priority": "Medium",
                    "status": "Open",
                    "assignedTo": "m2",
                    "dueDate": (date.today() + timedelta(days=5)).isoformat(),
                    "estimatedHours": 6.0,
                    "queueOrder": 2,
                    "businessValue": 5,
                    "dependencies": ["t1"],
                },
            ]
            self.tasks = [Task(**t) for t in fallback]
            print(f"⚠️ Using fallback demo tasks.")
        return self.tasks

    async def get_project_data(self):
        print("🔄 Fetching full project data (members + tasks)...")
        members = await self.fetch_project_members()
        tasks = await self.fetch_project_tasks()
        print(f"📊 Project Data Summary: {len(members)} members | {len(tasks)} tasks")
        return {"members": members, "tasks": tasks}
