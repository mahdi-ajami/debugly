from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.hf_models import get_hf


class ClassifierAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["classifier"]), providers)
        self._hf = get_hf()
        self.register_tool("classify_error_type", self._classify_type, "Classify the error type")
        self.register_tool("detect_language", self._detect_language, "Detect programming language")

    def _classify_type(self, text: str) -> str:
        if self._hf.available:
            return self._hf.classify_error_type(text)
        return "unknown"

    def _detect_language(self, text: str) -> str:
        if self._hf.available:
            return self._hf.classify_language(text)
        return "unknown"

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Classifier: analyzing error...")
        error_type = self._classify_type(inp.query)
        language = self._detect_language(inp.query)
        keywords = self._extract_keywords(inp.query)
        output = {
            "error_type": error_type,
            "language": language,
            "severity": self._estimate_severity(inp.query),
            "keywords": keywords,
        }
        self.emit_event("generate", f"Classifier: {language} | {error_type} | {len(keywords)} keywords")
        return AgentOutput(success=True, content=f"Type: {error_type}, Language: {language}", data=output)

    def _extract_keywords(self, text: str) -> list[str]:
        import re
        words = re.findall(r"[A-Za-z_]\w+", text)
        stopwords = {"the", "is", "at", "of", "in", "to", "a", "an", "and", "or", "for", "on", "with", "this", "that", "from", "by", "be", "as", "are", "was", "were", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "can", "could", "should", "may", "might", "shall", "not", "no", "nor", "but", "if", "so", "up", "out", "about", "into", "over", "after", "before", "between", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "each", "every", "both", "few", "more", "most", "other", "some", "such", "only", "own", "same", "too", "very", "just", "also", "than"}
        return [w for w in words if w.lower() not in stopwords][:15]

    def _estimate_severity(self, text: str) -> str:
        critical = {"traceback", "fatal", "critical", "panic", "segfault", "crash", "deadlock", "corrupt"}
        high = {"error", "exception", "fail", "invalid", "unexpected", "permission denied", "access denied"}
        words = set(text.lower().split())
        if words & critical:
            return "critical"
        if words & high:
            return "high"
        return "medium"
