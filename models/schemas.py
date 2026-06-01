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
    web_results: list[dict] = Field(default_factory=list)
    solution: str = ""
    arm_selected: Optional[int] = None
    arm_config: dict = Field(default_factory=dict)
    guardrails_passed: bool = True
    guardrail_message: str = ""
    error: str = ""


class AgentResult(BaseModel):
    agent_name: str = ""
    success: bool = True
    content: str = ""
    data: dict = Field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0
    tokens_used: int = 0


class OrchestratorPlan(BaseModel):
    steps: list[dict] = Field(default_factory=list)
    parallel_groups: list[list[str]] = Field(default_factory=list)
    workflow_mode: str = "sequential"
    metadata: dict = Field(default_factory=dict)


class VisionOutput(BaseModel):
    extracted_text: str = ""
    confidence: float = 0.0
    has_error: bool = False
    raw_response: str = ""


class ClassificationOutput(BaseModel):
    error_type: str = "unknown"
    language: str = "unknown"
    severity: str = "unknown"
    keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class KnowledgeOutput(BaseModel):
    docs: list[dict] = Field(default_factory=list)
    context: str = ""
    total_found: int = 0
    collection: str = ""


class ResearchOutput(BaseModel):
    results: list[dict] = Field(default_factory=list)
    total_sources: int = 0
    cached: bool = False


class CodeAnalysisOutput(BaseModel):
    relevant_files: list[str] = Field(default_factory=list)
    code_snippets: list[dict] = Field(default_factory=list)
    project_context: str = ""
    framework: str = ""


class GuardianOutput(BaseModel):
    passed: bool = True
    sanitized_text: str = ""
    warnings: list[str] = Field(default_factory=list)
    redacted: bool = False


class ValidatorOutput(BaseModel):
    valid: bool = True
    syntax_ok: bool = True
    completeness_score: float = 1.0
    suggestions: list[str] = Field(default_factory=list)


class SolverOutput(BaseModel):
    solution: str = ""
    diffs: list[dict] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class LearnerOutput(BaseModel):
    arm_updated: bool = False
    arm_selected: int = 0
    feedback_processed: bool = False
    rag_updated: bool = False
    bandit_stats: dict = Field(default_factory=dict)
