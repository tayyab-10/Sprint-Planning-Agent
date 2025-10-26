from pydantic import BaseModel, Field
from typing import Optional


class ProjectMember(BaseModel):
    """Project member model. Exposes a compatibility `._id` property while
    using `id` as the real field name (aliases incoming `_id` JSON).
    """

    id: str = Field(..., alias="_id")
    name: Optional[str]
    role: str
    availabilityPct: float = 1.0
    hourlyCapacity: float = 40.0
    velocity: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True

    @property
    def _id(self) -> str:
        return self.id
