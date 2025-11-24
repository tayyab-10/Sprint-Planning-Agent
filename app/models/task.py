from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Any, Dict
from datetime import date, datetime

class Task(BaseModel):
    """
    Model for a Task. Uses a validator to handle nested fields from Task Generator output.
    """
    taskId: str = Field(..., alias="_id")
    title: str
    description: Optional[str] = None
    estimatedHours: float = Field(8.0, description="The estimated effort in hours.")
    priority: str = Field("Medium", description="High, Medium, or Low.")
    status: str = Field("Backlog", description="Current status of the task.")
    
    # Crucial field: Use the explicit ProjectMemberId, not the complex assignedTo object
    assignedTo: Optional[str] = Field(None, alias="assignedPrimaryProjectMemberId", description="The assigned ProjectMemberId.")
    
    dependencies: List[str] = Field(default_factory=list, description="List of TaskIds that must be completed first.")
    epicId: Optional[str] = Field(None, alias="epic")
    userStoryId: Optional[str] = Field(None, alias="userStory")
    phaseId: Optional[str] = Field(None, alias="phase")
    deadline: Optional[date] = None # Use Python date object for easy comparison
    complexityScore: Optional[float] = None
    
    # Custom attributes for internal use in planner
    eligible: bool = False
    eligibility_reason: str = "Unprocessed"
    # Raw assignee/user details (keeps both projectMemberId and user details)
    assigneeDetails: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    @model_validator(mode='before')
    @classmethod
    def extract_nested_fields(cls, data: Any) -> Any:
        """Flattens the 'agentMeta' and extracts specific assignment IDs."""
        if isinstance(data, dict):
            # 1. Promote fields from agentMeta to the root if they aren't already present
            if 'agentMeta' in data and isinstance(data['agentMeta'], dict):
                meta = data.pop('agentMeta')
                for key, value in meta.items():
                    # Only promote if root doesn't have a value OR the model field name is different
                    if data.get(key) is None: 
                        data[key] = value
            
            # 2. Extract the critical assignedPrimaryProjectMemberId
            if data.get('assignedPrimaryProjectMemberId') is None:
                 if 'assignedPrimary' in data and isinstance(data['assignedPrimary'], dict):
                    # NOTE: This assumes 'assignedPrimary' is the user object, not the ProjectMemberId.
                    # We must use the explicit 'assignedPrimaryProjectMemberId' which seems to be the ID you need.
                    pass 
            
            # 3. Handle deadline date conversion
            if isinstance(data.get('deadline'), str):
                try:
                    data['deadline'] = datetime.strptime(data['deadline'].split('T')[0], "%Y-%m-%d").date()
                except ValueError:
                    data['deadline'] = None
                    
        return data

    @field_validator('estimatedHours', mode='before')
    @classmethod
    def convert_estimated_hours(cls, v):
        """Ensure estimatedHours is a float."""
        try:
            return float(v)
        except (ValueError, TypeError):
            return 8.0 # Default if conversion fails