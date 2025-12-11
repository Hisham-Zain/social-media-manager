import logging
import random

import pandas as pd

from .world_sim import GeminiWorldSim

logger = logging.getLogger(__name__)


class RLScheduler:
    """
    Learns the optimal posting schedule by playing against the World Sim.
    """

    def __init__(self) -> None:
        self.env: GeminiWorldSim = GeminiWorldSim()
        self.q_table: dict[tuple[str, int], float] = {}
        self.days: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.hours: list[int] = [9, 12, 15, 18, 21]
        self.alpha: float = 0.1
        self.epsilon: float = 0.2

    def train(self, content_topic: str, episodes: int = 10) -> pd.DataFrame:
        """Train the scheduler on a content topic."""
        logger.info(f"🏋️‍♂️ Training Schedule Agent on: '{content_topic}'")

        for _ in range(episodes):
            # Explore vs Exploit
            if random.random() < self.epsilon:
                day, hour = random.choice(self.days), random.choice(self.hours)
            else:
                day, hour = self.get_best_action()

            # Get Reward from Simulator
            reward = self.env.get_reward(content_topic, day, hour)

            # Q-Learning Update
            old_val = self.q_table.get((day, hour), 0)
            new_val = old_val + self.alpha * (reward - old_val)
            self.q_table[(day, hour)] = new_val

        return self.get_results_df()

    def get_best_action(self) -> tuple[str, int]:
        """Get the best day/hour action based on Q-table."""
        if not self.q_table:
            return random.choice(self.days), random.choice(self.hours)
        return max(self.q_table, key=lambda k: self.q_table[k])

    def get_results_df(self) -> pd.DataFrame:
        """Return Q-table as a sorted DataFrame."""
        data = [
            {"Day": d, "Hour": f"{h}:00", "Score": s}
            for (d, h), s in self.q_table.items()
        ]
        df = pd.DataFrame(data)
        return df.sort_values(by="Score", ascending=False) if not df.empty else df
