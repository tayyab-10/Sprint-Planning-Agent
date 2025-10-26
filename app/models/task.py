from pydantic import BaseModel, Field
from typing import List, Optional


class Task(BaseModel):
    # Use `id` as the real field name and accept incoming `_id` via alias.
    id: str = Field(..., alias="_id")
    title: str
    priority: str
    status: str
    assignedTo: Optional[str]
    dueDate: Optional[str] = None   # ✅ use dueDate instead of deadlineDays
    estimatedHours: float = 4.0
    queueOrder: Optional[int] = 0
    businessValue: Optional[int] = 1
    dependencies: Optional[List[str]] = Field(default_factory=list)
    score: Optional[float] = None  # computed by scorer

    class Config:
        allow_population_by_field_name = True

    @property
    def _id(self) -> str:
        return self.id
