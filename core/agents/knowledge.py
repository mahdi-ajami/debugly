import logging

from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        config = config or AgentConfig.from_dict(AGENT_CONFIGS["knowledge"])
        super().__init__(config, providers)
        self._rag = RAGPipeline(providers=self.providers)
        if self._rag.ok and self._rag.db:
            try:
                self._rag.db.collection_name = config.rag_collection or "error_solutions"
            except Exception as exc:
                logger.warning("KnowledgeAgent set collection failed: %s", exc)
        self.register_tool("search_knowledge_base", self._search_kb, "Search the knowledge base for similar errors")
        self.register_tool("get_kb_stats", self._get_stats, "Get knowledge base statistics")
        self.register_tool("count_documents", self._count_docs, "Count documents in the collection")

    def _search_kb(self, query: str, num_docs: int = 5) -> tuple[str, list[dict]]:
        try:
            return self._rag.retrieve_context(query, num_docs=num_docs)
        except Exception as exc:
            logger.warning("KnowledgeAgent search failed: %s", exc)
            return "", []

    def _get_stats(self) -> dict:
        try:
            cname = self._rag.db.collection_name if self._rag.db else "unknown"
            cnt = self._rag.db.count() if self._rag.db else 0
            return {"collection": cname, "count": cnt}
        except Exception:
            return {"collection": "unknown", "count": 0}

    def _count_docs(self) -> int:
        try:
            return self._rag.db.count() if self._rag.db else 0
        except Exception:
            return 0

    def run(self, inp: AgentInput) -> AgentOutput:
        num_docs = self.config.max_retrieved_docs
        cname = "unknown"
        try:
            cname = self._rag.db.collection_name if self._rag.db else "unknown"
        except Exception:
            pass
        self.emit_event("retrieve", f"Knowledge: searching {num_docs} docs in '{cname}'...")
        context, docs = self._search_kb(inp.query, num_docs=num_docs)
        self.emit_event("generate", f"Knowledge: found {len(docs)} relevant documents")
        best_score = docs[0]["score"] if docs else 0
        metadata = {"extracted_text": inp.metadata.get("extracted_text", "")}
        return AgentOutput(
            success=True,
            content=context,
            data={"docs": docs, "total_found": len(docs), "collection": cname, "best_score": best_score},
        )
