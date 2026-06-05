import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_hf_available = False

try:
    from huggingface_hub import InferenceClient, HfApi
    _hf_available = True
except ImportError:
    InferenceClient = None
    HfApi = None
    logger.debug("huggingface-hub not installed")


class HFModels:
    def __init__(self, api_token: str = ""):
        self.api_token = api_token
        self._client: Optional[InferenceClient] = None
        self._api: Optional[HfApi] = None
        self._local_available = False
        self._init()

    def _init(self):
        if not _hf_available:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._local_embedder = SentenceTransformer("all-MiniLM-L6-v2", trust_remote_code=True)
            self._local_available = True
        except Exception:
            self._local_embedder = None

        if self.api_token and InferenceClient:
            try:
                self._client = InferenceClient(token=self.api_token)
                self._api = HfApi(token=self.api_token)
            except Exception:
                pass

    @property
    def available(self) -> bool:
        return _hf_available

    def classify_error_type(self, error_text: str) -> str:
        types = {
            "import": r"(import|module|no module named)",
            "syntax": r"(syntax error|invalid syntax|unexpected token)",
            "type": r"(typeerror|type error|cannot .* type|unsupported operand)",
            "value": r"(valueerror|value error|invalid.*value)",
            "key": r"(keyerror|key error)",
            "index": r"(indexerror|index error|list index|out of range)",
            "attribute": r"(attributeerror|attribute error|has no attribute)",
            "file": r"(filenotfound|file not found|no such file)",
            "connection": r"(connectionrefused|connection.*refused|connection.*reset)",
            "permission": r"(permissionerror|permission denied|access denied)",
            "memory": r"(out of memory|memoryerror|memory.*alloc)",
            "null": r"(nullreference|null pointer|object.*null)",
        }
        lower = error_text.lower()
        for etype, pattern in types.items():
            if re.search(pattern, lower):
                return etype
        return "unknown"

    def classify_language(self, error_text: str) -> str:
        langs = {
            "python": r"(traceback|filenotfounderror|importerror|indentationerror|syntaxerror|typeerror|valueerror|keyerror|attributeerror|modulenotfounderror)",
            "javascript": r"(typeerror|referenceerror|syntaxerror|rangeerror|cannot read property|is not defined|is not a function)",
            "typescript": r"(cannot find name|type .* is not assignable|property .* does not exist)",
            "java": r"(nullpointerexception|classcastexception|illegalargumentexception|exception in thread)",
            "csharp": r"(nullreferenceexception|invalidoperationexception|argumentnullexception|cs\d{4})",
            "rust": r"(error\[e\d+\]|unresolved import|cannot borrow|mismatched types)",
            "go": r"(nil pointer dereference|unexpected end|syntax error.*go)",
            "ruby": r"(undefined method|nomethoderror|syntaxerror)",
        }
        lower = error_text.lower()
        for lang, pattern in langs.items():
            if re.search(pattern, lower):
                return lang
        return "unknown"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._local_available and self._local_embedder:
            try:
                return self._local_embedder.encode(texts, show_progress_bar=False).tolist()
            except Exception:
                pass

        if self._client:
            try:
                result = self._client.feature_extraction(texts, model="sentence-transformers/all-MiniLM-L6-v2")
                if result and isinstance(result, list) and len(result) > 0:
                    return result if isinstance(result[0], list) else [result]
            except Exception:
                pass

        return [[0.0] * 384 for _ in texts]

    def summarize_error(self, error_text: str, max_length: int = 150) -> str:
        return error_text[:max_length] + ("..." if len(error_text) > max_length else "")

    def clear(self):
        if hasattr(self, '_local_embedder') and self._local_embedder is not None:
            try:
                del self._local_embedder
            except Exception:
                pass
            self._local_embedder = None
        self._client = None
        self._api = None
        self._local_available = False
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


_hf: Optional[HFModels] = None


def get_hf() -> HFModels:
    global _hf
    if _hf is None:
        _hf = HFModels()
    return _hf


def init_hf(api_token: str = ""):
    global _hf
    _hf = HFModels(api_token=api_token)
    return _hf


def reset_hf():
    global _hf
    if _hf is not None:
        _hf.clear()
        _hf = None
