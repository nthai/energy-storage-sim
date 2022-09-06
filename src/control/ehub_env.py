import gym
import numpy as np
import gym.spaces as spaces

from ..common.battery import IdealBattery

MAXSOC = 100
class EhubEnv(gym.Env):
    def __init__(self, config) -> None:
        super().__init__()
        self.action_count = 21
        self.action_space = spaces.Discrete(21)
        self.observation_space = spaces.Dict({
            'action_mask': spaces.Discrete(21),
            'real_obs': spaces.Box(low=np.array([0, 0, -float('inf')]),
                                   high=np.array([float('inf'), MAXSOC, float('inf')]))
        })
    
    def reset(self):
        self.battery = IdealBattery()

    def step(self, action):
        obs = None
        reward = 0
        done = False
        info = None

        return obs, reward, done, info

    def _get_available_actions(self):
        mask = np.zeros(self.action_count)
        for idx in range(self.action_count):
            if 0 <= idx * 10 - 100 + self.battery.soc <= 100:
                mask[idx] = 1
        return mask

if __name__ == '__main__':
    print(__package__)
    env = EhubEnv({})
