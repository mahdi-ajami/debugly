from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.guardrails import InputGuardrails, OutputGuardrails


class GuardianAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["guardian"]), providers)
        self.register_tool("check_input", self._check_input, "Check input for safety issues")
        self.register_tool("check_output", self._check_output, "Check output for safety issues")
        self.register_tool("redact_sensitive", self._redact, "Redact sensitive data from text")

    def _check_input(self, text: str) -> dict:
        warnings = []
        length_check = InputGuardrails.check_length(text)
        if not length_check.passed:
            warnings.append(length_check.message)
        sensitive_check = InputGuardrails.check_sensitive_data(text)
        if sensitive_check.message:
            warnings.append(sensitive_check.message)
        dangerous_check = InputGuardrails.check_dangerous_code(text)
        if not dangerous_check.passed:
            warnings.append(dangerous_check.message)
        sanitized = sensitive_check.sanitized or text
        return {
            "passed": length_check.passed and dangerous_check.passed,
            "sanitized_text": sanitized,
            "warnings": warnings,
        }

    def _check_output(self, text: str) -> dict:
        warnings = []
        dangerous_check = OutputGuardrails.check_dangerous_code(text)
        if not dangerous_check.passed:
            warnings.append(dangerous_check.message)
        sensitive_check = OutputGuardrails.check_sensitive_data(text)
        if sensitive_check.message:
            warnings.append(sensitive_check.message)
        return {
            "passed": dangerous_check.passed,
            "sanitized_text": sensitive_check.sanitized or text,
            "warnings": warnings,
        }

    def _redact(self, text: str) -> str:
        return self._check_input(text)["sanitized_text"]

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Guardian: checking input safety...")
        result = self._check_input(inp.query)
        if result["warnings"]:
            for w in result["warnings"]:
                self.emit_event("think", f"Guardian: {w}")
        if not result["passed"]:
            self.emit_event("error", "Guardian: input blocked")
            return AgentOutput(
                success=False,
                content="",
                error="; ".join(result["warnings"]),
                data={"passed": False, "warnings": result["warnings"]},
            )
        self.emit_event("generate", "Guardian: input passed")
        return AgentOutput(
            success=True,
            content=result["sanitized_text"],
            data=result,
        )
