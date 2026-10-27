"""Pooling espacial aprendido, inicializado na media global original."""
import copy,hashlib
import torch
from torch import nn
from torch.nn import functional as F

class AttentionTail(nn.Module):
    def __init__(self,encoder,rank=32):
        super().__init__();self.block=copy.deepcopy(encoder.backbone.layer4);self.projection=copy.deepcopy(encoder.projection)
        for p in self.parameters():p.requires_grad_(False)
        self.attention=nn.Sequential(nn.Conv2d(512,rank,1),nn.ReLU(),nn.Conv2d(rank,1,1))
        nn.init.zeros_(self.attention[-1].weight);nn.init.zeros_(self.attention[-1].bias);self.train(False)
    def train(self,mode=True):
        super().train(mode);self.block.eval();self.projection.eval();return self
    def weights(self,x):
        logits=self.attention(x).flatten(2);learned=logits.softmax(-1)
        return (.5*learned+.5/logits.shape[-1]).reshape(len(x),1,*x.shape[-2:])
    def forward(self,x):
        with torch.no_grad():features=self.block(x)
        pooled=(features*self.weights(features)).sum((-2,-1))
        return F.normalize(self.projection(pooled),dim=1)
    def adapters(self):return {k:v.detach().cpu().clone() for k,v in self.state_dict().items() if k.startswith('attention.')}
    def load_adapters(self,state):
        expected=self.adapters();assert set(state)==set(expected)
        for k,v in state.items():assert v.shape==expected[k].shape and v.dtype==expected[k].dtype
        result=self.load_state_dict(state,strict=False);assert not result.unexpected_keys and all(not k.startswith('attention.') for k in result.missing_keys)
    def frozen_digest(self):
        h=hashlib.sha256()
        for k,v in self.state_dict().items():
            if k.startswith('attention.'):continue
            h.update(k.encode());h.update(str(v.dtype).encode());h.update(str(tuple(v.shape)).encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()
