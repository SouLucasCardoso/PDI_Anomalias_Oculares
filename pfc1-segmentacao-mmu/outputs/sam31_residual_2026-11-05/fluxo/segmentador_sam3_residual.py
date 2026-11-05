"""Correcao residual supervisionada com SAM3.1 e controle RGB+SAM3 congelado."""
import torch
from torch import nn
from torch.nn import functional as F

from segmentador_sam3_iris import IrisSam3Adapter, SAM_REVISION
from treinar_segmentacao_ubipr import MulticlassUNet

MODEL_TYPE = 'sam3_visual_iris_residual'
MODEL_CONFIG = {'width': 416, 'height': 320, 'residual_channels': 32, 'residual_logit_bound': 4.0}


class ResidualDecoder(MulticlassUNet):
    def __init__(self):
        super().__init__(32, 4)
        self.sam_projection = nn.Sequential(nn.Conv2d(256, 64, 1), nn.GELU(), nn.Conv2d(64, 256, 1))
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, rgb, features):
        e1 = self.enc1(rgb)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        middle = self.middle(self.pool(e3))
        semantic = self.sam_projection(features.to(dtype=rgb.dtype))
        middle = middle + F.interpolate(semantic, size=middle.shape[-2:], mode='bilinear', align_corners=False)
        value = self.dec3(torch.cat((self.up3(middle), e3), 1))
        value = self.dec2(torch.cat((self.up2(value), e2), 1))
        return self.output(self.dec1(torch.cat((self.up1(value), e1), 1)))


class IrisSam3Residual(nn.Module):
    def __init__(self):
        super().__init__()
        self.base = IrisSam3Adapter().requires_grad_(False).eval()
        self.correction = ResidualDecoder()

    def train(self, mode=True):
        super().train(mode)
        self.base.eval()  # Preserva tambem estatisticas BatchNorm do controle.
        return self

    def initialize(self, parent_state):
        self.base.load_state_dict(parent_state, strict=True)
        self.base.requires_grad_(False).eval()

    def forward(self, rgb, features):
        with torch.no_grad():
            baseline = self.base(rgb, features)
        correction = self.correction(rgb, features).float()
        return baseline.float() + MODEL_CONFIG['residual_logit_bound'] * torch.tanh(correction)


def load_checkpoint(state, device='cpu'):
    if state.get('sam_revision') != SAM_REVISION:
        raise ValueError('Revisao SAM3 divergente')
    if state.get('model_type') == MODEL_TYPE:
        if state.get('configuration') != MODEL_CONFIG:
            raise ValueError('Configuracao residual divergente')
        model = IrisSam3Residual()
    elif state.get('model_type') == 'sam3_visual_iris_adapter':
        model = IrisSam3Adapter()
    else:
        raise ValueError('Familia de segmentador desconhecida')
    model.load_state_dict(state['model'], strict=True)
    return model.to(device).eval()
