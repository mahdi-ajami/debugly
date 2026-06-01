import base64
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except ImportError:
    Image = None


class VLMHandler:
    def __init__(self, providers=None):
        self.providers = providers

    def _query_ollama(self, model: str, base_url: str, image_b64: str) -> str:
        import requests
        payload = {
            "model": model,
            "prompt": "Extract any error message text from this image. Return only the error text, nothing else.",
            "images": [image_b64],
            "stream": False,
        }
        resp = requests.post(f"{base_url.rstrip('/')}/api/generate", json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
        return ""

    def extract_text(self, image: "Image.Image") -> str:
        cfg = self.providers.get_llm() if self.providers else None
        base_url = self.providers.get_active_base_url(cfg) if cfg else "http://localhost:11434"
        model = self.providers.get_active_model(cfg, "llava:7b") if cfg else "llava:7b"

        try:
            buf = BytesIO()
            image.save(buf, format="PNG")
            buf.seek(0)
            image_b64 = base64.b64encode(buf.read()).decode("utf-8")
            return self._query_ollama(model, base_url, image_b64)
        except Exception as e:
            logger.error("VLM extract_text failed: %s", e)
            return f"Failed to extract text: {e}"
