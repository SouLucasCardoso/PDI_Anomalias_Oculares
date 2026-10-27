"""Ajuste dos kernels do ultimo bloco original, com BN/projecao congelados."""
import copy,hashlib
import torch
from torch import nn
from torch.nn import functional as F

class FullTail(nn.Module):
    def __init__(self,encoder,rank=0):
        super().__init__();self.block=copy.deepcopy(encoder.backbone.layer4);self.projection=copy.deepcopy(encoder.projection)
        for p in self.parameters():p.requires_grad_(False)
        for m in self.block.modules():
            if isinstance(m,nn.Conv2d):m.weight.requires_grad_(True)
        self._original={n:p.detach().cpu().clone() for n,p in self.named_parameters() if p.requires_grad}
        self.train(False)
    def train(self,mode=True):
        super().train(mode)
        for m in self.modules():
            if isinstance(m,(nn.BatchNorm1d,nn.BatchNorm2d)):m.eval()
        return self
    def forward(self,x):return F.normalize(self.projection(self.block(x).mean((-2,-1))),dim=1)
    def anchor_loss(self):
        return sum((p-self._original[n].to(p.device)).square().mean() for n,p in self.named_parameters() if p.requires_grad)
    def adapters(self):return {n:p.detach().cpu().clone() for n,p in self.named_parameters() if p.requires_grad}
    def load_adapters(self,state):
        expected=self.adapters();assert set(state)==set(expected)
        for n,v in state.items():assert v.shape==expected[n].shape and v.dtype==expected[n].dtype
        result=self.load_state_dict(state,strict=False);assert not result.unexpected_keys and not set(result.missing_keys)&set(expected)
    def frozen_digest(self):
        h=hashlib.sha256();trainable=set(self.adapters())
        for n,v in self.state_dict().items():
            if n in trainable:continue
            h.update(n.encode());h.update(str(v.dtype).encode());h.update(str(tuple(v.shape)).encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()
