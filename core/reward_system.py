import random
import json
from pathlib import Path

from core.config import BANDIT_EPSILON, BANDIT_DECAY, BANDIT_MIN_EPSILON

STATE_FILE = Path(__file__).resolve().parent.parent / "db" / "bandit_state.json"


ARM_CONFIGS = [
    {"temperature": 0.1, "prompt_style": "precise", "num_docs": 3, "label": "Conservative"},
    {"temperature": 0.5, "prompt_style": "balanced", "num_docs": 5, "label": "Balanced"},
    {"temperature": 0.8, "prompt_style": "creative", "num_docs": 7, "label": "Creative"},
]


class MultiArmedBandit:
    def __init__(self, n_arms: int = 3):
        self.n_arms = min(n_arms, len(ARM_CONFIGS))
        self.epsilon = BANDIT_EPSILON
        self.counts = [0] * self.n_arms
        self.values = [0.0] * self.n_arms
        self._load()

    def select_arm(self) -> int:
        if random.random() < self.epsilon:
            return random.randrange(self.n_arms)
        return max(range(self.n_arms), key=lambda i: self.values[i])

    def get_arm_config(self, arm: int) -> dict:
        return ARM_CONFIGS[arm % len(ARM_CONFIGS)]

    def update(self, arm: int, reward: float):
        self.counts[arm] += 1
        n = self.counts[arm]
        self.values[arm] += (reward - self.values[arm]) / n
        self.epsilon = max(BANDIT_MIN_EPSILON, self.epsilon * BANDIT_DECAY)
        self._save()

    def stats(self) -> dict:
        return {
            "epsilon": round(self.epsilon, 4),
            "counts": self.counts,
            "values": [round(v, 4) for v in self.values],
            "arms": [
                {"index": i, "label": ARM_CONFIGS[i]["label"], "count": self.counts[i], "value": round(self.values[i], 4)}
                for i in range(self.n_arms)
            ],
        }

    def _save(self):
        data = {
            "epsilon": self.epsilon,
            "counts": self.counts,
            "values": self.values,
        }
        STATE_FILE.write_text(json.dumps(data, indent=2))

    def _load(self):
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                self.epsilon = data["epsilon"]
                self.counts = data["counts"]
                self.values = data["values"]
            except (json.JSONDecodeError, KeyError):
                pass
