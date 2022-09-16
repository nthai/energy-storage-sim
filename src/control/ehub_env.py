import os
import gym
import numpy as np
import gym.spaces as spaces
import pandas as pd

from ..common.batteries import EnergyHub
from ..common.battery import IdealBattery
from ..common.util import process_file

MAXSOC = 100
class EhubEnv(gym.Env):
    def __init__(self, config: dict) -> None:
        # print(config)
        super().__init__()
        self.action_count = 21
        self.action_space = spaces.Discrete(21)
        # observation is (timestamp, soc, net load)
        # consider net load in a narrower range?
        self.observation_space = spaces.Dict({
            'action_mask': spaces.MultiBinary(21),
            'observations': spaces.Box(low=np.array([0, 0, 0, -float('inf')]),
                                       high=np.array([366, 24, MAXSOC, float('inf')]))
        })
        self.df_length = None
        self.df = self._load_file(config['filename'])
        self.ehub = EnergyHub(config['ehub_config'])
        self.trafo_maxpower = config['trafo_max_power']
        self.trafo_nompower = config['trafo_nominal_power']
        self.eval_mode = config['eval_mode']
    
    def reset(self):
        self.soc = 0 # state of charge
        self.prev_action = 0 # action in the previous timestep
        self.timestep = 0
        self.battery = IdealBattery()

        return self._get_observation()

    def step(self, action):
        '''Makes one step in the environment. Currently this step is 1-hour in time.
        Args:
            - action: int, selecting the action. Use the `action_mask` from the
                      observation dict to see what are the possible actions in the
                      current state. The action value determines the amount of
                      $\Delta SOC$. E.g. 0 is discharge with -100 kW, and 21 is
                      charge with +100 kW.
        '''

        trafo_load = self.df.iloc[self.timestep]['net']

        deltasoc = self.prev_action * 10 - 100
        tcharge = tdisch = tselfdis = tpen = pdemand = None
        if deltasoc > 0:
            tcharge, tselfdis, tpen, pdemand = self.ehub.charge(deltasoc)
            trafo_load += deltasoc
        elif deltasoc < 0:
            tdisch, tselfdis, tpen, pdemand = self.ehub.discharge(-deltasoc)
            pgain = deltasoc - pdemand
            trafo_load -= pgain
        info = {
            'total_charge': tcharge,
            'total_discharge': tdisch,
            'total_selfdischarge': tselfdis,
            'total_penalty': tpen,
            'pdemand': pdemand,
            'deltasoc': deltasoc,
            'trafoload': trafo_load,
        }

        if self.eval_mode:
            info['soc'] = self.ehub.get_soc()

        reward = self._get_reward(trafo_load)

        self.prev_action = action
        self.timestep += 1
        done = (self.timestep >= self.df_length - 1)

        return (self._get_observation(),
                reward,
                done,
                info)

    def _get_available_actions(self) -> np.ndarray:
        mask = np.zeros(self.action_count)
        for idx in range(self.action_count):
            if 0 <= idx * 10 - 100 + self.battery.soc <= 100:
                mask[idx] = 1
        return mask
    
    def _get_observation(self):
        # TODO: question: should we use the net load of this timestep
        # or the net load of the previous timestep?
        row = self.df.iloc[self.timestep]
        return {
            'observations': np.array([row['day'], row['hour'], self.soc, row['net']]),
            'action_mask': self._get_available_actions()
        }
    
    def _load_file(self, fname: str) -> pd.DataFrame:
        fname = f'{os.getcwd()}/{fname}'
        print(f'Loading from {fname}')
        
        df = process_file(fname)
        self.df_length = len(df)

        # convert ['timestamp'] to ['day', 'hour']
        df['day'] = df['timestamp'].dt.day_of_year.astype(float)
        df['hour'] = df['timestamp'].dt.hour.astype(float)

        df = df[['day', 'hour', 'net']]
        return df

    def _get_reward(self, trafo_load: float) -> float:
        # TODO: find a function to implement reward; function should depend
        # on self.trafo_maxpower, self.trafo_nompower, and trafo_load

        penalty = (self.trafo_nompower - trafo_load) ** 2
        if trafo_load > self.trafo_maxpower:
            penalty += (trafo_load - self.trafo_maxpower) ** 2

        return -penalty/10000.0 # divide it by 1000 to avoid very large numbers

if __name__ == '__main__':
    print(__package__)

    config = {
        'filename': '../../data/Sub71125.csv',
        'ehub_config': {
            'LiIonBattery': 2,
            'Flywheel': 2,
            'Supercapacitor': 2
        }
    }

    env = EhubEnv(config)
