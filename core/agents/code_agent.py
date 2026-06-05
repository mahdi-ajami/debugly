import ast
import re
from pathlib import Path

from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS, PROJECTS_DIR

_EXTENSIONS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".json", ".yaml", ".yml", ".md", ".txt", ".log", ".csv", ".html", ".css", ".jsx", ".tsx", ".go", ".rs", ".rb", ".php", ".swift", ".kt"}


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
            if f.is_file() and f.suffix in _EXTENSIONS:
                rel = f.relative_to(base)
                result.append(str(rel))
        return result[:50]

    def _grep(self, pattern: str, path: str = "") -> list[dict]:
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

    def _analyze_file_for_bugs(self, file_path: str, content: str) -> list[dict]:
        """Detect syntax errors and common bug patterns. Returns list of issue dicts."""
        issues = []
        if file_path.endswith(".py"):
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                issues.append({
                    "type": "syntax_error",
                    "severity": "error",
                    "line": e.lineno or 1,
                    "message": f"SyntaxError: {e.msg}",
                    "code": e.text or "",
                })
        lines = content.split("\n")
        in_block_comment = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*", "--")):
                if stripped.startswith("/*") or stripped.startswith('"""') or stripped.startswith("'''"):
                    in_block_comment = True
                if in_block_comment and ("*/" in stripped or stripped.endswith('"""') or stripped.endswith("'''")):
                    in_block_comment = False
                continue
            if in_block_comment:
                continue
            if file_path.endswith(".py"):
                if re.search(r'^(from\s+\S+\s+)?import\s+\S+\s*$', stripped) and ";" in stripped.rstrip(";"):
                    issues.append({"type": "style", "severity": "warning", "line": i, "message": "Multiple imports on one line", "code": stripped[:100]})
                if stripped.startswith("print ") and "(" not in stripped:
                    issues.append({"type": "syntax", "severity": "error", "line": i, "message": "Python 3 requires parentheses: print()", "code": stripped[:100]})
                if re.search(r'except\s+\w+\s*,', stripped) and not stripped.rstrip().endswith(":"):
                    issues.append({"type": "syntax", "severity": "error", "line": i, "message": "Use 'except X as e:' instead of 'except X, e:' (Python 3)", "code": stripped[:100]})
        return issues

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Code Agent: analyzing project context...")
        project_dir = inp.metadata.get("project_root", str(PROJECTS_DIR))
        files = self._list_dir(project_dir)
        relevant = []
        for f in files:
            if any(kw in f.lower() for kw in inp.query.lower().split()):
                relevant.append(f)
        code_snippets = []
        bug_reports = []
        for rf in relevant[:10]:
            content = self._read_file(str(Path(project_dir) / rf))
            if content:
                code_snippets.append({"file": rf, "content": content})
                bugs = self._analyze_file_for_bugs(rf, content)
                if bugs:
                    bug_reports.append({"file": rf, "issues": bugs})
        context_parts = [f"Project files: {len(files)} total, {len(relevant)} relevant"]
        if bug_reports:
            context_parts.append(f"Found issues in {len(bug_reports)} files:")
            for br in bug_reports:
                context_parts.append(f"  {br['file']}: {len(br['issues'])} issue(s)")
        context = "\n".join(context_parts)
        self.emit_event("generate", f"Code Agent: {context}")
        return AgentOutput(
            success=True,
            content=context,
            data={
                "relevant_files": relevant,
                "code_snippets": code_snippets,
                "bug_reports": bug_reports,
                "project_context": context,
            },
        )
