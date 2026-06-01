import base64
from io import BytesIO
from PIL import Image
import ollama

from core.config import OLLAMA_BASE_URL, LLAVA_MODEL


class VLMHandler:
    def __init__(self):
        self.client = ollama.Client(host=OLLAMA_BASE_URL)
        self.model = LLAVA_MODEL

    def _encode_image(self, image: Image.Image) -> str:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def extract_text(self, image: Image.Image) -> str:
        b64 = self._encode_image(image)
        response = self.client.generate(
            model=self.model,
            prompt="Extract all error messages and error text visible in this screenshot. "
                   "Return only the extracted text, nothing else.",
            images=[b64],
        )
        return response.get("response", "").strip()
