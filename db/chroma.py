import logging
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

logger = logging.getLogger(__name__)


class ChromaClient:
    def __init__(self, providers: ProviderManager | None = None, collection_name: str | None = None):
        self._ok = False
        self.vector_store = None
        self.persistent_client = None
        self.embedding = None
        self._collection_name = collection_name or COLLECTION_NAME
        self.providers = providers or ProviderManager.load()
        try:
            self.embedding = self._build_embedding()
            self.persistent_client = chromadb.PersistentClient(
                path=str(CHROMA_DB_DIR)
            )
            self.vector_store = Chroma(
                client=self.persistent_client,
                collection_name=self._collection_name,
                embedding_function=self.embedding,
            )
            self._ok = True
        except Exception as exc:
            logger.warning("ChromaClient init failed: %s", exc)

    @property
    def ok(self) -> bool:
        return self._ok

    @property
    def collection_name(self) -> str:
        return self._collection_name

    @collection_name.setter
    def collection_name(self, name: str):
        if name != self._collection_name:
            self._collection_name = name
            if not self._ok:
                return
            try:
                self.vector_store = Chroma(
                    client=self.persistent_client,
                    collection_name=name,
                    embedding_function=self.embedding,
                )
            except Exception as exc:
                logger.warning("ChromaClient switch collection failed: %s", exc)
                self._ok = False

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
        if not self._ok or not self.vector_store:
            return
        try:
            self.vector_store.add_texts(texts, metadatas=metadatas)
        except Exception as exc:
            logger.warning("ChromaClient add_documents failed: %s", exc)

    def search(self, query: str, k: int = MAX_RETRIEVED_DOCS):
        if not self._ok or not self.vector_store:
            return []
        try:
            return self.vector_store.similarity_search_with_relevance_scores(query, k=k)
        except Exception as exc:
            logger.warning("ChromaClient search failed: %s", exc)
            return []

    def count(self) -> int:
        if not self._ok or not self.vector_store:
            return 0
        try:
            return self.vector_store._collection.count()
        except Exception as exc:
            logger.warning("ChromaClient count failed: %s", exc)
            return 0

    def close(self):
        self.vector_store = None
        self.persistent_client = None
        self.embedding = None
        self._ok = False
