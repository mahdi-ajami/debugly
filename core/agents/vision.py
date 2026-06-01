from PIL import Image
from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.vlm_handler import VLMHandler


class VisionAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["vision"]), providers)
        self._vlm = VLMHandler(providers=self.providers)
        self.register_tool("extract_text_from_image", self._extract_text, "Extract error text from an image file")

    def _extract_text(self, image_path: str) -> str:
        img = Image.open(image_path)
        return self._vlm.extract_text(img)

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Vision: processing images...")
        texts = []
        for img_path in inp.images:
            self.emit_event("tool", f"Vision: extracting text from {img_path}")
            try:
                text = self._extract_text(img_path)
                texts.append(text)
                self.emit_event("generate", f"Vision: extracted {len(text)} chars")
            except Exception as e:
                self.emit_event("error", f"Vision: failed on {img_path}: {e}")
                return AgentOutput(success=False, error=str(e))
        combined = "\n".join(texts)
        inp.metadata["extracted_text"] = combined
        return AgentOutput(success=True, content=combined, data={"extracted_text": combined})
