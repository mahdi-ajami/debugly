import logging

from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)


SOLVER_SYSTEM_PROMPT = """You are an expert debugging assistant. Based on the error information and context provided, generate a clear, step-by-step solution.

Error: {query}

Context from knowledge base:
{context}

VLM analysis (from screenshot):
{vlm_text}

Web research:
{web_context}

Code analysis:
{code_context}

Classification:
- Language: {language}
- Error type: {error_type}
- Severity: {severity}
{classification}

Instructions:
1. Explain the root cause of the error
2. Provide a step-by-step solution
3. Include code examples where relevant
4. Suggest preventive measures
Be concise and focused."""


class SolverAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["solver"]), providers)
        self._rag = RAGPipeline(providers=self.providers)
        self.register_tool("generate_solution", self._generate, "Generate a solution from context")

    def _generate(self, query: str, context: str, vlm_text: str = "",
                  web_context: str = "", code_context: str = "",
                  classification: str = "", language: str = "unknown",
                  error_type: str = "unknown", severity: str = "medium") -> str:
        try:
            prompt = SOLVER_SYSTEM_PROMPT.format(
                query=query, context=context, vlm_text=vlm_text,
                web_context=web_context, code_context=code_context,
                classification=classification, language=language,
                error_type=error_type, severity=severity,
            )
            if not self._rag.ok or not self._rag.llm:
                return "I'm sorry, the LLM is not available. Please check that Ollama is running and the model is pulled."
            result = self._rag.llm.invoke(prompt)
            if hasattr(result, 'content'):
                return result.content
            return str(result)
        except Exception as exc:
            logger.warning("SolverAgent generate failed: %s", exc)
            return f"I encountered an error while generating the solution: {exc}\n\nPossible causes:\n- Ollama is not running\n- The model is not pulled (`ollama pull gpt-oss:latest`)\n- The model is still loading (try again in a moment)"

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Solver: generating solution...")
        context = inp.metadata.get("knowledge", {}).get("content", "")
        if not context:
            try:
                kb_context, _ = self._rag.retrieve_context(inp.query, num_docs=self.config.max_retrieved_docs)
                context = kb_context
            except Exception as exc:
                logger.warning("SolverAgent KB fallback failed: %s", exc)
                context = ""

        vlm_text = inp.metadata.get("vlm_text", "")
        web_context = inp.metadata.get("research", {}).get("content", "")
        code_context = inp.metadata.get("code_agent", {}).get("content", "")
        classification_raw = inp.metadata.get("classifier", {}).get("content", "")

        classifier_data = inp.metadata.get("classifier", {}).get("data", {})
        language = classifier_data.get("language", "unknown")
        error_type = classifier_data.get("error_type", "unknown")
        severity = classifier_data.get("severity", "medium")

        self.emit_event("generate", "Solver: composing final answer...")
        solution = self._generate(
            query=inp.query,
            context=context,
            vlm_text=vlm_text,
            web_context=web_context,
            code_context=code_context,
            classification=classification_raw,
            language=language,
            error_type=error_type,
            severity=severity,
        )
        self.emit_event("generate", solution, {"partial": False})
        return AgentOutput(success=True, content=solution, data={"solution": solution})
