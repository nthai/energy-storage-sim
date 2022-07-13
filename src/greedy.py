import gym
from peak_shave_battery import PeakShaveEnergyHub

class GreedyEnv(gym.Env):
    def __init__(self, config: dict) -> None:
        super().__init__()

        self.ehub = PeakShaveEnergyHub(config)
        self.reset()

    def reset(self):
        self.ehub.reset()

    def step(self):
        pass