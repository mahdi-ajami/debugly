import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    category: str = "general"
    fn: Optional[Callable] = None
    enabled: bool = True

    def execute(self, **kwargs) -> Any:
        if self.fn is None:
            raise ValueError(f"Tool '{self.name}' has no callable attached")
        return self.fn(**kwargs)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "category": self.category,
            "enabled": self.enabled,
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}
        self._call_log: list[dict] = []

    def register(self, tool: ToolSpec):
        self._tools[tool.name] = tool

    def register_fn(self, name: str, fn: Callable, description: str = "", category: str = "general", parameters: dict | None = None):
        self._tools[name] = ToolSpec(
            name=name,
            description=description,
            fn=fn,
            category=category,
            parameters=parameters or {},
        )

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[ToolSpec]:
        if category:
            return [t for t in self._tools.values() if t.category == category and t.enabled]
        return [t for t in self._tools.values() if t.enabled]

    def list_categories(self) -> list[str]:
        cats = {t.category for t in self._tools.values()}
        return sorted(cats)

    def execute(self, tool_name: str, **kwargs) -> Any:
        tool = self.get(tool_name)
        if tool is None:
            raise KeyError(f"Tool '{tool_name}' not found")
        if not tool.enabled:
            raise RuntimeError(f"Tool '{tool_name}' is disabled")
        result = tool.execute(**kwargs)
        self._call_log.append({
            "tool": tool_name,
            "params": kwargs,
            "timestamp": datetime.now().isoformat(),
        })
        return result

    def call_log(self, limit: int = 20) -> list[dict]:
        return self._call_log[-limit:]

    def remove(self, name: str):
        self._tools.pop(name, None)

    def clear(self):
        self._tools.clear()
        self._call_log.clear()

    def count(self) -> int:
        return len(self._tools)

    def to_dict(self) -> dict:
        return {"tools": [t.to_dict() for t in self._tools.values()]}

    @classmethod
    def from_dict(cls, data: dict, fn_map: dict[str, Callable] | None = None):
        registry = cls()
        for t_data in data.get("tools", []):
            fn = (fn_map or {}).get(t_data["name"])
            registry._tools[t_data["name"]] = ToolSpec(
                name=t_data["name"],
                description=t_data.get("description", ""),
                parameters=t_data.get("parameters", {}),
                category=t_data.get("category", "general"),
                fn=fn,
                enabled=t_data.get("enabled", True),
            )
        return registry
