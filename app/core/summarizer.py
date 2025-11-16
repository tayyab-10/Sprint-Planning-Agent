import json
import asyncio
import os
from typing import List, Dict, Any

# Ensure 'requests' is imported for the synchronous call in the background thread
try:
    import requests
except ImportError:
    # Handle the case where requests might not be installed (for environment checks)
    print("Warning: 'requests' library not found. AI summary will use fallback.")

# Define constants for the Gemini API call
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# ------------------------------------------------------
# Diverse Fallback Goals
# ------------------------------------------------------
# FIX: Use diverse, categorized fallbacks to avoid repetition (Point 3)
FALLBACK_GOALS = [
    # Delivery Goals
    "Finalize and merge all code for high-priority features (Delivery Goal).",
    "Complete the implementation of the primary backend ingestion API (Delivery Goal).",
    # Quality Goals
    "Achieve 100% unit test coverage for all newly implemented features (Quality Goal).",
    "Resolve all identified P1 and P2 bugs from the current backlog (Quality Goal).",
    # Risk/Dependency Goals
    "Validate and document the finalized API specification with the consuming frontend team (Risk/Dependency Goal).",
    "Set up the foundational CI/CD pipeline to de-risk future deployments (Risk/Dependency Goal)."
]


# --- Exponential Backoff Helper (Crucial for robust API calls) ---

async def fetch_with_retry(url, payload, headers, max_retries=3):
    """Fetches API response with exponential backoff."""
    delay = 1
    for attempt in range(max_retries):
        try:
            # We use asyncio.to_thread to run the blocking 'requests.post' call asynchronously
            response = await asyncio.to_thread(
                lambda: requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                # Log error on final failure
                print(f"Final API call failed after {max_retries} retries: {e}")
                raise
            await asyncio.sleep(delay)
            delay *= 2
            
# --- Core Generation Function ---

async def generate_sprint_summary(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates AI Summary, Confidence, and SMART Goals using Gemini API, 
    with dynamic goal counting based on sprint size and category.
    """
    
    # 1. Determine dynamic goal count and sprint type
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

    # Define a clean fallback that uses the dynamically set variables
    fallback = {
        "aiSummary": f"This is a {sprint_type} with {total_tasks} tasks. Team should prioritize efficiency and alignment.",
        "aiConfidence": 0.0, # Point 1: Fallback remains 0.0 when AI fails completely
        "goals": FALLBACK_GOALS[:goal_count]
    }
    
    if 'requests' not in globals() or not tasks:
        return fallback
        
    # 2. Create clean task data for the LLM prompt
    clean_task_data = [
        {
            "title": t.get('title'),
            "type": t.get('type', 'N/A'),
            "effort": f"{t.get('estimatedHours', 8.0)}h",
            "assignedTo": t.get('assignedTo')
        }
        for t in tasks
    ]
    
    # Point 5 & 3: Enhanced prompt for better summary and categorized goals
    user_query = f"""
    Analyze the following {sprint_type} tasks planned for the sprint (Total tasks: {total_tasks}).

    Generate:
    1. A concise, professional **Summary** (1-2 sentences) of the sprint's focus, emphasizing the *value* being delivered and the primary technical area (e.g., "backend API foundations").
    2. Exactly {goal_count} **SMART Goals**. These must be categorized as: Delivery Goal, Quality Goal, or Risk/Dependency Goal.
    3. An objective **Confidence Score** (0.0 to 1.0) on the plan's achievability.

    Tasks:
    {json.dumps(clean_task_data, indent=2)}

    Your response MUST contain ONLY the JSON object and no commentary.
    """
    
    # 3. Define System Instruction and Structured Output Schema
    system_prompt = "You are an expert Agile Coach and AI Sprint Planner. Your job is to analyze the assigned tasks for a sprint and generate an insightful summary, categorized SMART goals, and an objective confidence score for the plan. Respond STRICTLY in JSON."
    
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "aiSummary": {"type": "STRING", "description": "A concise, professional summary of the sprint's focus and delivered value (1-2 sentences)."},
            "aiConfidence": {"type": "NUMBER", "description": "Confidence score (0.0 to 1.0) reflecting the perceived success of completing all tasks."},
            "goals": {
                "type": "ARRAY",
                "description": f"Exactly {goal_count} specific, measurable, and categorized SMART goals (Delivery, Quality, Risk/Dependency).",
                "items": {"type": "STRING"}
            }
        },
        "required": ["aiSummary", "aiConfidence", "goals"]
    }

    payload = {
        "contents": [{ "parts": [{ "text": user_query }] }],
        "systemInstruction": { "parts": [{ "text": system_prompt }] },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }
    }
    
    headers = { 'Content-Type': 'application/json' }
    
    # 4. API Call and Parsing
    try:
        result = await fetch_with_retry(API_URL, payload, headers)

        candidate = result.get('candidates', [{}])[0]
        json_text = candidate.get('content', {}).get('parts', [{}])[0].get('text')
        
        if json_text:
            if json_text.strip().startswith("```json"):
                json_text = json_text.strip().lstrip("```json").rstrip("```")
                
            ai_data = json.loads(json_text)
            ai_data['aiConfidence'] = float(ai_data.get('aiConfidence', 0.5))
            
            # FIX: If the AI failed to hit the exact goal count, use the diverse fallback goals
            if len(ai_data.get("goals", [])) != goal_count:
                ai_data["goals"] = FALLBACK_GOALS[:goal_count] 
            
            # Point 1: If AI generated a summary, we use its confidence (0.0 < confidence <= 1.0)
            return ai_data
        
    except Exception as e:
        print(f"Gemini API call failed or JSON parsing failed: {e}")
        return fallback # Return diverse fallback on API or parsing error
        
    return fallback