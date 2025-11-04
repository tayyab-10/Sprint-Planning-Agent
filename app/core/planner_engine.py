from datetime import datetime, timedelta
import asyncio
from app.core.scorer import compute_task_score
from app.core.summarizer import generate_sprint_summary

SPRINT_DURATION_DAYS = 4
HOURS_PER_DAY = 8
MAX_SPRINTS = 100

async def plan_multiple_sprints(project_id, members, tasks):
    """
    Plans multiple sprints with AI summaries, goals, and phases.
    Non-blocking async — integrates Gemini summary per sprint.
    """
    if not tasks or not members:
        print("⚠️ No tasks or members found — skipping sprint generation.")
        return []

    # --- STEP 1: Score and sort tasks ---
    for t in tasks:
        t.score = compute_task_score(t)
    tasks.sort(key=lambda x: x.score, reverse=True)

    sprint_batches = []
    sprint_start = datetime.today()
    sprint_index = 1
    task_index = 0
    total_tasks = len(tasks)
    num_members = len(members)

    print(f"🧮 Total Tasks: {total_tasks} | Members: {num_members}")

    # --- STEP 2: Create sprints sequentially ---
    while task_index < total_tasks and sprint_index <= MAX_SPRINTS:
        sprint_tasks = []
        assigned_members = []

        for m in members:
            if task_index >= total_tasks:
                break

            task = tasks[task_index]
            task.assignedTo = m._id
            sprint_tasks.append(task)
            assigned_members.append(m._id)
            task_index += 1

        sprint_end = sprint_start + timedelta(days=SPRINT_DURATION_DAYS)

        # --- Default sprint data ---
        sprint_data = {
            "sprintName": f"Sprint {sprint_index} - {sprint_start.date()}",
            "projectId": project_id,
            "startDate": sprint_start.date().isoformat(),
            "endDate": sprint_end.date().isoformat(),
            "tasks": [t.model_dump() for t in sprint_tasks],
            "assignedMembers": assigned_members,
            "aiSummary": f"Sprint {sprint_index} generated without AI summary.",
            "aiConfidence": 0.0,
            "plannedBy": "SprintPlannerAgent",
            "velocity": len(sprint_tasks),
            "status": "Planned",
            "goals": [],
            "phase": "Unspecified"
        }

        # --- STEP 3: Add AI Summary (async, non-blocking) ---
        try:
            ai_data = await generate_sprint_summary(sprint_tasks)
            if ai_data:
                sprint_data.update(ai_data)
        except Exception as e:
            print(f"⚠️ AI Summary failed for Sprint {sprint_index}: {e}")

        # --- STEP 4: Auto-generate goals based on task themes ---
        sprint_data["goals"] = derive_goals_from_tasks(sprint_tasks)

        # --- STEP 5: Assign phase based on sprint number ---
        sprint_data["phase"] = infer_phase_label(sprint_index)

        sprint_batches.append(sprint_data)
        print(f"✅ Created Sprint {sprint_index} with {len(sprint_tasks)} tasks.")

        sprint_index += 1
        sprint_start = sprint_end + timedelta(days=1)

    print(f"🚀 Generated {len(sprint_batches)} sprints in total.")
    return sprint_batches


# ----------------- Helper Functions -----------------

def derive_goals_from_tasks(tasks):
    """Generates 2–3 high-level sprint goals from task titles."""
    if not tasks:
        return []
    titles = [getattr(t, "title", "") for t in tasks if getattr(t, "title", "")]
    if not titles:
        return []
    top_titles = titles[:3]
    return [f"Complete {t.lower()}" for t in top_titles]


def infer_phase_label(index: int):
    """Assigns project phase names dynamically."""
    if index <= 3:
        return "Setup & Initialization"
    elif index <= 10:
        return "Core Development"
    elif index <= 20:
        return "Feature Expansion"
    elif index <= 25:
        return "Testing & Optimization"
    else:
        return "Final Delivery & Review"
# ----------------- End of Module -----------------