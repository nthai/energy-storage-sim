from gym.spaces import Space, Dict
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2
from ray.rllib.utils.typing import ModelConfigDict
from ray.rllib.utils.typing import TensorType
from ray.rllib.models.torch.fcnet import FullyConnectedNetwork
from ray.rllib.policy.sample_batch import SampleBatch
from ray.rllib.utils.torch_utils import FLOAT_MIN
from ray.rllib.models import ModelCatalog

import gym
import torch
import torch.nn as nn

class TorchActionMaskModel(TorchModelV2, nn.Module):
    def __init__(self,
                 obs_space: Space,
                 action_space: Space,
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

        self.internal_model = FullyConnectedNetwork(
            orig_space['observations'],
            action_space,
            num_outputs,
            model_config,
            name + '_internal'
        )

    def forward(self, input_dict: SampleBatch, state, seq_lens):
        
        mask = input_dict['obs']['action_mask']

        logits, _ = self.internal_model({'obs': input_dict['obs']['observations']})

        inf_mask = torch.clamp(torch.log(mask), min=FLOAT_MIN)
        masked_logits = logits + inf_mask

        return masked_logits, state
    
    def value_function(self) -> TensorType:
        return self.internal_model.value_function()

if __name__ == '__main__':
    ModelCatalog.register_custom_model('torch_action_mask_model', TorchActionMaskModel)
