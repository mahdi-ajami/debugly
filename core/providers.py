import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import requests

from core.config import PROVIDERS_FILE, OLLAMA_BASE_URL
from core.database import providers_save as db_save, providers_load as db_load


@dataclass
class ProviderConfig:
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    provider_type: str = "ollama"
    enabled: bool = False


_CODE_PATTERNS = re.compile(
    r'(traceback|stack trace|error|exception|syntaxerror|importerror|typeerror|valueerror|'
    r'keyerror|attributeerror|indexerror|nameerror|modulenotfounderror|filenotfounderror|'
    r'zerodivisionerror|runtimeerror|stopiteration|recursionerror|'
    r'os\.path|sys\.stdout|def |class |import |from |return |'
    r'print\(|\.py\b|\.js\b|\.ts\b|\.java\b|\.cpp\b|\.c\b|\.h\b|'
    r'<!doctype|<html|<script|<style|function |const |let |var |'
    r'```\w*\n|#include|package |public class)',
    re.IGNORECASE,
)


@dataclass
class ProviderManager:
    llm: ProviderConfig = field(default_factory=ProviderConfig)
    vlm: ProviderConfig = field(default_factory=ProviderConfig)
    chat: ProviderConfig = field(default_factory=ProviderConfig)
    code: ProviderConfig = field(default_factory=ProviderConfig)
    embedding: ProviderConfig = field(default_factory=ProviderConfig)

    def get_llm(self, query_hint: str | None = None) -> ProviderConfig:
        if query_hint and _CODE_PATTERNS.search(query_hint):
            if self.code.enabled:
                return self.code
        elif query_hint and self.chat.enabled:
            return self.chat
        if self.code.enabled:
            return self.code
        return self.llm

    def get_active_base_url(self, provider: ProviderConfig) -> str:
        return provider.base_url or OLLAMA_BASE_URL

    def get_active_model(self, provider: ProviderConfig, default: str) -> str:
        return provider.model or default

    def get_api_url(self, provider: ProviderConfig) -> str:
        base = self.get_active_base_url(provider).rstrip("/")
        if provider.provider_type == "openai" and not base.endswith("/v1"):
            return base + "/v1"
        return base

    @staticmethod
    def fetch_available_models(provider_type: str, base_url: str) -> list[str]:
        url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        try:
            if provider_type == "ollama":
                resp = requests.get(f"{url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    return [m["name"] for m in models]
            elif provider_type == "openai":
                api_url = url + "/v1/models" if not url.endswith("/v1") else url + "/models"
                resp = requests.get(api_url, timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    return sorted([m["id"] for m in models])
        except Exception:
            pass
        return []

    def to_dict(self) -> dict:
        return {
            "llm": asdict(self.llm),
            "vlm": asdict(self.vlm),
            "chat": asdict(self.chat),
            "code": asdict(self.code),
            "embedding": asdict(self.embedding),
        }

    @classmethod
    def from_dict(cls, data: dict):
        mgr = cls()
        for key in ("llm", "vlm", "chat", "code", "embedding"):
            if key in data:
                setattr(mgr, key, ProviderConfig(**data[key]))
        return mgr

    def save(self):
        PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROVIDERS_FILE.write_text(
            json.dumps(self.to_dict(), indent=2),
            encoding="utf-8",
        )
        db_save(self.to_dict())

    @classmethod
    def load(cls):
        data = db_load()
        if data:
            return cls.from_dict(data)
        if PROVIDERS_FILE.exists():
            try:
                data = json.loads(PROVIDERS_FILE.read_text(encoding="utf-8"))
                mgr = cls.from_dict(data)
                mgr.save()
                return mgr
            except (json.JSONDecodeError, KeyError):
                pass
        return cls()
