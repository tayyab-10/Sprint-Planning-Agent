from pydantic import BaseModel, Field
from typing import List, Optional, Union


class Avatar(BaseModel):
    public_id: Optional[str] = ""
    url: Optional[str] = ""


class AssignedUser(BaseModel):
    _id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    avatar: Optional[Avatar] = None


class Task(BaseModel):
    # Use `id` as the real field name and accept incoming `_id` via alias.
    id: str = Field(..., alias="_id")
    title: str
    priority: str
    status: str
    # ✅ Fix: Allow either user ID (string) or full user object
    assignedTo: Optional[Union[str, AssignedUser]] = None

    dueDate: Optional[str] = None
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

    def model_dump(self, **kwargs):
        """Safe dump to ensure assignedTo is always an ID string."""
        base = super().model_dump(by_alias=True, **kwargs)
        assigned = base.get("assignedTo")

        # If assignedTo is a nested object, extract the ID
        if isinstance(assigned, dict):
            base["assignedTo"] = assigned.get("_id") or None
        elif hasattr(self.assignedTo, "_id"):
            base["assignedTo"] = self.assignedTo._id
        return base
