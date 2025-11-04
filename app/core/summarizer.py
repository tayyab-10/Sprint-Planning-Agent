import os
import logging
import traceback
import asyncio
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Load Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY not set. AI summaries will use fallback.")
else:
    genai.configure(api_key=GEMINI_API_KEY)


async def generate_sprint_summary(tasks):
    """
    Dynamically generates a sprint summary and goals using Gemini AI.
    Adapts tone, goal count, and focus based on the number and nature of tasks.
    """
    task_titles = [getattr(t, "title", str(t)) for t in tasks]
    total_tasks = len(task_titles)
    top_titles = ", ".join(task_titles[:5]) or "general tasks"

    # ✅ Determine tone and goal count based on sprint size
    if total_tasks <= 3:
        goal_count = 2
        sprint_type = "light sprint focused on quick wins"
    elif total_tasks <= 8:
        goal_count = 3
        sprint_type = "balanced sprint focusing on key deliverables"
    else:
        goal_count = 5
        sprint_type = "intensive sprint addressing complex objectives"

    # ✅ Default fallback (used when AI fails)
    fallback = {
        "aiSummary": f"This is a {sprint_type}. Tasks include: {top_titles}. Team should prioritize efficiency and alignment.",
        "aiConfidence": 0.0,
        "goals": [
            "Complete high-priority tasks efficiently",
            "Ensure code quality and testing coverage",
            "Maintain strong communication across the team"
        ][:goal_count]
    }

    if not GEMINI_API_KEY:
        logger.debug("GEMINI_API_KEY missing. Returning fallback summary.")
        return fallback

    try:
        # 🔹 Build dynamic prompt
        task_list = "\n".join([f"- {t}" for t in task_titles[:10]])
        prompt = f"""
        You are an expert Agile Sprint Planner AI.
        Analyze these sprint tasks:
        {task_list}

        Sprint Type: {sprint_type}
        Total Tasks: {total_tasks}

        Generate:
        1. A concise 3–4 line **summary** describing the sprint focus, work type, and dependencies.
        2. {goal_count} short and actionable **goals** (use bullet points).

        Format strictly as:

        SUMMARY:
        <summary text>

        GOALS:
        - goal 1
        - goal 2
        - goal 3 ...
        """

        # Run Gemini safely in a background thread
        loop = asyncio.get_event_loop()
        raw_text = await loop.run_in_executor(None, _call_gemini, prompt)

        if not raw_text:
            logger.warning("Gemini returned empty response; using fallback.")
            return fallback

        summary_text, goals = _parse_summary_and_goals(raw_text)

        # ✅ Ensure goals array has the expected length
        if not goals or len(goals) < goal_count:
            goals = fallback["goals"]

        return {
            "aiSummary": summary_text.strip() if summary_text else fallback["aiSummary"],
            "aiConfidence": 0.9 if summary_text else 0.0,
            "goals": goals
        }

    except Exception as e:
        logger.error(f"❌ [AI ERROR] Gemini summary failed: {e}")
        logger.debug(traceback.format_exc())
        return fallback


def _call_gemini(prompt: str) -> str:
    """
    Safe, synchronous Gemini API call run in executor (thread).
    Prevents blocking the main FastAPI loop.
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")  # ✅ stable, fast model
        response = model.generate_content(prompt)
        return getattr(response, "text", "") or ""
    except Exception as e:
        print(f"❌ [Gemini API ERROR in thread]: {e}")
        return ""


def _parse_summary_and_goals(text: str):
    """
    Parse summary and goals from Gemini's formatted text response.
    """
    summary_text = ""
    goals = []

    try:
        lines = text.splitlines()
        in_goals = False

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.upper().startswith("SUMMARY"):
                continue
            elif line.upper().startswith("GOALS"):
                in_goals = True
                continue
            elif in_goals and line.startswith("-"):
                goals.append(line.lstrip("-").strip())
            elif not in_goals:
                summary_text += line + " "

        summary_text = summary_text.strip()
    except Exception as e:
        print(f"⚠️ Failed to parse AI response: {e}")
    
    return summary_text, goals
