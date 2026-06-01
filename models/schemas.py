from pydantic import BaseModel, Field
from typing import Optional


class ErrorQuery(BaseModel):
    error_text: str = Field(..., description="Error text extracted from screenshot")


class ErrorResponse(BaseModel):
    id: str
    error_text: str
    solution: str
    sources: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class Feedback(BaseModel):
    response_id: str
    rating: int = Field(..., ge=0, le=1, description="0 for thumbs down, 1 for thumbs up")


class ChatMessage(BaseModel):
    role: str
    content: str


class AgentState(BaseModel):
    error_text: str = ""
    retrieved_docs: list[dict] = Field(default_factory=list)
    solution: str = ""
    arm_selected: Optional[int] = None
