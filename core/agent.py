from core.vlm_handler import VLMHandler
from core.rag_pipeline import RAGPipeline
from core.reward_system import MultiArmedBandit
from models.schemas import AgentState


class DebugAgent:
    def __init__(self):
        self.vlm = VLMHandler()
        self.rag = RAGPipeline()
        self.bandit = MultiArmedBandit(n_arms=3)

    def extract_error(self, image_path: str) -> str:
        from PIL import Image
        image = Image.open(image_path)
        return self.vlm.extract_text(image)

    def solve(self, error_text: str, stream: bool = False):
        state = AgentState(error_text=error_text)
        state.arm_selected = self.bandit.select_arm()

        result, docs = self.rag.invoke(error_text, stream=stream)
        state.retrieved_docs = docs

        if stream:
            return result, state
        state.solution = result
        return state

    def handle_feedback(self, arm: int, rating: int):
        self.bandit.update(arm, reward=float(rating))
