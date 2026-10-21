"""ViT-L prefixo6 treinavel com projecao espacial de patches da faixa polar."""
import torch
from torch import nn

class Encoder(nn.Module):
    def __init__(self,backbone):
        super().__init__();self.backbone=backbone
        self.token_projection=nn.Sequential(nn.LayerNorm(1024),nn.Linear(1024,64),nn.GELU())
        self.projection=nn.Sequential(nn.Flatten(),nn.Dropout(.2),nn.Linear(128*64,256,bias=False),nn.BatchNorm1d(256))
    def forward(self,x):
        tokens=self.backbone(pixel_values=x).last_hidden_state[:,5:]
        if tokens.shape[1:]!=(128,1024):raise ValueError('Expected128 polar patches; CLS/registers excluded')
        return nn.functional.normalize(self.projection(self.token_projection(tokens)),dim=1)

def load(checkpoint,device='cpu'):
    from transformers import AutoModel
    from transformers.models.dinov3_vit.configuration_dinov3_vit import DINOv3ViTConfig
    state=torch.load(checkpoint,map_location='cpu',weights_only=True);configuration=state['configuration']
    assert configuration['architecture']=='dino6_polar_spatial256'
    config=DINOv3ViTConfig(**configuration['backbone_config']);config.num_hidden_layers=6
    backbone=AutoModel.from_config(config);backbone.norm=nn.Identity();model=Encoder(backbone)
    model.load_state_dict(state['model']);return model.to(device).eval(),configuration
