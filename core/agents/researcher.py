from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.web_search import search_web


class ResearchAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["research"]), providers)
        self.register_tool("search_web", self._web_search, "Search approved web sources")
        self.register_tool("search_stackoverflow", self._search_so, "Search Stack Overflow specifically")

    def _web_search(self, query: str, max_results: int = 3) -> list[dict]:
        return search_web(query, max_results=max_results)

    def _search_so(self, query: str) -> list[dict]:
        return search_web(f"site:stackoverflow.com {query}", max_results=5)

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("retrieve", "Research: searching web sources...")
        results = self._web_search(inp.query)
        num = len(results)
        if num > 0:
            self.emit_event("generate", f"Research: found {num} web sources")
        else:
            self.emit_event("think", "Research: no web results found")
        fragments = []
        for r in results[:3]:
            src = r.get("source", "web")
            content = r.get("content", "")[:300]
            url = r.get("url", "")
            fragments.append(f"[{src}]({url}): {content}")
        context = "\n\n".join(fragments) if fragments else ""
        return AgentOutput(
            success=True,
            content=context,
            data={"results": results, "total_sources": num},
        )
