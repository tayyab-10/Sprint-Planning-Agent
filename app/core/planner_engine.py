from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any, Tuple, Optional

# Assuming these files exist and contain the necessary functions
from app.core.scorer import compute_task_score
from app.core.summarizer import generate_sprint_summary

# ------------------------------------------------------
# CONFIG CONSTANTS
# ------------------------------------------------------

SOFT_MIN_RELIABILITY = 0.20        # Members below this threshold are skipped
RECOVERY_RATE = 0.02               # +2% reliability if assigned a task
DECAY_RATE = 0.01                  # -1% reliability if idle
BURNOUT_THRESHOLD = 3              # If member gets > 3 tasks → burnout penalty
BURNOUT_PENALTY = 0.05             # -5% reliability for burnout
ROLE_MATCH_BOOST = 1.15            # 15% weight boost if member’s role matches task
ROLE_MISMATCH_PENALTY = 0.80       # 20% weight reduction if mismatched
TASK_DEFAULT_EFFORT_HOURS = 8.0    # Default effort for a task if not defined (FIX: 0-hour tasks treated as 8h)
STANDARD_CAPACITY_BASE_HOURS = 40.0 # Used if member.hourlyCapacity is missing


# ------------------------------------------------------
# Role Keywords Mapping (Used for matching and difficulty distribution)
# ------------------------------------------------------
ROLE_KEYWORDS = {
    "backend": ["api", "database", "server", "backend", "auth"],
    "frontend": ["ui", "frontend", "react", "page", "component"],
    "mobile": ["android", "ios", "mobile", "flutter"],
    "designer": ["design", "ui", "ux", "figma"],
    "devops": ["deployment", "docker", "ci", "cd", "infrastructure"],
}


# ------------------------------------------------------
# Helper: Safely get task ID
# ------------------------------------------------------
def _get_task_id(task: Any) -> str:
    """Tries to get ID from a task object, checking for common field names."""
    if hasattr(task, 'id') and task.id:
        return task.id
    if hasattr(task, '_id') and task._id:
        return task._id
    raise AttributeError("Task object missing 'id' or '_id' attribute.")

# ------------------------------------------------------
# Helper: Get CORRECTED Task Effort
# ------------------------------------------------------
def _get_corrected_effort(task: Any) -> float:
    """Returns task effort, defaulting to 8.0h if input is 0 or missing."""
    raw_effort = getattr(task, 'estimatedHours', TASK_DEFAULT_EFFORT_HOURS)
    return raw_effort if raw_effort is not None and raw_effort > 0.0 else TASK_DEFAULT_EFFORT_HOURS


# ------------------------------------------------------
# Helper: Check if task matches member role
# ------------------------------------------------------
def role_match_score(member_role: str, task_title: str):
    if not member_role:
        return 1.0
    role = member_role.lower().strip()
    title = (task_title or "").lower()
    keywords = ROLE_KEYWORDS.get(role)
    if not keywords:
        return 1.0
    for word in keywords:
        if word in title:
            return ROLE_MATCH_BOOST
    return ROLE_MISMATCH_PENALTY


# ------------------------------------------------------
# Compute weighted score for member
# ------------------------------------------------------
def compute_member_weight(member, task_title=None):
    reliability = max(member.reliability or 0.0, 0.0)
    availability = member.availabilityPct or 1.0
    velocity_bonus = 1 + (member.velocity or 0) / 10
    role_factor = role_match_score(member.role, task_title)
    return reliability * availability * velocity_bonus * role_factor


# ------------------------------------------------------
# MAIN ENGINE – ALWAYS ONE SPRINT (Capacity-Aware)
# ------------------------------------------------------

