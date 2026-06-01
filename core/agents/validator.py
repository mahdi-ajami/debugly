import re
from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS


class ValidatorAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["validator"]), providers)
        self.register_tool("check_syntax", self._check_syntax, "Check code syntax")
        self.register_tool("check_completeness", self._check_completeness, "Check solution completeness")

    def _check_syntax(self, code: str, language: str = "python") -> dict:
        blocks = re.findall(r"```(\w+)?\n(.*?)```", code, re.DOTALL)
        issues = []
        for lang, body in blocks:
            if lang in ("python", "py", "") or language == "python":
                lines = body.splitlines()
                for i, line in enumerate(lines, 1):
                    if re.match(r"^\s*except\s*:", line):
                        issues.append({"line": i, "message": "bare except clause", "severity": "warning"})
                    if re.match(r"^\s*import\s+\*", line):
                        issues.append({"line": i, "message": "wildcard import", "severity": "warning"})
        return {"valid": len(issues) == 0, "issues": issues, "total_blocks": len(blocks)}

    def _check_completeness(self, solution: str) -> dict:
        score = 1.0
        missing = []
        if "root cause" not in solution.lower() and "cause" not in solution.lower():
            score -= 0.2
            missing.append("root cause explanation")
        if "step" not in solution.lower() and not re.search(r"\d\.\s", solution):
            score -= 0.2
            missing.append("step-by-step instructions")
        if "```" not in solution:
            score -= 0.2
            missing.append("code example")
        if len(solution) < 100:
            score -= 0.3
            missing.append("sufficient detail")
        return {"score": max(0.0, score), "missing": missing, "length": len(solution)}

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Validator: checking solution quality...")
        solution = inp.query or inp.metadata.get("solver", {}).get("content", "")
        if not solution:
            return AgentOutput(success=True, content="", data={"valid": True, "message": "nothing to validate"})
        syntax = self._check_syntax(solution)
        completeness = self._check_completeness(solution)
        valid = syntax["valid"] and completeness["score"] >= 0.5
        if not valid:
            issues = []
            if not syntax["valid"]:
                issues.append(f"{len(syntax['issues'])} syntax issues")
            if completeness["score"] < 0.5:
                issues.append(f"completeness score: {completeness['score']}")
            self.emit_event("think", f"Validator: {', '.join(issues)}")
        self.emit_event("generate", f"Validator: {'passed' if valid else 'needs improvement'} (completeness: {completeness['score']:.1f})")
        return AgentOutput(
            success=valid,
            content=solution if valid else "",
            data={
                "valid": valid,
                "syntax_ok": syntax["valid"],
                "completeness_score": completeness["score"],
                "suggestions": completeness["missing"],
            },
        )
