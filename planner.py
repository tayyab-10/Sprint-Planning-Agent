from agents import task_decomposer, sprint_allocator
import json

def generate_sprint_plan(description: str):
    raw = task_decomposer(description)
    try:
        tasks_json = json.loads(raw)
    except json.JSONDecodeError:
        tasks_json = {"error": "Failed to parse OpenAI response."}
    sprint_plan = sprint_allocator(tasks_json)
    return {
        "backlog": tasks_json,
        "sprintAllocation": sprint_plan
    }