async def plan_single_sprint(project_id, members, tasks, sprint_duration, max_tasks_per_member: Optional[int] = None, debug_mode: bool = False):
    """
    Generates EXACTLY ONE intelligent sprint with capacity-aware assignment.
    Implements early stopping and rich metadata output.
    """

    # 0. Initialize Capacity & Workload Tracker
    member_remaining_capacity = {}
    member_total_capacity = {}
    member_task_count = {m._id: 0 for m in members}
    members_map = {m._id: m for m in members}

    for m in members:
        base_capacity = m.hourlyCapacity if m.hourlyCapacity is not None and m.hourlyCapacity > 0 else STANDARD_CAPACITY_BASE_HOURS
        
        # Capacity = Base Hours * (Sprint Days / 7) * Availability
        total_capacity = base_capacity * (sprint_duration / 7.0) * m.availabilityPct
        
        # Point 2: Calculate flexible max tasks per member if not provided by PM
        # Default Max Tasks = Total Capacity / Default Task Effort (8h)
        default_max_tasks = max(1, round(total_capacity / TASK_DEFAULT_EFFORT_HOURS))
        m.effective_max_tasks = max_tasks_per_member if max_tasks_per_member is not None else default_max_tasks
        
        member_total_capacity[m._id] = {"total": total_capacity, "max_tasks": m.effective_max_tasks}
        member_remaining_capacity[m._id] = total_capacity
        
    # Filter tasks to ensure only unassigned tasks are considered
    unassigned_tasks = [t for t in tasks if getattr(t, 'assignedTo', None) is None]
    
    # STEP 1: Score all unassigned tasks
    scored_tasks: List[Tuple[float, Any]] = []
    for task in unassigned_tasks:
        score = compute_task_score(task)
        scored_tasks.append((score, task))

    scored_tasks.sort(key=lambda x: x[0], reverse=True)
    
    decision_log = []
    task_assignments: Dict[str, str] = {}
    assignment_reasons_log = [] # Point 6: Detailed assignment log
    rolled_over_tasks = []
    
    # STEP 2: For each scored task → choose best member
    for score, task in scored_tasks:
        # Use the corrected effort for all capacity/effort calculations
        task_effort = _get_corrected_effort(task)
        
        task_title = getattr(task, 'title', 'Untitled Task')
        task_id = _get_task_id(task)

        best_member_id = None
        best_weight = -999
        
        winning_role_factor = 0
        
        for m in members:
            member_id = m._id
            remaining_capacity = member_remaining_capacity.get(member_id, 0)
            raw_weight = compute_member_weight(m, task_title)
            current_task_count = member_task_count[member_id]
            
            # CHECK 1: MAX TASK COUNT (Uses m.effective_max_tasks)
            if current_task_count >= m.effective_max_tasks:
                if debug_mode: decision_log.append(f"⛔ Skipped {m.name}: Max task limit reached ({m.effective_max_tasks}).")
                continue
                
            # CHECK 2: CAPACITY
            if remaining_capacity < task_effort:
                if debug_mode: decision_log.append(f"⛔ Skipped {m.name}: Insufficient capacity for '{task_title}' (E: {task_effort:.1f}h). Left: {remaining_capacity:.1f}h")
                continue

            # CHECK 3: RELIABILITY (SOFT MIN)
            if raw_weight < SOFT_MIN_RELIABILITY:
                if debug_mode: decision_log.append(f"❌ Skipped {m.name}: Low reliability factor {m.reliability:.2f}")
                continue
            
            if debug_mode: decision_log.append(
                f"⭐ Candidate {m.name} for '{task_title}': weight={raw_weight:.3f}"
            )

            if raw_weight > best_weight:
                best_weight = raw_weight
                best_member_id = member_id
                winning_role_factor = role_match_score(m.role, task_title)

        # ASSIGNMENT LOGIC
        if not best_member_id:
            # Early Stop. If no one can take the task, roll over the rest.
            rolled_over_tasks = [task] + [t for _, t in scored_tasks[scored_tasks.index((score, task)) + 1:]]
            if debug_mode: decision_log.append(f"🛑 EARLY STOP: No suitable member found for '{task_title}'. {len(rolled_over_tasks)} tasks rolled over.")
            break 
            
        # Successful Assignment
        best_member = members_map[best_member_id]
        
        # Deduct capacity
        member_remaining_capacity[best_member_id] -= task_effort
        
        # Point 6: Capture Assignment Reason
        assignment_reasons_log.append({
            "task_id": task_id,
            "task_title": task_title,
            "member_id": best_member_id,
            "member_name": best_member.name,
            "reason": f"Selected due to highest weighted score ({best_weight:.2f}). Role factor: {winning_role_factor:.2f}. Capacity remaining: {member_remaining_capacity[best_member_id]:.1f}h."
        })
        
        task_assignments[task_id] = best_member_id
        member_task_count[best_member_id] += 1
        best_member.reliability = min(1.0, best_member.reliability + RECOVERY_RATE)

        if debug_mode: decision_log.append(
            f"✅ Assigned '{task_title}' → {best_member.name}. Cap Left: {member_remaining_capacity[best_member_id]:.1f}h. (New R={best_member.reliability:.2f})"
        )
    
    
    # STEP 3 & 4: Reliability Updates (Decay and Burnout)
    member_reliability_history = {}
    reliability_impact = {"increased": [], "unchanged": [], "penalized": []}

    for m in members:
        member_reliability_history[m._id] = {"before": m.reliability, "burnoutState": "normal"}

        # Decay Logic
        current_remaining = member_remaining_capacity.get(m._id, 0)
        total_cap = member_total_capacity.get(m._id, {}).get("total", 1)
        
        if current_remaining / total_cap > 0.90: 
            m.reliability = max(0.0, m.reliability - DECAY_RATE)
            member_reliability_history[m._id]["burnoutState"] = "idle"

        # Burnout Detection
        count = member_task_count.get(m._id, 0)
        if count > BURNOUT_THRESHOLD:
            m.reliability = max(0.0, m.reliability - BURNOUT_PENALTY)
            member_reliability_history[m._id]["burnoutState"] = "burnout"
        
        # Point 8: Reliability Impact Summary
        history = member_reliability_history[m._id]
        history["after"] = m.reliability
        
        if history["after"] > history["before"] + 0.001:
            reliability_impact["increased"].append(m.name)
        elif history["after"] < history["before"] - 0.001:
            reliability_impact["penalized"].append(m.name)
        else:
            reliability_impact["unchanged"].append(m.name)


    # STEP 5: Final output calculation and construction
    sprint_number = 1 
    sprint_start = datetime.today()
    sprint_name = f"Sprint {sprint_number} - {sprint_start.strftime('%b %d')}" 
    sprint_end = sprint_start + timedelta(days=sprint_duration)

    final_sprint_tasks = []
    total_planned_effort = 0.0
    all_tasks_map = {_get_task_id(t): t for t in tasks}

    # Finalize tasks and calculate velocity
    for task_id, assigned_member_id in task_assignments.items():
        task = all_tasks_map.get(task_id)
        if task:
            # FIX 2: Velocity and workload calculations must use corrected effort
            corrected_effort = _get_corrected_effort(task)
            
            task_data = task.model_dump()
            task_data['assignedTo'] = assigned_member_id
            
            # NOTE: We keep estimatedHours: 0.0 in the output tasks list 
            # if that's what the Node backend sent, to preserve the original data.
            # But all metrics rely on the corrected effort.

            final_sprint_tasks.append(task_data)
            total_planned_effort += corrected_effort
            
    assigned_members_list = list(set(task_assignments.values()))
    
    # Point 7 & FIX 3: Difficulty Distribution Radar / Workload Breakdown
    workload_difficulty = {"backend": 0.0, "frontend": 0.0, "mobile": 0.0, "designer": 0.0, "devops": 0.0, "other": 0.0}
    total_team_capacity = sum(c['total'] for c in member_total_capacity.values())

    for task in final_sprint_tasks:
        # FIX 3: Use corrected effort for workload difficulty calculation
        effort = _get_corrected_effort(task)
        task_type = task.get('type', 'other').lower()
        
        found_key = 'other'
        for key, keywords in ROLE_KEYWORDS.items():
            if task_type in key or any(k in task.get('title', '').lower() for k in keywords):
                found_key = key
                break
        
        workload_difficulty[found_key] = workload_difficulty.get(found_key, 0.0) + effort

    # Point 4 & FIX 4: Dynamic Phase Detection (Heuristic)
    dominant_type = max(workload_difficulty, key=workload_difficulty.get)
    # FIX 4: Use a threshold check to ensure we only detect phase if actual work is planned
    if total_planned_effort == 0:
         phase = "Planning & Backlog Refinement"
    elif dominant_type in ["backend", "frontend", "mobile"]:
        phase = "Core Feature Development"
    elif dominant_type in ["devops"]:
        phase = "Infrastructure & Release"
    elif dominant_type in ["designer"]:
        phase = "Design and Prototyping"
    else:
        phase = "Maintenance & Support"
        
    # Point 9: Sprint Health Score
    capacity_utilized = total_planned_effort / total_team_capacity if total_team_capacity > 0 else 0
    avg_reliability = sum(m.reliability for m in members) / len(members) if members else 1.0
    health_score = round(capacity_utilized * avg_reliability * 10, 2) # Score out of 10

    # FIX 5: Compacted Decision Log
    compacted_log = [
        f"Assignment complete: {len(final_sprint_tasks)} tasks assigned.",
        f"{len(rolled_over_tasks)} tasks rolled over due to capacity/limits."
    ]
    if debug_mode:
        compacted_log.extend(decision_log)

    sprint_data = {
        "sprintName": sprint_name,
        "projectId": project_id,
        "startDate": sprint_start.date().isoformat(),
        "endDate": sprint_end.date().isoformat(),
        "tasks": final_sprint_tasks, 
        "assignedMembers": assigned_members_list, 
        "plannedBy": "SprintPlannerAgent",
        "velocity": round(total_planned_effort, 1),
        "status": "Planned",
        "goals": [],
        "phase": phase, # Point 4
        "sprintHealthScore": health_score, # Point 9
        "meta": {
            "decisionLog": compacted_log,
            "assignmentReasons": assignment_reasons_log, # Point 6
            "rolledOverTasks": [t.model_dump() for t in rolled_over_tasks],
            "workloadDifficulty": {k: round(v, 1) for k, v in workload_difficulty.items()}, # Point 7
            "reliabilityImpact": reliability_impact, # Point 8
            "memberCapacity": {
                m._id: {
                    "total": member_total_capacity.get(m._id, {}).get("total", 0.0),
                    "remaining": member_remaining_capacity.get(m._id, 0.0),
                    "assignedTasks": member_task_count.get(m._id, 0),
                    "maxTasks": member_total_capacity.get(m._id, {}).get("max_tasks", 0)
                } for m in members
            },
            "reliabilityHistory": {m._id: member_reliability_history[m._id] for m in members}
        }
    }

    # AI SUMMARY (Runs asynchronously)
    try:
        # Pass the list of assigned task data (dictionaries) to the summarizer
        ai_data = await generate_sprint_summary(final_sprint_tasks)
        sprint_data.update(ai_data)
    except Exception as e:
        sprint_data["aiSummary"] = f"AI summary unavailable: {e}"

    return sprint_data