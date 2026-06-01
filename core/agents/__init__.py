from core.agents.orchestrator import OrchestratorAgent
from core.agents.vision import VisionAgent
from core.agents.classifier import ClassifierAgent
from core.agents.knowledge import KnowledgeAgent
from core.agents.researcher import ResearchAgent
from core.agents.code_agent import CodeAgent
from core.agents.solver import SolverAgent
from core.agents.guardian import GuardianAgent
from core.agents.validator import ValidatorAgent
from core.agents.learner import LearnerAgent

AGENT_CLASSES = {
    "orchestrator": OrchestratorAgent,
    "vision": VisionAgent,
    "classifier": ClassifierAgent,
    "knowledge": KnowledgeAgent,
    "research": ResearchAgent,
    "code_agent": CodeAgent,
    "solver": SolverAgent,
    "guardian": GuardianAgent,
    "validator": ValidatorAgent,
    "learner": LearnerAgent,
}


def create_agent(agent_name: str, config=None, providers=None):
    cls = AGENT_CLASSES.get(agent_name)
    if cls is None:
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENT_CLASSES.keys())}")
    return cls(config=config, providers=providers)


__all__ = [
    "OrchestratorAgent", "VisionAgent", "ClassifierAgent",
    "KnowledgeAgent", "ResearchAgent", "CodeAgent",
    "SolverAgent", "GuardianAgent", "ValidatorAgent",
    "LearnerAgent", "create_agent", "AGENT_CLASSES",
]
