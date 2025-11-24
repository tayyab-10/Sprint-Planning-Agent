from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date

# --- 1. Nested Output Models for Capacity, Risk, and Planning ---

class MemberCapacityOutput(BaseModel):
    """Details the effective capacity for a single member."""
    projectMemberId: str
    effectiveHours: float

class CapacityOutput(BaseModel):
    """Represents the total team capacity."""
    totalCapacityHours: float
    memberCapacities: List[MemberCapacityOutput]

class RiskAnalysisOutput(BaseModel):
    """Represents the calculated risks for the sprint."""
    delayRiskPercent: float
    overloadedMembers: List[str]
    criticalDependencies: List[str]
    deadlineThreats: List[str]

# --- 2. Nested Output Models for New KPIs and Fairness ---

class BurndownForecastItem(BaseModel):
    """Represents one point in the burndown chart forecast."""
    date: str
    remainingHours: float

class FairnessReportItem(BaseModel):
    """Exposes a member's fairness score and calculated share of effort."""
    projectMemberId: str
    fairnessScore: Optional[float]
    normalizedShare: Optional[float]
    fairShareHours: Optional[float]
    plannedHours: float
    overloadFlag: bool

class MemberWorkloadSummaryItem(BaseModel):
    """Summary of planned workload per member."""
    memberId: str
    taskCount: int
    totalEstimatedHours: float
    totalStoryPoints: float

# --- 3. Planning Decision Models (Updated with Member Details) ---

class AssignedMemberDetailsOutput(BaseModel):
    """
    Combines core ProjectMember fields with planning metrics and rich user details (avatar, email)
    captured from the API response's assignedTo field.
    """
    projectMemberId: str
    name: Optional[str]
    role: Optional[str]
    reliabilityScore: Optional[float]
    effectiveCapacity: Optional[float]
    currentLoad: Optional[float]
    fairShareHours: Optional[float]
    fairnessScore: Optional[float]
    
    # Rich details from the original assignedTo field (e.g., avatar, email)
    userId: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[Dict[str, Any]] = None

class SelectedTaskOutput(BaseModel):
    """Represents a task selected for the sprint."""
    taskId: str
    estimatedHours: float
    assignedTo: str # The ProjectMemberId
    reason: str
    assignedMemberDetails: AssignedMemberDetailsOutput # NEW

class DeferredTaskOutput(BaseModel):
    """Represents a task that was not included in the sprint."""
    taskId: str
    reason: str
    # Note: Deferred tasks do not need assignedMemberDetails as they were not selected

# --- 4. Main Sprint Plan Output ---

class SprintPlanOutput(BaseModel):
    """
    The complete, structured output payload matching the Agent's Final Plan contract,
    including all new KPIs and Fairness metrics.
    """
    success: bool = Field(True, description="Always true if planning was completed successfully.")
    sprintId: str = Field(..., description="Unique ID for the planned sprint.")
    summary: str = Field(..., description="A concise AI-generated summary of the sprint plan.")
    
    # Core Planning Data
    capacity: CapacityOutput
    riskAnalysis: RiskAnalysisOutput
    recommendations: List[str] = Field(default_factory=list)
    selectedTasks: List[SelectedTaskOutput]
    deferredTasks: List[DeferredTaskOutput]
    
    # Core Sprint Context
    goals: List[str] = Field(default_factory=list)
    startDate: Optional[str] = None # Using str for ISO format from planner.py
    endDate: Optional[str] = None   # Using str for ISO format from planner.py
    project: Optional[str] = None
    status: str = Field(default="Planned")
    plannedBy: str = Field(default="SprintPlannerAgent")
    
    # AI/KPI Metrics (NEW)
    aiSummary: Optional[str] = None
    aiConfidence: Optional[float] = None
    predictedVelocity: Optional[float] = Field(None, description="Weighted, predicted velocity score for the sprint.")
    sprintRiskScore: Optional[float] = Field(None, description="Overall risk score (0-100) combining deferred, dependency, and overload factors.")
    
    # Detailed Planning/Tracking Metrics (NEW)
    assignmentStrategy: str
    totalEffort: float = Field(..., description="Total estimated hours of all tasks selected for the sprint.")
    
    # Reports (NEW)
    burndownForecast: List[BurndownForecastItem] = Field(default_factory=list)
    fairnessReport: List[FairnessReportItem] = Field(default_factory=list)
    memberWorkloadSummary: List[MemberWorkloadSummaryItem] = Field(default_factory=list)
    
    # Legacy/Optional fields
    velocity: Optional[float] = None