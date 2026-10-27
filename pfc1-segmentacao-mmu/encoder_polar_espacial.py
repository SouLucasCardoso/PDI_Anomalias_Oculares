"""Correcoes de baixa ordem nas quatro convolucoes do ultimo bloco ResNet18."""
import copy,hashlib
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

class ConvCorrection(nn.Module):
    def __init__(self,base,rank=8):
        super().__init__();self.base=copy.deepcopy(base)
        for p in self.base.parameters():p.requires_grad_(False)
        self.low_in=nn.Conv2d(base.in_channels,rank,base.kernel_size,stride=base.stride,padding=base.padding,dilation=base.dilation,bias=False)
        self.low_out=nn.Conv2d(rank,base.out_channels,1,bias=False);nn.init.zeros_(self.low_out.weight)
    def forward(self,x):return self.base(x)+self.low_out(self.low_in(x))

class SpatialTail(nn.Module):
    def __init__(self,encoder,rank=8):
        super().__init__();self.block=copy.deepcopy(encoder.backbone.layer4);self.projection=copy.deepcopy(encoder.projection);self.rank=rank
        for p in self.parameters():p.requires_grad_(False)
        for residual in self.block:
            residual.conv1=ConvCorrection(residual.conv1,rank);residual.conv2=ConvCorrection(residual.conv2,rank)
        self.train(False)
    def train(self,mode=True):
        super().train(mode)
        for m in self.modules():
            if isinstance(m,(nn.BatchNorm1d,nn.BatchNorm2d)):m.eval()
        return self
    def forward(self,x):
        x=self.block(x);x=F.adaptive_avg_pool2d(x,1).flatten(1)
        return F.normalize(self.projection(x),dim=1)
    def adapters(self):return {k:v.detach().cpu().clone() for k,v in self.state_dict().items() if '.low_' in k}
    def load_adapters(self,state):
        expected=self.adapters();assert set(expected)==set(state)
        for k,v in state.items():assert v.shape==expected[k].shape and v.dtype==expected[k].dtype
        result=self.load_state_dict(state,strict=False);assert not result.unexpected_keys and all('.low_' not in k for k in result.missing_keys)
    def frozen_digest(self):
        h=hashlib.sha256()
        for k,v in self.state_dict().items():
            if '.low_' in k:continue
            h.update(k.encode());h.update(str(v.dtype).encode());h.update(str(tuple(v.shape)).encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()

def prefix_model(encoder):return nn.Sequential(*list(encoder.backbone.children())[:7]).eval()

def prefix_features(prefix,images,device):
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    x=torch.from_numpy(np.asarray(images).transpose(0,3,1,2).copy()).to(device).float()/255
    with torch.inference_mode():return prefix((x-mean)/std).cpu().numpy()

def tail_vectors(tail,features,indices,device,batch=32):
    result=[]
    with torch.inference_mode():
        for start in range(0,len(indices),batch):
            x=torch.from_numpy(np.array(features[indices[start:start+batch]],copy=True)).to(device);result.append(tail(x).cpu().numpy())
    return np.concatenate(result)
