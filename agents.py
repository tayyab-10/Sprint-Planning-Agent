
from typing import List, Dict
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class TaskAnalyzerAgent:
    """
    Analyzes project description and extracts potential task components.
    """
    def analyze_description(self, description: str) -> List[str]:
        prompt = f"Break down the following project description into actionable tasks:\n\n{description}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content.strip().split('\n')

class SprintAllocatorAgent:
    """
    Allocates tasks into sprints based on size/priority.
    """
    def allocate_to_sprints(self, tasks: List[str]) -> Dict[str, List[str]]:
        prompt = f"Distribute the following tasks into two sprints based on size and priority:\n{tasks}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": str(prompt)}],
            temperature=0.5,
            max_tokens=500
        )
        return {
            "Sprint 1": [],
            "Sprint 2": [],
            "Raw": response.choices[0].message.content.strip()
        }

class AcceptanceCriteriaAgent:
    """
    Generates acceptance criteria for each task.
    """
    def generate_criteria(self, task: str) -> List[str]:
        prompt = f"Write 2 acceptance criteria for the following task:\n\n{task}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300
        )
        return response.choices[0].message.content.strip().split('\n')
