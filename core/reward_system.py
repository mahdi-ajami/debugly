import random
import json
from pathlib import Path

from core.config import BANDIT_EPSILON, BANDIT_DECAY, BANDIT_MIN_EPSILON

STATE_FILE = Path(__file__).resolve().parent.parent / "db" / "bandit_state.json"


class MultiArmedBandit:
    def __init__(self, n_arms: int = 3):
        self.n_arms = n_arms
        self.epsilon = BANDIT_EPSILON
        self.counts = [0] * n_arms
        self.values = [0.0] * n_arms
        self._load()

    def select_arm(self) -> int:
        if random.random() < self.epsilon:
            return random.randrange(self.n_arms)
        return max(range(self.n_arms), key=lambda i: self.values[i])

    def update(self, arm: int, reward: float):
        self.counts[arm] += 1
        n = self.counts[arm]
        self.values[arm] += (reward - self.values[arm]) / n
        self.epsilon = max(BANDIT_MIN_EPSILON, self.epsilon * BANDIT_DECAY)
        self._save()

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
