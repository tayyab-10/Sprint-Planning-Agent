from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import date

class ProjectMember(BaseModel):
    """
    Revised Project Member Model: Captures all performance, capacity, and
    reliability metrics required by the Sprint Planner Agent for calculation.
    """
    # 1. Primary Identifiers
    projectMemberId: str = Field(..., alias="_id") # Use the explicit ID name, alias the common '_id'
    name: Optional[str] = None
    role: str

    # 2. Capacity & Availability Factors (Used for Step 1: Capacity Calculation)
    baseWeeklyHours: float = Field(40.0, description="Standard work hours per week.")
    unavailableDates: List[date] = Field(default_factory=list, description="Dates member is fully unavailable.")
    
    # Renamed/Aliased availability factor
    availabilityFactor: float = Field(1.0, alias="availabilityPct", description="Percentage of base time available.")
    
    skillEfficiencyMultiplier: float = Field(1.0, description="Factor for skill level.")
    
    # 3. Performance & Risk Scores
    reliabilityScore: float = Field(0.7, description="Historical metric of task completion (0.0 to 1.0).")
    reliabilityTier: Optional[str] = None
    overloadRiskScore: float = Field(0.0, description="Current risk of overload (0.0 to 1.0).")
    recentWeightedScore: Optional[float] = None
    
    # 4. Agent Calculation Fields (Internal use)
    velocity: Optional[int] = 0
    sprintCapacityHours: Optional[float] = None # Calculated during planning (Effective Capacity)
    effective_max_tasks: int = 0             # Calculated during planning
    assigned_effort: float = 0.0             # Tracks current load

    class Config:
        # Allows ProjectMember(reliabilityPct=0.8) or ProjectMember(availabilityFactor=0.8)
        populate_by_name = True 
        
    # NOTE: The custom @property for _id is now redundant if you rely on the alias 
    # and use the ProjectMemberId field directly in your planner logic.