from .custom_model import TorchActionMaskModel
from .ehub_env import EhubEnv

from typing import Dict, Union

import argparse
import ray
from ray.rllib.algorithms import ppo
from ray.rllib.algorithms.callbacks import DefaultCallbacks
from ray.rllib.env import BaseEnv
from ray.rllib.policy import Policy
from ray.rllib.evaluation import Episode, RolloutWorker
from pprint import pprint

class LoggerCallback(DefaultCallbacks):

    def on_episode_start(self, *, worker: "RolloutWorker", base_env: BaseEnv,
                         policies: Dict[str, Policy], episode: Episode,
                         **kwargs) -> None:
        pass

    def on_episode_step(self, *, worker: "RolloutWorker", base_env: BaseEnv,
                        policies: Dict[str, Policy], episode: Episode,
                        **kwargs) -> None:
        info = episode.last_info_for()
        print(f"deltasoc: {info['deltasoc']:5.1f}, soc: {info['soc']:.2f}, trafoload: {info['trafoload']:5.1f}")

    def on_episode_end(self, *, worker: "RolloutWorker", base_env: BaseEnv,
                       policies: Dict[str, Policy], episode: Episode,
                       **kwargs) -> None:
        pass

def parse_args():
    parser = argparse.ArgumentParser('Ehub Environment in RLlib')
    parser.add_argument('--fname', type=str, help='Input file containing')

    args = parser.parse_args()
    return args

def run_ray():
    args = parse_args()

    algo = ppo.PPO(env=EhubEnv, config={
        'framework': 'torch',
        'model': {
            'custom_model': TorchActionMaskModel,
            'custom_model_config': {}
        },
        'env_config': {
            'filename': args.fname,
            'ehub_config': {
                'LiIonBattery': 2,
                'Flywheel': 2,
                'Supercapacitor': 2
            },
            'trafo_max_power': 100,
            'trafo_nominal_power': 90,
            'eval_mode': False,
        },
        'disable_env_checking': True,
        'batch_mode': 'complete_episodes',
        'evaluation_num_workers': 1,
        'evaluation_config': {
            'callbacks': LoggerCallback,
            'env_config': {
                'eval_mode': True
            }
        },
    })

    for _ in range(10): # modify this line for fewer or more training loops
        res = algo.train()
        pprint(f"{res['episode_reward_max']=}")
        pprint(f"{res['episode_reward_mean']=}")
        pprint(f"{res['episode_reward_min']=}\n")
    
    res = algo.evaluate()
    res = res['evaluation']    

    pprint(f"{res['episode_reward_max']=}")
    pprint(f"{res['episode_reward_mean']=}")
    pprint(f"{res['episode_reward_min']=}\n")

if __name__ == '__main__':
    ray.init()
    run_ray()
