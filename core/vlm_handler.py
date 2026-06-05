import base64
import logging
import re
from io import BytesIO
from typing import Any

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except ImportError:
    Image = None

DEBUG_VLM_PROMPT = """You are a debug screenshot analyzer. Analyze this image and return a structured result.

1. TEXT EXTRACTION: Extract ALL text visible in the image, especially:
   - Error messages (exact text)
   - Stack traces
   - Line numbers and file paths
   - Terminal/console output

2. CLASSIFICATION:
   - Error type: [SyntaxError | RuntimeError | ImportError | TypeError | ValueError | NameError | KeyError | AttributeError | IndexError | ModuleNotFoundError | FileNotFoundError | IndentationError | Unknown]
   - Language: [Python | JavaScript | TypeScript | Java | C++ | C | Go | Rust | Bash | HTML/CSS | Other]
   - Severity: [Critical | High | Medium | Low]
   - Context: [Terminal | IDE | Browser Console | Log File | Web Page | Other]

3. SUMMARY:
   - One-line description of the issue

Return as structured text:
===EXTRACTED===
[exact error text here]
===TYPE===
[error type]
===LANGUAGE===
[language]
===SEVERITY===
[severity]
===CONTEXT===
[context]
===SUMMARY===
[one-line summary]"""


_VLM_STRUCT_FIELDS = {"EXTRACTED", "TYPE", "LANGUAGE", "SEVERITY", "CONTEXT", "SUMMARY"}


def parse_vlm_output(raw: str) -> dict[str, Any]:
    result = {"extracted": "", "type": "Unknown", "language": "Unknown",
              "severity": "Medium", "context": "Other", "summary": ""}
    current_field = None
    lines = []
    for line in raw.split("\n"):
        stripped = line.strip()
        marker = stripped.strip("=")
        if marker in _VLM_STRUCT_FIELDS and stripped.startswith("===") and stripped.endswith("==="):
            if current_field and lines:
                key = current_field.lower()
                result[key] = "\n".join(lines).strip()
            current_field = marker
            lines = []
        elif current_field:
            lines.append(line)
    if current_field and lines:
        key = current_field.lower()
        result[key] = "\n".join(lines).strip()
    return result


class VLMHandler:
    def __init__(self, providers=None):
        self.providers = providers

    def _query_ollama(self, model: str, base_url: str, image_b64: str) -> str:
        import requests
        payload = {
            "model": model,
            "prompt": DEBUG_VLM_PROMPT,
            "images": [image_b64],
            "stream": False,
        }
        resp = requests.post(f"{base_url.rstrip('/')}/api/generate", json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
        return ""

    def _query_openai_vision(self, model: str, api_url: str, api_key: str, image_b64: str) -> str:
        import requests
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": DEBUG_VLM_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    ],
                }
            ],
            "max_tokens": 2000,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = requests.post(api_url.rstrip("/") + "/chat/completions", json=payload, headers=headers, timeout=120)
        if resp.status_code == 200:
            choices = resp.json().get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        return ""

    def extract_text(self, image: "Image.Image") -> str:
        cfg = self.providers.vlm if self.providers else None
        if not cfg or not cfg.enabled:
            cfg = self.providers.get_llm() if self.providers else None
        base_url = self.providers.get_active_base_url(cfg) if cfg else "http://localhost:11434"
        model = self.providers.get_active_model(cfg, "glm-ocr:latest") if cfg else "glm-ocr:latest"

        try:
            buf = BytesIO()
            image.save(buf, format="PNG")
            buf.seek(0)
            image_b64 = base64.b64encode(buf.read()).decode("utf-8")

            if cfg and cfg.provider_type == "openai" and cfg.api_key:
                api_url = self.providers.get_api_url(cfg)
                return self._query_openai_vision(model, api_url, cfg.api_key, image_b64)
            return self._query_ollama(model, base_url, image_b64)
        except Exception as e:
            logger.error("VLM extract_text failed: %s", e)
            return ""
