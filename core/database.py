import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from core.config import DB_PATH

_conn: Optional[sqlite3.Connection] = None
_db_initialized = False


def _init_tables(c):
    c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            root_path TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            active_session_id TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            context TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (project_name) REFERENCES projects(name) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            steps TEXT NOT NULL DEFAULT '[]',
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_key TEXT UNIQUE NOT NULL,
            base_url TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            api_key TEXT NOT NULL DEFAULT '',
            provider_type TEXT NOT NULL DEFAULT 'ollama',
            enabled INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS kb_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_text TEXT NOT NULL,
            solution_text TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'knowledge_base',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feedback_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            arm INTEGER NOT NULL DEFAULT 0,
            rating INTEGER NOT NULL,
            error_text TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            latency_ms REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS approved_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            label TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
    """)
    c.commit()


def get_conn() -> sqlite3.Connection:
    global _conn, _db_initialized
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_tables(_conn)
        _db_initialized = True
    return _conn


def close():
    global _conn
    if _conn:
        _conn.close()
        _conn = None


def project_save(name: str, root_path: str, created_at: str, active_session_id: Optional[str]):
    c = get_conn()
    c.execute("""
        INSERT INTO projects (name, root_path, created_at, active_session_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            root_path=excluded.root_path,
            active_session_id=excluded.active_session_id
    """, (name, root_path, created_at, active_session_id))
    _conn.commit()


def project_load(name: str) -> Optional[dict]:
    c = get_conn()
    r = c.execute("SELECT * FROM projects WHERE name=?", (name,)).fetchone()
    if r:
        return dict(r)
    return None


def project_list() -> list[dict]:
    return [dict(r) for r in get_conn().execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()]


def project_delete(name: str):
    get_conn().execute("DELETE FROM projects WHERE name=?", (name,))
    _conn.commit()


def session_save(session_dict: dict):
    c = get_conn()
    c.execute("""
        INSERT INTO sessions (id, project_name, created_at, updated_at, context)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            project_name=excluded.project_name,
            updated_at=excluded.updated_at,
            context=excluded.context
    """, (
        session_dict["id"],
        session_dict["project_name"],
        session_dict["created_at"],
        session_dict["updated_at"],
        json.dumps(session_dict.get("context", {}), ensure_ascii=False),
    ))
    c.execute("DELETE FROM messages WHERE session_id=?", (session_dict["id"],))
    for m in session_dict.get("messages", []):
        c.execute(
            "INSERT INTO messages (session_id, role, content, timestamp, steps) VALUES (?, ?, ?, ?, ?)",
            (session_dict["id"], m["role"], m["content"], m.get("timestamp", ""),
             json.dumps(m.get("steps", []), ensure_ascii=False)),
        )
    _conn.commit()
    project_save(
        name=session_dict["project_name"],
        root_path="",
        created_at=session_dict["created_at"],
        active_session_id=session_dict["id"],
    )


def session_load(session_id: str) -> Optional[dict]:
    c = get_conn()
    r = c.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not r:
        return None
    s = dict(r)
    s["context"] = json.loads(s.get("context", "{}"))
    s["messages"] = []
    for m in c.execute("SELECT * FROM messages WHERE session_id=? ORDER BY id", (session_id,)):
        msg = dict(m)
        msg["steps"] = json.loads(msg.get("steps", "[]"))
        s["messages"].append(msg)
    return s


def session_list(project_name: str) -> list[dict]:
    c = get_conn()
    rows = c.execute("""
        SELECT s.id, s.created_at, s.updated_at,
               COALESCE((SELECT content FROM messages WHERE session_id=s.id ORDER BY id DESC LIMIT 1), '') as preview
        FROM sessions s WHERE s.project_name=?
        ORDER BY s.updated_at DESC
    """, (project_name,)).fetchall()
    return [{"id": r["id"], "created_at": r["created_at"], "updated_at": r["updated_at"],
             "preview": (r["preview"] or "")[:60]} for r in rows]


def session_delete(session_id: str):
    get_conn().execute("DELETE FROM sessions WHERE id=?", (session_id,))
    _conn.commit()


def providers_save(providers_dict: dict):
    c = get_conn()
    for key, cfg in providers_dict.items():
        c.execute("""
            INSERT INTO providers (provider_key, base_url, model, api_key, provider_type, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider_key) DO UPDATE SET
                base_url=excluded.base_url, model=excluded.model,
                api_key=excluded.api_key, provider_type=excluded.provider_type,
                enabled=excluded.enabled
        """, (key, cfg.get("base_url", ""), cfg.get("model", ""),
              cfg.get("api_key", ""), cfg.get("provider_type", "ollama"),
              1 if cfg.get("enabled") else 0))
    _conn.commit()


def providers_load() -> dict:
    c = get_conn()
    result = {}
    for r in c.execute("SELECT * FROM providers"):
        result[r["provider_key"]] = {
            "base_url": r["base_url"],
            "model": r["model"],
            "api_key": r["api_key"],
            "provider_type": r["provider_type"],
            "enabled": bool(r["enabled"]),
        }
    return result


def kb_add(error_text: str, solution_text: str, source: str = "knowledge_base"):
    c = get_conn()
    c.execute(
        "INSERT INTO kb_entries (error_text, solution_text, source, created_at) VALUES (?, ?, ?, ?)",
        (error_text, solution_text, source, datetime.now().isoformat()),
    )
    _conn.commit()


def kb_search(query: str, limit: int = 10) -> list[dict]:
    c = get_conn()
    like = f"%{query}%"
    rows = c.execute("""
        SELECT * FROM kb_entries
        WHERE error_text LIKE ? OR solution_text LIKE ?
        ORDER BY created_at DESC LIMIT ?
    """, (like, like, limit)).fetchall()
    return [dict(r) for r in rows]


def setting_get(key: str, default: str = "") -> str:
    r = get_conn().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def setting_set(key: str, value: str):
    get_conn().execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    _conn.commit()


def feedback_log_add(session_id: str, arm: int, rating: int, error_text: str, model: str, latency_ms: float = 0):
    c = get_conn()
    c.execute(
        "INSERT INTO feedback_log (session_id, arm, rating, error_text, model, latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session_id, arm, rating, error_text[:200], model, latency_ms, datetime.now().isoformat()),
    )
    _conn.commit()


def feedback_log_list(limit: int = 50) -> list[dict]:
    return [dict(r) for r in get_conn().execute(
        "SELECT * FROM feedback_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()]


def approved_sites_list() -> list[dict]:
    return [dict(r) for r in get_conn().execute(
        "SELECT * FROM approved_sites ORDER BY label"
    ).fetchall()]


def approved_site_add(url: str, label: str = ""):
    get_conn().execute(
        "INSERT OR IGNORE INTO approved_sites (url, label, enabled, created_at) VALUES (?, ?, 1, ?)",
        (url, label, datetime.now().isoformat()),
    )
    _conn.commit()


def approved_site_toggle(site_id: int, enabled: bool):
    get_conn().execute("UPDATE approved_sites SET enabled=? WHERE id=?", (1 if enabled else 0, site_id))
    _conn.commit()


def approved_site_delete(site_id: int):
    get_conn().execute("DELETE FROM approved_sites WHERE id=?", (site_id,))
    _conn.commit()


def seed_approved_sites():
    defaults = [
        ("https://stackoverflow.com/questions", "Stack Overflow"),
        ("https://developer.mozilla.org", "MDN Web Docs"),
        ("https://docs.python.org/3", "Python Docs"),
        ("https://react.dev/reference", "React Reference"),
        ("https://docs.npmjs.com", "npm Docs"),
        ("https://learn.microsoft.com/en-us/dotnet", ".NET Docs"),
        ("https://pkg.go.dev", "Go Packages"),
        ("https://docs.rs", "Rust Docs"),
        ("https://docs.docker.com", "Docker Docs"),
        ("https://kubernetes.io/docs", "K8s Docs"),
    ]
    for url, label in defaults:
        approved_site_add(url, label)
