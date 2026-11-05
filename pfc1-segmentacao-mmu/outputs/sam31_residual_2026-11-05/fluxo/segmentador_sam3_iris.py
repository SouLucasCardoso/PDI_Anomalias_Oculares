"""SAM3.1 visual congelado e decodificador supervisionado de iris.

Nao e o segmentador textual original nem ajuste integral do SAM3. A projecao
inicialmente nula preserva o controle RGB antes do aprendizado supervisionado.
"""
from __future__ import annotations
import gc
import importlib.metadata
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F

from treinar_segmentacao_ubipr import MulticlassUNet
from treinar_segmentacao_diversa import diverse_loss

ROOT = Path(__file__).resolve().parent
SAM_REVISION = 'f1647e8d0c1d280991f4d1b7d974c2704537fe66'


class IrisSam3Adapter(MulticlassUNet):
    def __init__(self):
        super().__init__(8, 4)
        self.sam_projection = nn.Sequential(nn.Conv2d(256,32,1),nn.GELU(),nn.Conv2d(32,64,1))
        nn.init.zeros_(self.sam_projection[-1].weight)
        nn.init.zeros_(self.sam_projection[-1].bias)

    def load_rgb_control(self, state):
        result = self.load_state_dict(state, strict=False)
        expected = {'sam_projection.0.weight','sam_projection.0.bias',
                    'sam_projection.2.weight','sam_projection.2.bias'}
        if set(result.missing_keys) != expected or result.unexpected_keys:
            raise ValueError('Controle RGB incompatível com o adaptador')

    def forward(self, rgb, sam_features):
        if sam_features.ndim != 4 or sam_features.shape[1] != 256 or len(sam_features) != len(rgb):
            raise ValueError('Características SAM3 incompatíveis')
        e1 = self.enc1(rgb); e2 = self.enc2(self.pool(e1)); e3 = self.enc3(self.pool(e2))
        middle = self.middle(self.pool(e3))
        semantic = self.sam_projection(sam_features.to(dtype=rgb.dtype))
        middle = middle + F.interpolate(semantic,size=middle.shape[-2:],mode='bilinear',align_corners=False)
        value = self.dec3(torch.cat((self.up3(middle),e3),1))
        value = self.dec2(torch.cat((self.up2(value),e2),1))
        return self.output(self.dec1(torch.cat((self.up1(value),e1),1)))


def iris_loss(logits, target):
    # Penaliza falsos positivos no alvo anotado, sem inventar rótulos de pupila.
    valid = target != 255
    probability = logits.float().softmax(1)[:,1] * valid
    truth = (target == 1).float()
    tp = (probability*truth).sum((1,2))
    fp = (probability*(1-truth)).sum((1,2))
    fn = ((1-probability)*truth).sum((1,2))
    tversky = (tp+1)/(tp+.7*fp+.3*fn+1)
    return diverse_loss(logits,target) + .25*(1-tversky.mean())


class Sam3VisualFeatures:
    def __init__(self, device='cuda'):
        from avaliar_sam31_diverso import load_detector
        origin = json.loads(importlib.metadata.distribution('sam3').read_text('direct_url.json'))
        if SAM_REVISION not in json.dumps(origin):
            raise ValueError('Usar o ambiente SAM3 atual registrado')
        protocol = json.loads((ROOT/'outputs/sam31_atual_prompts_2026-11-03/protocolo.json').read_text())
        self.checkpoint = Path(protocol['checkpoint'])
        model,self.audit = load_detector(self.checkpoint,'cpu')
        self.backbone = model.backbone
        # A linguagem e as cabeças textuais não entram no extrator visual.
        self.backbone.language_backbone = None
        del model
        gc.collect()
        self.device = torch.device(device)
        self.backbone.requires_grad_(False).eval().to(self.device)
        from torchvision.transforms import v2
        self.transform = v2.Compose([v2.ToDtype(torch.uint8,scale=True),v2.Resize((1008,1008)),
                                     v2.ToDtype(torch.float32,scale=True),v2.Normalize([.5]*3,[.5]*3)])

    @torch.inference_mode()
    def __call__(self, rgb_uint8):
        from torchvision.transforms.v2 import functional as VF
        image = self.transform(VF.to_image(Image.fromarray(rgb_uint8)).to(self.device))[None]
        with torch.autocast('cuda',dtype=torch.bfloat16,enabled=self.device.type=='cuda'):
            output = self.backbone.forward_image(image)['vision_features']
        result = output[0].float().cpu().numpy().astype(np.float16)
        if result.shape != (256,72,72) or not np.isfinite(result).all():
            raise ValueError(f'Mapa SAM3 inválido: shape={result.shape}, finite={bool(np.isfinite(result).all())}')
        return result


def binary_metrics(predicted, target):
    valid = target != 255
    pred,truth = (predicted == 1)&valid,(target == 1)&valid
    tp,pp,tt = int((pred&truth).sum()),int(pred.sum()),int(truth.sum())
    return {'dice':(2*tp+1e-6)/(pp+tt+1e-6),'iou':(tp+1e-6)/(pp+tt-tp+1e-6),
            'prediction_pixels':pp,'reference_pixels':tt,'intersection_pixels':tp,
            'empty_reference_false_positive':bool(tt==0 and pp>0)}
