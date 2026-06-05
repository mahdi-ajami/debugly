import json
import math
import logging
import gc
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime
from typing import Optional
from threading import Lock

from core.config import (
    KNOWLEDGE_BASE_DIR, CHROMA_DB_DIR, COLLECTION_NAME,
    AGENT_RAG_COLLECTIONS,
)
from core.database import get_conn, kb_add as sqlite_kb_add
from db.chroma import ChromaClient

logger = logging.getLogger(__name__)


SEEN_FLAG_KEY = "kb_seeded_v2"

KB_PACKAGES = {
    "error_solutions": {"file": "error_solutions.json", "label": "Python Errors", "collection": "error_solutions"},
    "curated_python": {"file": "curated_python.json", "label": "Python Advanced", "collection": "error_solutions"},
    "curated_javascript": {"file": "curated_javascript.json", "label": "JavaScript/TypeScript", "collection": "code_patterns"},
    "curated_docker": {"file": "curated_docker.json", "label": "Docker", "collection": "best_practices"},
    "curated_git": {"file": "curated_git.json", "label": "Git", "collection": "best_practices"},
    "curated_web_python": {"file": "curated_web_python.json", "label": "Web Python", "collection": "code_patterns"},
    "security_guidelines": {"file": "security_guidelines.json", "label": "Security", "collection": "security_guidelines"},
}

COLLECTION_TO_PACKAGES = defaultdict(list)
for pkg_name, pkg_info in KB_PACKAGES.items():
    COLLECTION_TO_PACKAGES[pkg_info["collection"]].append(pkg_name)


class BM25Index:
    def __init__(self):
        self.corpus: list[dict] = []
        self.doc_freqs: list[Counter] = []
        self.idf: dict[str, float] = {}
        self.avg_doc_len: float = 0
        self.k1: float = 1.5
        self.b: float = 0.75
        self._lock = Lock()

    def _tokenize(self, text: str) -> list[str]:
        return text.lower().split()

    def build(self, documents: list[dict]):
        with self._lock:
            self.corpus = documents
            n_docs = len(documents)
            if n_docs == 0:
                self.doc_freqs = []
                self.idf = {}
                self.avg_doc_len = 0
                return
            self.doc_freqs = []
            total_len = 0
            df: Counter = Counter()
            for doc in documents:
                content = doc.get("content", "")
                tokens = self._tokenize(content)
                self.doc_freqs.append(Counter(tokens))
                total_len += len(tokens)
                for token in set(tokens):
                    df[token] += 1
            self.avg_doc_len = total_len / n_docs
            n_docs_float = float(n_docs)
            self.idf = {}
            for token, doc_count in df.items():
                self.idf[token] = math.log((n_docs_float - doc_count + 0.5) / (doc_count + 0.5) + 1.0)

    def search(self, query: str, k: int = 10) -> list[dict]:
        with self._lock:
            if not self.corpus or not self.idf:
                return []
            query_tokens = self._tokenize(query)
            scores = []
            for i, doc_freq in enumerate(self.doc_freqs):
                score = 0.0
                doc_len = sum(doc_freq.values())
                for token in query_tokens:
                    if token in self.idf and token in doc_freq:
                        tf = doc_freq[token]
                        score += (self.idf[token] * tf * (self.k1 + 1)) / (
                            tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
                        )
                scores.append(score)
            doc_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
            results = []
            for idx in doc_indices:
                doc = dict(self.corpus[idx])
                doc["bm25_score"] = round(scores[idx], 4)
                results.append(doc)
            return results


