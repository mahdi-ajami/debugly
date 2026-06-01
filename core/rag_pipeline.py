from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser

from core.config import OLLAMA_BASE_URL, LLAMA_MODEL
from db.chroma import ChromaClient


PROMPT_TEMPLATE = """You are an expert debugging assistant.

The user encountered this error:
{error_text}

Here are relevant solutions from the knowledge base:
{context}

Provide a clear, step-by-step solution. Be concise.
"""


class RAGPipeline:
    def __init__(self):
        self.db = ChromaClient()
        self.llm = Ollama(
            model=LLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.1,
        )
        self.prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["error_text", "context"],
        )
        self.chain = self.prompt | self.llm | StrOutputParser()

    def retrieve_context(self, error_text: str) -> tuple[str, list[dict]]:
        results = self.db.search(error_text)
        docs = []
        fragments = []
        for doc, score in results:
            docs.append({"content": doc.page_content, "source": doc.metadata.get("source", "knowledge_base"), "score": round(score, 3)})
            fragments.append(doc.page_content)
        context = "\n---\n".join(fragments) if fragments else "No relevant results found."
        return context, docs

    def invoke(self, error_text: str, stream: bool = False):
        context, docs = self.retrieve_context(error_text)
        if stream:
            return self.chain.stream({"error_text": error_text, "context": context}), docs
        result = self.chain.invoke({"error_text": error_text, "context": context})
        return result, docs
