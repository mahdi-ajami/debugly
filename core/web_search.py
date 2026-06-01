import logging
import re
import urllib.parse
from typing import Optional

import requests

from core.database import approved_sites_list

logger = logging.getLogger("debugly")

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Debugly/1.0"

_SEARCH_CACHE = {}


def _site_domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return url.lower()


def _is_allowed(url: str) -> bool:
    domain = _site_domain(url)
    sites = approved_sites_list()
    for s in sites:
        if not s.get("enabled", 1):
            continue
        allowed = _site_domain(s["url"])
        if domain == allowed or domain.endswith("." + allowed):
            return True
    return False


def _fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    try:
        resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=timeout)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "text" not in content_type and "json" not in content_type:
            return None
        text = resp.text
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000]
    except requests.RequestException as e:
        logger.debug("fetch_page failed for %s: %s", url, e)
        return None


def search_web(query: str, max_results: int = 3) -> list[dict]:
    sites = approved_sites_list()
    enabled = [s for s in sites if s.get("enabled", 1)]
    if not enabled:
        return []

    query_clean = re.sub(r"[^\w\s]", " ", query).strip()
    keywords = [w.lower() for w in query_clean.split() if len(w) > 2]

    results = []
    for site in enabled:
        url = site["url"]
        label = site.get("label", url)
        search_url = url.rstrip("/")

        if "stackoverflow.com" in url:
            search_url = f"https://api.stackexchange.com/2.3/search/excerpts?order=desc&sort=relevance&site=stackoverflow&q={urllib.parse.quote(query)}"
            try:
                resp = requests.get(search_url, headers={"User-Agent": _USER_AGENT}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", [])[:max_results]:
                        title = item.get("title", "")
                        excerpt = item.get("excerpt", "")[:500]
                        link = f"https://stackoverflow.com/questions/{item.get('question_id')}"
                        results.append({
                            "source": f"Stack Overflow: {title[:60]}",
                            "url": link,
                            "content": excerpt,
                            "site_label": "Stack Overflow",
                            "score": round(item.get("score", 0) / 100, 3),
                        })
                continue
            except requests.RequestException:
                pass

        if "developer.mozilla.org" in url:
            search_url = f"https://developer.mozilla.org/api/v1/search?q={urllib.parse.quote(query)}&locale=en-US"
            try:
                resp = requests.get(search_url, headers={"User-Agent": _USER_AGENT}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("documents", [])[:max_results]:
                        title = item.get("title", "")
                        summary = item.get("summary", "")[:500]
                        slug = item.get("slug", "")
                        link = f"https://developer.mozilla.org/en-US/docs/{slug}"
                        results.append({
                            "source": f"MDN: {title}",
                            "url": link,
                            "content": summary,
                            "site_label": "MDN Web Docs",
                            "score": 0.7,
                        })
                continue
            except requests.RequestException:
                pass

        if "docs.python.org" in url:
            page = _fetch_page(f"https://docs.python.org/3/search.html?q={urllib.parse.quote(query)}")
            if page:
                results.append({
                    "source": f"Python Docs: {query[:40]}",
                    "url": f"https://docs.python.org/3/search.html?q={urllib.parse.quote(query)}",
                    "content": page[:600],
                    "site_label": "Python Docs",
                    "score": 0.5,
                })
            continue

        page = _fetch_page(search_url)
        if page:
            results.append({
                "source": f"{label}: {query[:40]}",
                "url": search_url,
                "content": page[:600],
                "site_label": label,
                "score": 0.3,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]
