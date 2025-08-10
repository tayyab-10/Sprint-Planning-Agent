from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from agents import TaskAnalyzerAgent, SprintAllocatorAgent, AcceptanceCriteriaAgent
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="NEXA Agentic AI - Sprint Planner", version="1.0")

# Optional: Allow frontend/backend integration later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Input Model -----
class ProjectInput(BaseModel):
    description: str

# ----- Output Model (Optional, for validation) -----
class SprintPlanResponse(BaseModel):
    tasks: List[str]
    sprints: Dict[str, List[str]]
    acceptance_criteria: Dict[str, List[str]]

# ----- Initialize Agents -----
task_agent = TaskAnalyzerAgent()
sprint_agent = SprintAllocatorAgent()
criteria_agent = AcceptanceCriteriaAgent()

# ----- API Route -----
@app.post("/plan-sprint")
async def plan_sprint(input: ProjectInput):
    """
    Main route to accept project description and return structured sprint plan.
    """
    try:
        # Step 1: Analyze tasks
        tasks = task_agent.analyze_description(input.description)

        # Step 2: Allocate to sprints
        sprints = sprint_agent.allocate_to_sprints(tasks)

        # Step 3: Generate acceptance criteria per task
        acceptance_criteria = {}
        for task in tasks:
            acceptance_criteria[task] = criteria_agent.generate_criteria(task)

        # Step 4: Return structured JSON response
        return {
            "tasks": tasks,
            "sprints": sprints,
            "acceptance_criteria": acceptance_criteria
        }

    except Exception as e:
        return {"error": str(e)}
