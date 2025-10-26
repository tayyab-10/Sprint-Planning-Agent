from datetime import datetime, timedelta
from app.core.scorer import compute_task_score

SPRINT_DURATION_DAYS = 4  # configurable
HOURS_PER_DAY = 8
MAX_SPRINTS = 100  # safety cap to prevent overflow

def plan_multiple_sprints(project_id, members, tasks):
    if not tasks or not members:
        print("⚠️ No tasks or members found — skipping sprint generation.")
        return []

    # --- STEP 1: Score and sort tasks ---
    for t in tasks:
        t.score = compute_task_score(t)
    tasks.sort(key=lambda x: x.score, reverse=True)

    # --- STEP 2: Initial setup ---
    sprint_batches = []
    sprint_start = datetime.today()
    sprint_index = 1
    task_index = 0
    total_tasks = len(tasks)
    num_members = len(members)

    print(f"🧮 Total Tasks: {total_tasks} | Members: {num_members}")

    # --- STEP 3: Create sprints in sequence ---
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

        sprint_data = {
            "sprintName": f"Sprint {sprint_index} - {sprint_start.date()}",
            "projectId": project_id,
            "startDate": sprint_start.date().isoformat(),
            "endDate": sprint_end.date().isoformat(),
            "tasks": [t.model_dump() for t in sprint_tasks],
            "assignedMembers": assigned_members,
        }

        sprint_batches.append(sprint_data)
        print(f"✅ Created Sprint {sprint_index} with {len(sprint_tasks)} tasks.")

        sprint_index += 1
        sprint_start = sprint_end + timedelta(days=1)

    print(f"🚀 Generated {len(sprint_batches)} sprints in total.")
    return sprint_batches
