from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class Sprint(BaseModel):
    """Pydantic model matching the Node/Mongoose `Sprint` schema.

    Fields mirror the schema provided by the user. This model is suitable for
    validation and serialization when interacting with the Node backend.
    """

    name: str = Field(..., description="Sprint name")
    startDate: date
    endDate: date
    project: str = Field(..., description="Project ObjectId (as string)")
    plannedBy: str = Field(default="SprintPlannerAgent")
    aiSummary: Optional[str] = None
    aiConfidence: Optional[float] = None
    velocity: Optional[float] = None
    status: str = Field(default="Planned", description="One of: Planned, Active, Completed")
    goals: List[str] = Field(default_factory=list)

