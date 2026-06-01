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
        self.providers = providers or ProviderManager.load()
        self.db = ChromaClient(providers=self.providers)
        self._hf = get_hf()
        self._last_query_type = ""
        self.llm = self._build_llm()
        self.prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["error_text", "context", "language", "error_type", "style_instruction"],
        )
        self.chain = self.prompt | self.llm | StrOutputParser()

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
        query_type = "code" if re.search(r'(traceback|stack\s*trace|def |class |import |```|\.py\b)', query_hint, re.IGNORECASE) else "chat"
        if query_type != self._last_query_type:
            self.llm = self._build_llm(query_hint=query_hint)
            self.chain = self.prompt | self.llm | StrOutputParser()
            self._last_query_type = query_type

    def retrieve_context(self, error_text: str, num_docs: int = 5) -> tuple[str, list[dict]]:
        results = self.db.search(error_text, k=num_docs)
        docs = []
        fragments = []
        for doc, score in results:
            docs.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "knowledge_base"),
                "score": round(score, 3),
            })
            fragments.append(doc.page_content)
        context = "\n---\n".join(fragments) if fragments else "No relevant results found."
        return context, docs

    def invoke(self, error_text: str, stream: bool = False, language: str = "unknown", error_type: str = "unknown", style_instruction: str = ""):
        context, docs = self.retrieve_context(error_text)
        inputs = {"error_text": error_text, "context": context, "language": language, "error_type": error_type, "style_instruction": style_instruction}
        if stream:
            return self.chain.stream(inputs), docs
        result = self.chain.invoke(inputs)
        return result, docs
