import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings

from core.config import (
    CHROMA_DB_DIR,
    COLLECTION_NAME,
    OLLAMA_BASE_URL,
    EMBEDDING_MODEL,
    MAX_RETRIEVED_DOCS,
)


class ChromaClient:
    def __init__(self):
        self.embedding = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
        self.persistent_client = chromadb.PersistentClient(
            path=str(CHROMA_DB_DIR)
        )
        self.vector_store = Chroma(
            client=self.persistent_client,
            collection_name=COLLECTION_NAME,
            embedding_function=self.embedding,
        )

    def add_documents(self, texts: list[str], metadatas: list[dict] | None = None):
        self.vector_store.add_texts(texts, metadatas=metadatas)

    def search(self, query: str, k: int = MAX_RETRIEVED_DOCS):
        return self.vector_store.similarity_search_with_relevance_scores(
            query, k=k
        )

    def count(self) -> int:
        return self.vector_store._collection.count()
