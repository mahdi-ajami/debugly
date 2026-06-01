import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import PROJECTS_DIR
from core.database import (
    project_save as db_project_save,
    project_load as db_project_load,
    project_list as db_project_list,
    project_delete as db_project_delete,
    session_list as db_session_list,
    session_save as db_session_save,
)


@dataclass
class Project:
    name: str
    root_path: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    active_session_id: Optional[str] = None

    @property
    def dir(self) -> Path:
        return PROJECTS_DIR / self.name

    @property
    def sessions_dir(self) -> Path:
        return self.dir / "sessions"

    @property
    def config_path(self) -> Path:
        return self.dir / "project.json"

    def save(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"name": self.name, "root_path": self.root_path,
                        "created_at": self.created_at,
                        "active_session_id": self.active_session_id},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        db_project_save(self.name, self.root_path, self.created_at, self.active_session_id)

    def list_sessions(self) -> list[dict]:
        return db_session_list(self.name)

    @classmethod
    def load(cls, name: str):
        data = db_project_load(name)
        if data:
            return cls(
                name=data["name"],
                root_path=data.get("root_path", ""),
                created_at=data.get("created_at", ""),
                active_session_id=data.get("active_session_id"),
            )
        config_path = PROJECTS_DIR / name / "project.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                p = cls(
                    name=data["name"],
                    root_path=data.get("root_path", ""),
                    created_at=data.get("created_at", ""),
                    active_session_id=data.get("active_session_id"),
                )
                p.save()
                return p
            except (json.JSONDecodeError, KeyError):
                return None
        return None


class ProjectManager:
    def __init__(self):
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        self._current: Optional[Project] = None

    @property
    def current(self) -> Optional[Project]:
        return self._current

    def set_current(self, project: Project):
        self._current = project

    def list_projects(self) -> list[dict]:
        return db_project_list()

    def create_project(self, name: str, root_path: str = "") -> Project:
        p = Project(name=name, root_path=root_path or str(Path.cwd()))
        p.save()
        self._current = p
        return p

    def get_or_create_default(self) -> Project:
        default_name = "debugly"
        p = Project.load(default_name)
        if p is None:
            p = self.create_project(default_name,
                                    root_path=str(Path(__file__).resolve().parent.parent))
        self._current = p
        return p

    @classmethod
    def _load_project(cls, name: str):
        return Project.load(name)

    def delete_project(self, name: str):
        path = PROJECTS_DIR / name
        if path.exists():
            shutil.rmtree(path)
        db_project_delete(name)
        if self._current and self._current.name == name:
            self._current = None
