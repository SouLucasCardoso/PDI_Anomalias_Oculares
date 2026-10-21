"""Reconstrucao da arquitetura registrada antes de carregar um checkpoint polar."""
from pathlib import Path
import torch
from torch import nn
from treinar_identidade_iris import IdentityEncoder

def load(checkpoint,device='cpu'):
    state=torch.load(Path(checkpoint),map_location='cpu',weights_only=True)
    configuration=state['configuration']
    if 'input3x64x512' not in configuration['model']:raise ValueError('Not a polar encoder checkpoint')
    model=IdentityEncoder()
    # MaxPool has no trainable state: state_dict alone cannot recover this change.
    if configuration.get('dense_texture',False):model.backbone.maxpool=nn.Identity()
    model.load_state_dict(state['model'])
    return model.to(device).eval(),configuration
