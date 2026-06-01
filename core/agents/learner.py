from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.reward_system import MultiArmedBandit


class LearnerAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["learner"]), providers)
        self._bandit = MultiArmedBandit(n_arms=3)
        self.register_tool("select_arm", self._select_arm, "Select the best bandit arm")
        self.register_tool("process_feedback", self._process_feedback, "Process user feedback")
        self.register_tool("get_bandit_stats", self._get_stats, "Get bandit statistics")

    def _select_arm(self) -> dict:
        arm = self._bandit.select_arm()
        cfg = self._bandit.get_arm_config(arm)
        return {"arm": arm, "config": cfg, "label": cfg["label"]}

    def _process_feedback(self, arm: int, rating: int) -> dict:
        self._bandit.update(arm, reward=float(rating))
        return {"arm_updated": True, "arm": arm, "rating": rating, "stats": self._bandit.stats()}

    def _get_stats(self) -> dict:
        return self._bandit.stats()

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Learner: analyzing...")
        action = inp.metadata.get("learner_action", "select_arm")
        if action == "process_feedback":
            arm = inp.metadata.get("arm", 0)
            rating = inp.metadata.get("rating", 0)
            result = self._process_feedback(arm, rating)
            self.emit_event("generate", f"Learner: arm {arm} updated with rating {rating}")
        else:
            result = self._select_arm()
            self.emit_event("generate", f"Learner: selected arm {result['arm']} ({result['label']})")
        return AgentOutput(
            success=True,
            content=f"Learner: {action} completed",
            data={"action": action, "result": result, "bandit_stats": self._bandit.stats()},
        )
