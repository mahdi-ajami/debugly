import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_VLM_MODEL = "llava:7b"
DEFAULT_LLM_MODEL = "qwen3-coder:30b"
DEFAULT_CHAT_MODEL = "qwen3-coder:30b"
DEFAULT_CODE_MODEL = "qwen3-coder:30b"
DEFAULT_EMBEDDING_MODEL = "mxbai-embed-large:latest"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

DB_PATH = PROJECT_ROOT / "db" / "debugly.db"
CHROMA_DB_DIR = PROJECT_ROOT / "db" / "chroma_data"
COLLECTION_NAME = "error_solutions"
PROVIDERS_FILE = PROJECT_ROOT / "db" / "providers.json"
PROJECTS_DIR = PROJECT_ROOT / "projects"

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"

MAX_RETRIEVED_DOCS = 5
STREAM_CHUNK_SIZE = 20

BANDIT_EPSILON = 0.1
BANDIT_DECAY = 0.995
BANDIT_MIN_EPSILON = 0.01

UI_TITLE = "Debugly"
UI_THEME_COLOR = "#7C3AED"

AGENT_CONFIGS = {
    "orchestrator": {
        "name": "orchestrator",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.3,
        "rag_collection": "",
        "timeout_seconds": 120,
        "label": "Orchestrator",
        "description": "Supervisor agent that routes tasks and aggregates results",
    },
    "vision": {
        "name": "vision",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.1,
        "rag_collection": "",
        "timeout_seconds": 60,
        "label": "Vision",
        "description": "Extracts error text from screenshots via VLM",
    },
    "classifier": {
        "name": "classifier",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.2,
        "rag_collection": "error_solutions",
        "timeout_seconds": 30,
        "label": "Classifier",
        "description": "Classifies error type, language, and severity",
    },
    "knowledge": {
        "name": "knowledge",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.3,
        "rag_collection": "error_solutions",
        "max_retrieved_docs": 5,
        "timeout_seconds": 30,
        "label": "Knowledge",
        "description": "Retrieves context from ChromaDB knowledge base",
    },
    "research": {
        "name": "research",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.3,
        "rag_collection": "web_cache",
        "timeout_seconds": 60,
        "label": "Research",
        "description": "Searches approved web sources for solutions",
    },
    "code_agent": {
        "name": "code_agent",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.2,
        "rag_collection": "code_patterns",
        "timeout_seconds": 60,
        "label": "Code Agent",
        "description": "Analyzes project code and file context",
    },
    "solver": {
        "name": "solver",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.5,
        "rag_collection": "best_practices",
        "max_retrieved_docs": 7,
        "timeout_seconds": 120,
        "label": "Solver",
        "description": "Generates the final solution from all contexts",
    },
    "guardian": {
        "name": "guardian",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.1,
        "rag_collection": "security_guidelines",
        "timeout_seconds": 15,
        "label": "Guardian",
        "description": "Input/output safety checks and data redaction",
    },
    "validator": {
        "name": "validator",
        "enabled": False,
        "llm_model": "",
        "temperature": 0.1,
        "rag_collection": "",
        "timeout_seconds": 30,
        "label": "Validator",
        "description": "Validates solution syntax and completeness",
    },
    "learner": {
        "name": "learner",
        "enabled": True,
        "llm_model": "",
        "temperature": 0.3,
        "rag_collection": "feedback_patterns",
        "timeout_seconds": 15,
        "label": "Learner",
        "description": "Processes feedback and updates RL bandit",
    },
}

AGENT_RAG_COLLECTIONS = {
    "error_solutions": "General error-solution pairs",
    "code_patterns": "Code patterns and idioms",
    "best_practices": "Best practice solutions",
    "web_cache": "Cached web search results",
    "security_guidelines": "Security rules and patterns",
    "feedback_patterns": "User feedback history",
}

AGENT_WORKFLOW_MODES = ["sequential", "parallel", "dynamic"]
DEFAULT_WORKFLOW_MODE = "sequential"
MAX_PARALLEL_AGENTS = 3

MODEL_CONTEXT_SIZES = {
    "qwen3-coder:30b": 32768,
    "qwen3-coder:14b": 16384,
    "qwen3-coder:7b": 8192,
    "qwen2.5-coder:32b": 32768,
    "qwen2.5-coder:14b": 16384,
    "qwen2.5-coder:7b": 32768,
    "llama3.2:3b": 8192,
    "llama3.2:1b": 8192,
    "llama3.1:8b": 128000,
    "llama3.1:70b": 128000,
    "llama3.1:405b": 128000,
    "deepseek-coder:6.7b": 16384,
    "deepseek-coder:33b": 16384,
    "codegemma:2b": 8192,
    "codegemma:7b": 8192,
    "codellama:7b": 16384,
    "codellama:13b": 16384,
    "codellama:34b": 16384,
    "mistral:7b": 32768,
    "mixtral:8x7b": 32768,
    "llava:7b": 4096,
    "llava:13b": 4096,
    "llava:34b": 4096,
    "mxbai-embed-large": 512,
    "nomic-embed-text": 8192,
    "snowflake-arctic-embed": 8192,
}
DEFAULT_CONTEXT_LIMIT = 8192
TOKEN_RATIO = 0.35

RTL_RANGES = [
    (0x0590, 0x05FF, "hebrew"),
    (0x0600, 0x06FF, "arabic"),
    (0x0700, 0x074F, "syriac"),
    (0x0750, 0x077F, "arabic_supplement"),
    (0x08A0, 0x08FF, "arabic_extended_a"),
    (0xFB1D, 0xFB4F, "hebrew_presentation"),
    (0xFE70, 0xFEFF, "arabic_presentation_b"),
    (0x0600, 0x06FF, "arabic"),
    (0x0750, 0x077F, "arabic_supp"),
    (0x08A0, 0x08FF, "arabic_ext_a"),
    (0xFB50, 0xFDFF, "arabic_presentation_a"),
    (0xFE70, 0xFEFF, "arabic_presentation_b"),
]
