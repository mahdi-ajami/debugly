import logging
import re
import warnings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
warnings.filterwarnings("ignore", message=".*langchain_ollama.*")
from langchain_community.llms import Ollama
from core.config import OLLAMA_BASE_URL, DEFAULT_LLM_MODEL, DEFAULT_EMBEDDING_MODEL
from core.providers import ProviderManager
from core.hf_models import get_hf
from db.chroma import ChromaClient

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are an expert debugging assistant.
The user encountered this error:
{error_text}
Detected language: {language}
Detected error type: {error_type}
{style_instruction}
Here are relevant solutions from the knowledge base:
{context}
Provide a clear, step-by-step solution. Be concise and focused on fixing the issue.
"""


class RAGPipeline:
    def __init__(self, providers: ProviderManager | None = None):
        self._ok = False
        self.db = None
        self.llm = None
        self.chain = None
        self.prompt = None
        self.providers = providers or ProviderManager.load()
        self._last_query_type = ""
        try:
            self.db = ChromaClient(providers=self.providers)
            self._hf = get_hf()
            self.llm = self._build_llm()
            self.prompt = PromptTemplate(
                template=PROMPT_TEMPLATE,
                input_variables=["error_text", "context", "language", "error_type", "style_instruction"],
            )
            self.chain = self.prompt | self.llm | StrOutputParser()
            self._ok = True
        except Exception as exc:
            logger.warning("RAGPipeline init failed: %s", exc)

    @property
    def ok(self) -> bool:
        return self._ok

    def _build_llm(self, query_hint: str | None = None):
        cfg = self.providers.get_llm(query_hint=query_hint)
        model = self.providers.get_active_model(cfg, DEFAULT_LLM_MODEL)
        base_url = self.providers.get_active_base_url(cfg)
        if cfg.enabled and cfg.provider_type == "openai":
            return ChatOpenAI(
                model=model,
                openai_api_key=cfg.api_key or "not-set",
                openai_api_base=self.providers.get_api_url(cfg),
                temperature=0.1,
                streaming=True,
            )
        return Ollama(model=model, base_url=base_url, temperature=0.1)

    def set_llm_for_query(self, query_hint: str):
        if not self._ok:
            return
        query_type = "code" if re.search(r'(traceback|stack\s*trace|def |class |import |```|\.py\b)', query_hint, re.IGNORECASE) else "chat"
        if query_type != self._last_query_type:
            try:
                self.llm = self._build_llm(query_hint=query_hint)
                self.chain = self.prompt | self.llm | StrOutputParser()
                self._last_query_type = query_type
            except Exception as exc:
                logger.warning("RAGPipeline set_llm_for_query failed: %s", exc)
                self._ok = False

    def retrieve_context(self, error_text: str, num_docs: int = 5) -> tuple[str, list[dict]]:
        if not self._ok or not self.db:
            return "", []
        try:
            results = self.db.search(error_text, k=num_docs)
        except Exception as exc:
            logger.warning("RAGPipeline retrieve_context search failed: %s", exc)
            return "", []
        docs = []
        fragments = []
        try:
            for doc, score in results:
                docs.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "knowledge_base"),
                    "score": round(score, 3),
                })
                fragments.append(doc.page_content)
        except Exception as exc:
            logger.warning("RAGPipeline process results failed: %s", exc)
            return "", []
        context = "\n---\n".join(fragments) if fragments else ""
        return context, docs

    def invoke(self, error_text: str, stream: bool = False, language: str = "unknown",
               error_type: str = "unknown", style_instruction: str = ""):
        if not self._ok or not self.chain:
            if stream:
                return iter([""]), []
            return "", []
        try:
            context, docs = self.retrieve_context(error_text)
            inputs = {
                "error_text": error_text, "context": context,
                "language": language, "error_type": error_type,
                "style_instruction": style_instruction,
            }
            if stream:
                return self.chain.stream(inputs), docs
            result = self.chain.invoke(inputs)
            return result, docs
        except Exception as exc:
            logger.warning("RAGPipeline invoke failed: %s", exc)
            if stream:
                return iter([""]), []
            return "", []

    def close(self):
        if self.db:
            self.db.close()
            self.db = None
        self.llm = None
        self.chain = None
        self.prompt = None
        self._ok = False
