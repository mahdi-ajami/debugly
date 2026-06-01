import warnings

import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

warnings.filterwarnings("ignore", message=".*langchain_ollama.*")
from langchain_community.embeddings import OllamaEmbeddings

from core.config import (
    CHROMA_DB_DIR, COLLECTION_NAME,
    OLLAMA_BASE_URL, DEFAULT_EMBEDDING_MODEL,
    MAX_RETRIEVED_DOCS,
)
from core.providers import ProviderManager


class ChromaClient:
    def __init__(self, providers: ProviderManager | None = None):
        self.providers = providers or ProviderManager.load()
        self.embedding = self._build_embedding()
        self.persistent_client = chromadb.PersistentClient(
            path=str(CHROMA_DB_DIR)
        )
        self.vector_store = Chroma(
            client=self.persistent_client,
            collection_name=COLLECTION_NAME,
            embedding_function=self.embedding,
        )

    def _build_embedding(self):
        cfg = self.providers.embedding
        model = self.providers.get_active_model(cfg, DEFAULT_EMBEDDING_MODEL)

        if cfg.enabled and cfg.provider_type == "openai":
            return OpenAIEmbeddings(
                model=model,
                openai_api_key=cfg.api_key or "not-set",
                openai_api_base=self.providers.get_api_url(cfg),
            )

        return OllamaEmbeddings(
            model=model,
            base_url=self.providers.get_active_base_url(cfg),
        )

    def add_documents(self, texts: list[str], metadatas: list[dict] | None = None):
        self.vector_store.add_texts(texts, metadatas=metadatas)

    def search(self, query: str, k: int = MAX_RETRIEVED_DOCS):
        return self.vector_store.similarity_search_with_relevance_scores(
            query, k=k
        )

    def count(self) -> int:
        return self.vector_store._collection.count()
