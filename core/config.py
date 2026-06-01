import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLAVA_MODEL = os.getenv("LLAVA_MODEL", "llava")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama3.1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

CHROMA_DB_DIR = PROJECT_ROOT / "db" / "chroma_data"
COLLECTION_NAME = "error_solutions"

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"

MAX_RETRIEVED_DOCS = 5
STREAM_CHUNK_SIZE = 20

BANDIT_EPSILON = 0.1
BANDIT_DECAY = 0.995
BANDIT_MIN_EPSILON = 0.01

UI_TITLE = "Error Assistant"
UI_WIDTH = 1100
UI_HEIGHT = 750
UI_THEME_COLOR = "#1a73e8"