class KbManager:
    def __init__(self, providers=None):
        self._providers = providers
        self._chroma: Optional[ChromaClient] = None
        self._bm25_indexes: dict[str, BM25Index] = {}
        self._ok = False
        try:
            self._chroma = ChromaClient(providers=providers, collection_name=COLLECTION_NAME)
            self._ok = True
        except Exception as exc:
            logger.warning("KbManager init failed: %s", exc)

    @property
    def chroma(self) -> Optional[ChromaClient]:
        return self._chroma

    def _get_bm25(self, collection: str) -> BM25Index:
        if collection not in self._bm25_indexes:
            self._bm25_indexes[collection] = BM25Index()
        return self._bm25_indexes[collection]

    def ensure_seeded(self):
        conn = get_conn()
        c = conn.cursor()
        already = c.execute(
            "SELECT value FROM settings WHERE key=?", (SEEN_FLAG_KEY,)
        ).fetchone()
        if already:
            return
        count = 0
        for pkg_name, pkg_info in KB_PACKAGES.items():
            file_path = KNOWLEDGE_BASE_DIR / "data" / pkg_info["file"]
            if not file_path.exists():
                continue
            collection = pkg_info["collection"]
            try:
                entries = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to load %s: %s", file_path, exc)
                continue
            for entry in entries:
                self.add_entry(entry, collection)
                count += 1
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (SEEN_FLAG_KEY, datetime.now().isoformat()),
        )
        conn.commit()
        logger.info("KbManager seeded %d entries from curated files", count)

    def add_entry(self, entry: dict, collection: str = COLLECTION_NAME) -> bool:
        title = entry.get("title", "")
        tags = entry.get("tags", [])
        languages = entry.get("languages", [])
        severity = entry.get("severity", "medium")
        steps = entry.get("solution_steps", [])
        code = entry.get("code_example", "")
        error_patterns = entry.get("error_patterns", [])

        error_text = title
        solution_parts = "\n".join(steps) if steps else ""
        if code:
            solution_parts = f"{solution_parts}\n\n```\n{code}\n```"
        solution_text = solution_parts

        content = f"Error: {error_text}\nSolution: {solution_text}"
        meta = {
            "source": entry.get("source", "curated"),
            "error": error_text,
            "collection": collection,
            "tags": ",".join(tags) if tags else "",
            "languages": ",".join(languages) if languages else "",
            "severity": severity,
            "title": title,
            "error_patterns": ",".join(error_patterns) if error_patterns else "",
            "related_topics": ",".join(entry.get("related_topics", [])),
        }

        if self._chroma and self._chroma.ok:
            try:
                old_collection = self._chroma.collection_name
                self._chroma.collection_name = collection
                self._chroma.add_documents([content], [meta])
                self._chroma.collection_name = old_collection
            except Exception as exc:
                logger.warning("Chroma add_entry failed: %s", exc)

        sqlite_kb_add(error_text, solution_text, source=f"curated:{collection}")

        bm25_doc = {"content": content, "title": title, "collection": collection, "error": error_text}
        bm25 = self._get_bm25(collection)
        bm25.build(bm25.corpus + [bm25_doc])

        return True

    def hybrid_search(self, query: str, collection: str = COLLECTION_NAME, k: int = 5) -> list[dict]:
        vector_results = []
        if self._chroma and self._chroma.ok:
            try:
                old = self._chroma.collection_name
                self._chroma.collection_name = collection
                results = self._chroma.search(query, k=k)
                self._chroma.collection_name = old
                vector_results = [
                    {
                        "content": doc.page_content,
                        "source": doc.metadata.get("source", "chroma"),
                        "score": float(score),
                        "title": doc.metadata.get("title", ""),
                        "severity": doc.metadata.get("severity", ""),
                        "tags": doc.metadata.get("tags", ""),
                        "collection": collection,
                    }
                    for doc, score in results if score is not None
                ]
            except Exception as exc:
                logger.warning("Chroma search in %s failed: %s", collection, exc)

        bm25 = self._get_bm25(collection)
        bm25_results = bm25.search(query, k=k)

        scored: dict[str, dict] = {}
        for vr in vector_results:
            key = vr["content"][:100]
            scored[key] = {**vr, "vector_score": vr.get("score", 0), "bm25_score": 0.0}

        for br in bm25_results:
            key = br["content"][:100]
            if key in scored:
                scored[key]["bm25_score"] = br.get("bm25_score", 0)
            else:
                scored[key] = {
                    "content": br["content"],
                    "source": "bm25",
                    "score": 0.0,
                    "vector_score": 0.0,
                    "bm25_score": br.get("bm25_score", 0),
                    "title": br.get("title", ""),
                    "severity": "",
                    "tags": "",
                    "collection": collection,
                }

        fusion_results = []
        for key, doc in scored.items():
            vector_score = doc.get("vector_score", 0)
            bm25_score = doc.get("bm25_score", 0)
            bm25_normalized = min(1.0, bm25_score / 10.0) if bm25_score > 0 else 0
            doc["score"] = 0.7 * vector_score + 0.3 * bm25_normalized
            fusion_results.append(doc)

        fusion_results.sort(key=lambda x: x["score"], reverse=True)
        return fusion_results[:k]

    def search_all_collections(self, query: str, k: int = 3) -> list[dict]:
        all_results = []
        for col_name in AGENT_RAG_COLLECTIONS:
            try:
                results = self.hybrid_search(query, collection=col_name, k=k)
                all_results.extend(results)
            except Exception as exc:
                logger.debug("Search collection %s failed: %s", col_name, exc)
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:k * 3]

    def get_collection_stats(self) -> dict:
        stats = {}
        for col_name, col_desc in AGENT_RAG_COLLECTIONS.items():
            count = 0
            if self._chroma and self._chroma.ok:
                try:
                    old = self._chroma.collection_name
                    self._chroma.collection_name = col_name
                    count = self._chroma.count()
                    self._chroma.collection_name = old
                except Exception:
                    count = 0
            stats[col_name] = {
                "count": count,
                "description": col_desc,
                "packages": COLLECTION_TO_PACKAGES.get(col_name, []),
            }
        conn = get_conn()
        c = conn.cursor()
        sqlite_count = c.execute("SELECT COUNT(*) as cnt FROM kb_entries").fetchone()
        stats["sqlite"] = {"count": sqlite_count["cnt"] if sqlite_count else 0}
        return stats

    def get_entries(self, collection: str = COLLECTION_NAME) -> list[dict]:
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM kb_entries WHERE source LIKE ? ORDER BY created_at DESC LIMIT 200",
            (f"%{collection}%",),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_sqlite(self, query: str, limit: int = 10) -> list[dict]:
        conn = get_conn()
        like = f"%{query}%"
        rows = conn.execute(
            "SELECT * FROM kb_entries WHERE error_text LIKE ? OR solution_text LIKE ? ORDER BY created_at DESC LIMIT ?",
            (like, like, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_entry(self, entry_id: int) -> bool:
        conn = get_conn()
        conn.execute("DELETE FROM kb_entries WHERE id = ?", (entry_id,))
        conn.commit()
        return True

    def update_entry(self, entry_id: int, error_text: str, solution_text: str) -> bool:
        conn = get_conn()
        conn.execute(
            "UPDATE kb_entries SET error_text = ?, solution_text = ? WHERE id = ?",
            (error_text, solution_text, entry_id),
        )
        conn.commit()
        return True

    def import_json(self, file_path: str, collection: str = COLLECTION_NAME) -> int:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            logger.error("Import JSON failed: %s", exc)
            return 0
        if isinstance(data, dict):
            data = [data]
        count = 0
        for entry in data:
            self.add_entry(entry, collection)
            count += 1
        logger.info("Imported %d entries from %s", count, file_path)
        return count

    def import_text(self, file_path: str, collection: str = COLLECTION_NAME) -> int:
        try:
            text = Path(file_path).read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Import text failed: %s", exc)
            return 0
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        count = 0
        for i in range(0, len(lines), 2):
            error_line = lines[i] if i < len(lines) else ""
            solution_line = lines[i + 1] if i + 1 < len(lines) else ""
            if error_line:
                self.add_entry({
                    "title": error_line[:80],
                    "solution_steps": [solution_line],
                    "source": "imported:txt",
                }, collection)
                count += 1
        logger.info("Imported %d entries from %s", count, file_path)
        return count

    def export_collection(self, collection: str = COLLECTION_NAME) -> list[dict]:
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM kb_entries WHERE source LIKE ? ORDER BY id",
            (f"%{collection}%",),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "error_text": r["error_text"],
                "solution_text": r["solution_text"],
                "source": r["source"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def learn_from_feedback(self, query: str, solution: str, collection: str = "feedback_patterns") -> bool:
        entry = {
            "title": f"Learned: {query[:80]}",
            "tags": ["user_feedback", "learned"],
            "languages": [],
            "severity": "medium",
            "error_patterns": [query],
            "solution_steps": [solution],
            "code_example": "",
            "related_topics": [],
            "source": "user_feedback",
        }
        return self.add_entry(entry, collection)

    def rebuild_bm25_index(self, collection: str = COLLECTION_NAME):
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM kb_entries WHERE source LIKE ? LIMIT 500",
            (f"%{collection}%",),
        ).fetchall()
        documents = []
        for r in rows:
            documents.append({
                "content": f"Error: {r['error_text']}\nSolution: {r['solution_text']}",
                "title": r["error_text"][:80],
                "collection": collection,
                "error": r["error_text"],
            })
        bm25 = self._get_bm25(collection)
        bm25.build(documents)
        logger.info("Rebuilt BM25 index for %s with %d docs", collection, len(documents))

    def rebuild_all_bm25(self):
        for col_name in AGENT_RAG_COLLECTIONS:
            self.rebuild_bm25_index(col_name)

    def close(self):
        self._chroma = None
        self._bm25_indexes.clear()
        gc.collect()
