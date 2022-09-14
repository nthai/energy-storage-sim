from gym.spaces import Dict, Discrete, Tuple, MultiBinary, MultiDiscrete
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2
from ray.rllib.utils.typing import ModelConfigDict, TensorType
from ray.rllib.models import ModelCatalog
from ray.rllib.models.torch.fcnet import FullyConnectedNetwork
from ray.rllib.utils.torch_utils import FLOAT_MIN
import gym
import torch.nn as nn
import torch
import numpy as np

from ray.rllib.policy.sample_batch import SampleBatch

# TODO: looks like the state is converted into one-hot encoding and becomes too large for the fcnet

class TorchActionMaskModel(TorchModelV2, nn.Module):
    def __init__(self,
                 obs_space: gym.spaces.Space,
                 action_space: gym.spaces.Space,
                 num_outputs: int,
                 model_config: ModelConfigDict,
                 name: str,
                 **kwargs):

        orig_space = getattr(obs_space, 'original_space', obs_space)

        assert (isinstance(orig_space, Dict) and
                'action_mask' in orig_space.spaces and
                'observations' in orig_space.spaces)

        TorchModelV2.__init__(self, obs_space, action_space, num_outputs,
                              model_config, name, **kwargs)
        nn.Module.__init__(self)

        # print(f'Init {self.__class__.__name__}')
        # print(f'{obs_space=}')
        # print(f'{action_space=}')
        # print(f'{num_outputs=}')
        # print(f'{model_config=}')

        self.internal_model = FullyConnectedNetwork(
            MultiDiscrete([10, 10]),
            action_space,
            num_outputs,
            model_config,
            name + '_internal',
        )

        self.no_masking = False
        if 'no_masking' in model_config['custom_model_config']:
            self.no_masking = model_config['custom_model_config'].get('no_masking', False)
    
    def forward(self, input_dict: SampleBatch, state, seq_lens):
        print('forward called...')
        print(input_dict['obs_flat'].float().shape)
        print(input_dict['obs']['observations'])

        mask = input_dict['obs']['action_mask']

        logits, _ = self.internal_model({'obs': input_dict['obs']['observations']})

        if self.no_masking:
            return logits, state

        inf_mask = torch.clamp(torch.log(mask), min=FLOAT_MIN)
        masked_logits = logits + inf_mask

        return masked_logits, state

    def value_function(self) -> TensorType:
        return self.internal_model.value_function()

ModelCatalog.register_custom_model('torch_action_mask_model', TorchActionMaskModel)

class CustomGridEnv(gym.Env):
    def __init__(self, env_config: dict) -> None:
        super().__init__()

        self.xmax = env_config['xmax']
        self.ymax = env_config['ymax']

        self.action_space = Discrete(4)
        self.observation_space = Dict({
            'observations': MultiDiscrete([self.xmax, self.ymax]),
            'action_mask': MultiBinary(4)
        })

        self.position = [0, 0]
    
    def _get_available_actions(self):
        '''Actions are [ UP RIGHT DOWN LEFT ].'''
        mask = np.array([1, 1, 1, 1])
        if self.position[0] <= 0:
            mask[3] = 0
        if self.position[1] <= 0:
            mask[2] = 0
        if self.position[0] >= self.xmax - 1:
            mask[1] = 0
        if self.position[1] >= self.ymax - 1:
            mask[0] = 0
        
        print(f'{self.position=}, {mask=}')
        return mask

    def _get_observation(self):
        return {
            'observations': tuple(self.position),
            'action_mask': self._get_available_actions()
        }

    def reset(self):
        self.position = [0, 0]
        return self._get_observation()
    
    def step(self, action):
        '''Actions are:
            0: UP
            1: RIGHT
            2: DOWN
            3: LEFT
        '''
        print(f'{action=}')

        if action == 0:
            self.position[1] += 1
            print(self.position)
            assert 0 <= self.position[1] <= self.ymax
        elif action == 1:
            self.position[0] += 1
            print(self.position)
            assert 0 <= self.position[0] <= self.xmax
        elif action == 2:
            self.position[1] -= 1
            print(self.position)
            assert 0 <= self.position[1] <= self.ymax
        elif action == 3:
            self.position[0] -= 1
            print(self.position)
            assert 0 <= self.position[0] <= self.xmax
        
        return self._get_observation(), 0, False, {}

def run_ray():
    import ray
    from ray.rllib.algorithms import ppo

    ray.init()

    algo = ppo.PPO(env=CustomGridEnv, config={
        'framework': 'torch',
        'model': {
            'custom_model': 'torch_action_mask_model',
            'custom_model_config': {
                'no_masking': False
            }
        },
        'env_config': {
            'xmax': 10,
            'ymax': 10
        },
        'disable_env_checking': True # we need this because the env checker selects random actions disregarding the mask
    })
    algo.train()

def test():
    # test env
    env = CustomGridEnv({'xmax': 10, 'ymax': 10})
    obs = env.reset()
    test = env.observation_space.sample()
    print(f'{obs=}\n{test=}')

    print(env.observation_space['observations'])
    orig_space = getattr(env.observation_space, 'original_space', env.observation_space)
    print(orig_space['observations'].shape)

    # test model
    model = TorchActionMaskModel(
        env.observation_space,
        env.action_space,
        1,
        { 'custom_model_config': { 'no_masking': False } },
        'Bela',
    )

if __name__ == '__main__':
    # test()
    run_ray()
