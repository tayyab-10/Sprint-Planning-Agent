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
    Asynchronously generate a 3–4 line sprint summary using Gemini AI.
    Always returns immediately if Gemini API fails, avoiding blocking loops.
    """
    # Prepare list of task titles
    task_titles = [getattr(t, "title", str(t)) for t in tasks]
    top_titles = ", ".join(task_titles[:5]) or "general tasks"

    # Predefine fallback in case Gemini fails or is disabled
    fallback = {
        "aiSummary": f"Sprint includes top tasks: {top_titles}. Focus on completing high-priority items and resolving blockers.",
        "aiConfidence": 0.0
    }

    # If no Gemini API key, immediately return fallback
    if not GEMINI_API_KEY:
        logger.debug("GEMINI_API_KEY missing. Returning fallback summary.")
        return fallback

    try:
        # Prepare prompt (keep it small and efficient)
        task_list = "\n".join([f"- {t}" for t in task_titles[:10]])
        prompt = f"""
        You are an expert Agile Sprint Planner AI.
        Given these tasks for the sprint:
        {task_list}

        Generate a concise 3–4 line summary covering:
        - Sprint focus
        - Type of work being prioritized
        - Any key dependencies or goals
        """

        # Run Gemini call in a background thread to avoid blocking FastAPI event loop
        loop = asyncio.get_event_loop()
        summary_text = await loop.run_in_executor(None, _call_gemini, prompt)

        if not summary_text:
            logger.warning("Gemini returned empty response; using fallback.")
            return fallback

        return {"aiSummary": summary_text.strip(), "aiConfidence": 0.9}

    except Exception as e:
        logger.error(f"❌ [AI ERROR] Gemini summary failed: {e}")
        logger.debug(traceback.format_exc())
        return fallback


def _call_gemini(prompt: str) -> str:
    """
    Safe, synchronous Gemini API call run in executor (thread).
    Prevents blocking the main async FastAPI loop.
    """
    try:
        # ✅ Choose a stable, supported Gemini model
        model = genai.GenerativeModel("gemini-2.5-flash")  # fast & reliable
        response = model.generate_content(prompt)

        # Extract output safely
        text = getattr(response, "text", None)
        return text or ""
    except Exception as e:
        print(f"❌ [Gemini API ERROR in thread]: {e}")
        return ""
