from .custom_model import TorchActionMaskModel
from .ehub_env import EhubEnv

import argparse
import ray
from ray.rllib.algorithms import ppo
from pprint import pprint

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
        },
        'disable_env_checking': True,
        'batch_mode': 'complete_episodes',
    })

    res = algo.train()
    pprint(res)
    
if __name__ == '__main__':
    ray.init()
    run_ray()
