from pathlib import Path
from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS, PROJECTS_DIR


class CodeAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["code_agent"]), providers)
        self.register_tool("read_file", self._read_file, "Read contents of a file")
        self.register_tool("list_directory", self._list_dir, "List files in a directory")
        self.register_tool("search_in_files", self._grep, "Search for pattern in project files")

    def _read_file(self, path: str) -> str:
        p = Path(path)
        if p.exists() and p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
        return ""

    def _list_dir(self, path: str = "") -> list[str]:
        base = Path(path) if path else PROJECTS_DIR
        if not base.exists():
            return []
        result = []
        for f in base.rglob("*"):
            if f.is_file() and f.suffix in {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".json", ".yaml", ".yml", ".md", ".txt", ".log", ".csv", ".html", ".css", ".jsx", ".tsx"}:
                rel = f.relative_to(base)
                result.append(str(rel))
        return result[:50]

    def _grep(self, pattern: str, path: str = "") -> list[dict]:
        import re
        base = Path(path) if path else PROJECTS_DIR
        if not base.exists():
            return []
        matches = []
        for f in base.rglob("*"):
            if f.is_file() and f.suffix in {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".json", ".txt", ".log", ".csv"}:
                try:
                    for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            matches.append({"file": str(f.relative_to(base)), "line": i, "content": line.strip()[:200]})
                except Exception:
                    pass
        return matches[:30]

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Code Agent: analyzing project context...")
        project_dir = inp.metadata.get("project_root", str(PROJECTS_DIR))
        files = self._list_dir(project_dir)
        relevant = []
        for f in files:
            if any(kw in f.lower() for kw in inp.query.lower().split()):
                relevant.append(f)
        code_snippets = []
        for rf in relevant[:5]:
            content = self._read_file(str(Path(project_dir) / rf))
            if content:
                code_snippets.append({"file": rf, "content": content[:500]})
        context = f"Project files: {len(files)} total, {len(relevant)} relevant"
        self.emit_event("generate", f"Code Agent: {context}")
        return AgentOutput(
            success=True,
            content=context,
            data={"relevant_files": relevant, "code_snippets": code_snippets, "project_context": context},
        )
