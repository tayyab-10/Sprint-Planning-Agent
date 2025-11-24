from typing import Any
from app.core import planner_engine

# Compatibility wrapper: expose plan_single_sprint and accept extra kwargs
async def plan_single_sprint(project_id: str, members: Any, tasks: Any, sprint_config: dict, **kwargs):
    return await planner_engine.plan_single_sprint(project_id, members, tasks, sprint_config, **kwargs)
