import json
import asyncio
import os
from typing import List, Dict, Any
from datetime import date, timedelta

try:
    import requests
except ImportError:
    print("Warning: 'requests' library not found. AI summary will use fallback.")

from app.core.scorer import compute_task_score

MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

FALLBACK_GOALS = [
    "Finalize and merge all code for high-priority features (Delivery Goal).",
    "Complete the implementation of the primary backend ingestion API (Delivery Goal).",
    "Achieve 100% unit test coverage for all newly implemented features (Quality Goal).",
    "Resolve all identified P1 and P2 bugs from the current backlog (Quality Goal).",
    "Validate and document the finalized API specification with the consuming frontend team (Risk/Dependency Goal).",
    "Set up the foundational CI/CD pipeline to de-risk future deployments (Risk/Dependency Goal)."
]

DEFAULT_SPRINT_DAYS = 14
DEADLINE_URGENCY_DAYS = 5


async def fetch_with_retry(url, payload, headers, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                lambda: requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Final API call failed after {max_retries} retries: {e}")
                raise
            await asyncio.sleep(delay)
            delay *= 2


async def generate_sprint_summary(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_tasks = len(tasks)

    if total_tasks <= 3:
        goal_count = 2
        sprint_type = "light sprint focused on quick wins"
    elif total_tasks <= 8:
        goal_count = 3
        sprint_type = "balanced sprint focusing on key deliverables"
    else:
        goal_count = 5
        sprint_type = "intensive sprint addressing complex objectives"

    # Compute per-task scores, velocity and deadlines
    clean_task_data = []
    total_effort = 0.0
    scores = []
    selected_task_ids = set()
    deadlines = []

    for t in tasks:
        # ensure safe access for dicts or Pydantic models
        if isinstance(t, dict):
            est = float(t.get('estimatedHours', t.get('effort', 8.0) or 8.0))
            tid = t.get('taskId') or t.get('_id')
        else:
            est = float(getattr(t, 'estimatedHours', 8.0) or 8.0)
            tid = getattr(t, 'taskId', None)

        score = compute_task_score(t)
        scores.append(score)
        total_effort += est
        selected_task_ids.add(tid)

        # collect deadlines
        d = None
        if isinstance(t, dict):
            d = t.get('deadline')
        else:
            d = getattr(t, 'deadline', None)

        if isinstance(d, str):
            try:
                deadlines.append(date.fromisoformat(d.split('T')[0]))
            except Exception:
                pass
        elif isinstance(d, date):
            deadlines.append(d)

        clean_task_data.append({
            "taskId": tid,
            "title": t.get('title') if isinstance(t, dict) else getattr(t, 'title', None),
            "type": t.get('type', 'Other') if isinstance(t, dict) else getattr(t, 'type', 'Other'),
            "priority": t.get('priority', 'Medium') if isinstance(t, dict) else getattr(t, 'priority', 'Medium'),
            "estimatedHours": est,
            "score": score,
            "assignedTo": t.get('assignedTo') if isinstance(t, dict) else getattr(t, 'assignedTo', None),
            "dependencies": t.get('dependencies', []) if isinstance(t, dict) else getattr(t, 'dependencies', [])
        })

    # Basic derived fields
    velocity = round(total_effort, 1)
    avg_score = sum(scores) / len(scores) if scores else 0.0
    ai_confidence = round(min(1.0, (avg_score / 10.0)), 2)

    start_date = date.today()
    if deadlines:
        end_date = max(deadlines)
        # Ensure end_date is at least start_date + DEFAULT_SPRINT_DAYS
        min_end = start_date + timedelta(days=DEFAULT_SPRINT_DAYS)
        if end_date < min_end:
            end_date = min_end
    else:
        end_date = start_date + timedelta(days=DEFAULT_SPRINT_DAYS)

    # Risk analysis (simple heuristics)
    overdue = [c['taskId'] for c in clean_task_data if isinstance(c.get('estimatedHours'), (int, float)) and False]
    # Deadline threats: tasks with deadline within DEADLINE_URGENCY_DAYS
    deadline_threats = []
    for i, d in enumerate(deadlines):
        days_left = (d - start_date).days
        if days_left < 0:
            deadline_threats.append(clean_task_data[i]['taskId'])
        elif days_left <= DEADLINE_URGENCY_DAYS:
            deadline_threats.append(clean_task_data[i]['taskId'])

    # Critical dependencies: dependencies that are not present in the selected tasks list
    critical_dependencies = []
    for c in clean_task_data:
        for dep in c.get('dependencies', []):
            if dep not in selected_task_ids:
                critical_dependencies.append(dep)

    delayRiskPercent = 0
    if velocity > 0:
        # rudimentary risk: more effort -> higher delay risk in absence of capacity info
        delayRiskPercent = min(100, int((velocity / max(1.0, velocity + 20.0)) * 100 * 0.8))

    risk_analysis = {
        "delayRiskPercent": delayRiskPercent,
        "overloadedMembers": [],
        "criticalDependencies": list(set(critical_dependencies)),
        "deadlineThreats": list(set(deadline_threats))
    }

    fallback = {
        "aiSummary": f"This is a {sprint_type} with {total_tasks} tasks. Team should prioritize efficiency and alignment.",
        "aiConfidence": ai_confidence,
        "goals": FALLBACK_GOALS[:goal_count],
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "project": None,
        "velocity": velocity,
        "riskAnalysis": risk_analysis
    }

    # If requests not available or no tasks, return fallback enriched with computed fields
    if 'requests' not in globals() or not tasks:
        return fallback

    # Re-read GEMINI API key at call-time so changes in the environment are picked up
    api_key = os.getenv("GEMINI_API_KEY")
    # Fallback: if not set in environment, try to read from a local .env file in project root
    if not api_key:
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('GEMINI_API_KEY='):
                            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
        except Exception:
            pass
    if not api_key:
        print("Gemini API key not configured (GEMINI_API_KEY); using fallback summary.")
        return fallback

    # Build the API URL using the runtime key
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"

    # Build API prompt payload
    user_query = f"""
    Analyze the following {sprint_type} tasks planned for the sprint (Total tasks: {total_tasks}).

    Generate:
    1. A concise, professional Summary (1-2 sentences) of the sprint's focus, emphasizing value, team assignment, and key dependencies.
    2. Exactly {goal_count} SMART Goals. Categorize each as: Delivery Goal, Quality Goal, or Risk/Dependency Goal.
    3. An objective Confidence Score (0.0 to 1.0) reflecting task prioritization, effort, and dependencies.

    Tasks (including scores, member IDs, and dependencies):
    {json.dumps(clean_task_data, indent=2)}

    Respond strictly in JSON format with fields: aiSummary, aiConfidence, goals.
    """

    system_prompt = "You are an expert Agile Coach and AI Sprint Planner. Analyze the assigned tasks for a sprint considering task score, assigned member, dependencies, priority, and effort. Generate an insightful summary, categorized SMART goals, and an objective confidence score. Respond strictly in JSON."

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"responseMimeType": "application/json"}
    }

    headers = {'Content-Type': 'application/json'}

    try:
        # Use the runtime URL constructed with the live API key (avoid import-time cached URL)
        if not api_url or api_url.endswith("=None"):
            print("Gemini API key missing or invalid at call-time; aborting remote call.")
            return fallback

        # Masked debug: do not print the full key
        print(f"Calling Gemini API with key present; endpoint={api_url.split('?')[0]}")

        result = await fetch_with_retry(api_url, payload, headers)
        candidate = result.get('candidates', [{}])[0]
        json_text = candidate.get('content', {}).get('parts', [{}])[0].get('text')

        if json_text:
            if json_text.strip().startswith("```json"):
                json_text = json_text.strip().lstrip("```json").rstrip("```")
            ai_data = json.loads(json_text)

            # Ensure required structure and merge computed fields
            ai_data['aiConfidence'] = float(ai_data.get('aiConfidence', ai_confidence))
            # Normalize goals to simple strings to satisfy downstream Pydantic models
            raw_goals = ai_data.get('goals', [])
            normalized_goals = []
            for g in raw_goals:
                if isinstance(g, str):
                    normalized_goals.append(g)
                elif isinstance(g, dict):
                    # Attempt to extract common fields from structured goal objects
                    text = g.get('text') or g.get('goal') or g.get('summary') or g.get('description')
                    category = g.get('category')
                    if text and category:
                        normalized_goals.append(f"{text} ({category})")
                    elif text:
                        normalized_goals.append(text)
                    else:
                        # Fallback: stringify the dict
                        try:
                            normalized_goals.append(json.dumps(g))
                        except Exception:
                            normalized_goals.append(str(g))
                else:
                    try:
                        normalized_goals.append(str(g))
                    except Exception:
                        normalized_goals.append('')

            if len(normalized_goals) != goal_count:
                ai_data['goals'] = FALLBACK_GOALS[:goal_count]
            else:
                ai_data['goals'] = normalized_goals

            # Attach computed fields if missing
            ai_data.setdefault('startDate', fallback['startDate'])
            ai_data.setdefault('endDate', fallback['endDate'])
            ai_data.setdefault('project', fallback['project'])
            ai_data.setdefault('velocity', fallback['velocity'])
            ai_data.setdefault('riskAnalysis', fallback['riskAnalysis'])

            return ai_data

    except Exception as e:
        print(f"Gemini API call failed or JSON parsing failed: {e}")
        return fallback

    return fallback
