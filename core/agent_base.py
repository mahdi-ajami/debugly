from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from core.providers import ProviderManager
from core.session import StepEvent


AGENT_CONFIG_FIELDS = {"name", "enabled", "llm_model", "llm_provider", "temperature", "rag_collection", "max_retrieved_docs", "timeout_seconds"}


def _filter_config(d: dict) -> dict:
    return {k: v for k, v in d.items() if k in AGENT_CONFIG_FIELDS}


@dataclass
class AgentConfig:
    name: str = ""
    enabled: bool = True
    llm_model: str = ""
    llm_provider: str = "ollama"
    temperature: float = 0.3
    rag_collection: str = ""
    max_retrieved_docs: int = 3
    timeout_seconds: int = 60
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "AgentConfig":
        return cls(**_filter_config(d))


@dataclass
class AgentInput:
    query: str = ""
    context: str = ""
    images: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.query


@dataclass
class AgentOutput:
    success: bool = True
    content: str = ""
    data: dict = field(default_factory=dict)
    error: str = ""
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    def __init__(self, config: AgentConfig | None = None, providers: ProviderManager | None = None):
        self.config = config or AgentConfig()
        self.providers = providers or ProviderManager.load()
        self._tools: dict[str, Any] = {}
        self._memory: list[dict] = []
        self._event_handlers: list[callable] = []

    @abstractmethod
    def run(self, inp: AgentInput) -> AgentOutput:
        ...

    def register_tool(self, name: str, fn: callable, description: str = ""):
        self._tools[name] = {"fn": fn, "description": description}

    def get_tool(self, name: str) -> Optional[callable]:
        tool = self._tools.get(name)
        return tool["fn"] if tool else None

    def list_tools(self) -> list[dict]:
        return [{"name": n, "description": v["description"]} for n, v in self._tools.items()]

    def add_to_memory(self, role: str, content: str):
        self._memory.append({"role": role, "content": content})

    def get_memory(self, limit: int = 10) -> list[dict]:
        return self._memory[-limit:]

    def clear_memory(self):
        self._memory.clear()

    def on_event(self, handler: callable):
        self._event_handlers.append(handler)

    def emit_event(self, type: str, content: str, metadata: dict | None = None):
        event = StepEvent(type=type, content=content, metadata=metadata or {})
        for handler in self._event_handlers:
            handler(event)
        return event

    def reset(self):
        self._memory.clear()
        self._tools.clear()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}:{self.config.name}>"
