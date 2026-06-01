"""Run this script to populate the knowledge base with seed data.

Usage:
    python scripts/seed_kb.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_base.seed import get_seed_documents
from db.chroma import ChromaClient


def main():
    client = ChromaClient()
    texts, metadatas = get_seed_documents()
    client.add_documents(texts, metadatas)
    print(f"Seeded {len(texts)} documents into ChromaDB.")


if __name__ == "__main__":
    main()
