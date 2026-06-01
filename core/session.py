import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import PROJECTS_DIR
from core.database import session_save as db_save, session_load as db_load, session_delete as db_delete


@dataclass
class StepEvent:
    type: str
    content: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {"type": self.type, "content": self.content, "metadata": self.metadata}


@dataclass
class Message:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    steps: list = field(default_factory=list)

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "steps": [s.to_dict() if isinstance(s, StepEvent) else s for s in self.steps],
        }


@dataclass
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    project_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    context: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)

    def add_message(self, role: str, content: str, steps: list | None = None):
        msg = Message(role=role, content=content, steps=steps or [])
        self.messages.append(msg)
        self.updated_at = datetime.now().isoformat()
        return msg

    @property
    def path(self) -> Path:
        return PROJECTS_DIR / self.project_name / "sessions" / f"{self.id}.json"

    def save(self):
        db_save(self.to_dict())

    def to_dict(self):
        return {
            "id": self.id,
            "project_name": self.project_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context": self.context,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def create(cls, project, source_file: str = ""):
        return cls(
            project_name=project.name,
            context={
                "source_file": source_file,
                "project_root": str(project.root_path),
            },
        )

    @classmethod
    def load(cls, file_path: Optional[Path] = None, session_id: Optional[str] = None):
        if session_id:
            data = db_load(session_id)
            if not data:
                return None
        elif file_path and file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, KeyError):
                return None
        else:
            return None
        s = cls(
            id=data["id"],
            project_name=data.get("project_name", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            context=data.get("context", {}),
        )
        for m in data.get("messages", []):
            steps = [StepEvent(**s) for s in m.get("steps", [])]
            msg = Message(role=m["role"], content=m["content"],
                          timestamp=m.get("timestamp", ""), steps=steps)
            s.messages.append(msg)
        return s

    def delete(self):
        db_delete(self.id)
