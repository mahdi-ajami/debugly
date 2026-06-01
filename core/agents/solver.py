from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.rag_pipeline import RAGPipeline


SOLVER_SYSTEM_PROMPT = """You are an expert debugging assistant. Based on the error information and context provided, generate a clear, step-by-step solution.

Error: {query}

Context from knowledge base:
{context}

Web research:
{web_context}

Code analysis:
{code_context}

Classification:
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

    def _generate(self, query: str, context: str, web_context: str = "", code_context: str = "", classification: str = "") -> str:
        prompt = SOLVER_SYSTEM_PROMPT.format(
            query=query, context=context, web_context=web_context,
            code_context=code_context, classification=classification,
        )
        inputs = {
            "error_text": query,
            "context": context,
            "language": "unknown",
            "error_type": "unknown",
            "style_instruction": "Provide a clear, balanced solution with explanation.",
        }
        result = self._rag.chain.invoke(inputs)
        return result

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Solver: generating solution...")
        context = inp.metadata.get("knowledge", {}).get("content", "")
        if not context:
            kb_context, _ = self._rag.retrieve_context(inp.query, num_docs=self.config.max_retrieved_docs)
            context = kb_context
        web_context = inp.metadata.get("research", {}).get("content", "")
        code_context = inp.metadata.get("code_agent", {}).get("content", "")
        classification = inp.metadata.get("classifier", {}).get("content", "")
        self.emit_event("generate", "Solver: composing final answer...")
        solution = self._generate(
            query=inp.query,
            context=context,
            web_context=web_context,
            code_context=code_context,
            classification=classification,
        )
        self.emit_event("generate", solution, {"partial": False})
        return AgentOutput(success=True, content=solution, data={"solution": solution})
