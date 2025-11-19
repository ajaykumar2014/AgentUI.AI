from pydantic import BaseModel, Field
from typing import Any, Dict

class ToolInfo(BaseModel):
    name: str
    description: str
    endpoint: str
    method: str = "POST"

class InvokeRequest(BaseModel):
    tool: str = Field(..., description="Tool name to invoke")
    params: Dict[str, Any] = Field(default_factory=dict)
