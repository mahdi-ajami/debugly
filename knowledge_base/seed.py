"""Seed the knowledge base with curated error solutions.

Uses KbManager to load all JSON data files from knowledge_base/data/
into ChromaDB vector store + SQLite for hybrid search.

Consolidates 173 curated entries across 7 packages:
  - error_solutions.json      (Python common errors)
  - curated_python.json       (Advanced Python debugging)
  - curated_javascript.json   (JS/TS/React solutions)
  - curated_docker.json       (Docker/compose fixes)
  - curated_git.json          (Git recovery)
  - curated_web_python.json   (FastAPI/Django/Flask)
  - security_guidelines.json  (OWASP security)
"""

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

logger = logging.getLogger("seed_kb")


def seed_all():
    """Load all curated JSON files into KbManager."""
    from core.kb_manager import KbManager
    from core.providers import ProviderManager
    providers = ProviderManager.load()
    mgr = KbManager(providers=providers)
    mgr.ensure_seeded()
    stats = mgr.get_collection_stats()
    total = stats.get("sqlite", {}).get("count", 0)
    mgr.close()
    return total


if __name__ == "__main__":
    count = seed_all()
    print(f"Seeded {count} entries into ChromaDB + SQLite")
