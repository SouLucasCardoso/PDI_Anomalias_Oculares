"""Adaptador residual de descritor; backbone e projeção originais congelados."""
import numpy as np
import torch
from torch import nn

class PolarAdapter(nn.Module):
    def __init__(self):
        super().__init__();self.head=nn.Sequential(nn.Linear(512,128),nn.ReLU(),nn.Linear(128,256))
        nn.init.zeros_(self.head[-1].weight);nn.init.zeros_(self.head[-1].bias)
    def forward(self,raw,base):
        residual=.05*torch.tanh(self.head(raw))
        return nn.functional.normalize(base+residual,dim=-1),residual

def pooled_features(encoder,images,device,batch=32):
    """New candidate precision fixed to FP32 for both training and validation."""
    raw=[];base=[];mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    for start in range(0,len(images),batch):
        x=torch.from_numpy(np.asarray(images[start:start+batch]).transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode():
            features=encoder.backbone((x-mean)/std);vectors=nn.functional.normalize(encoder.projection(features),dim=1)
        raw.append(features.cpu().numpy());base.append(vectors.cpu().numpy())
    return np.concatenate(raw),np.concatenate(base)

def apply_adapter(model,raw,base,mean,std,device,batch=512):
    result=[]
    with torch.inference_mode():
        for start in range(0,len(raw),batch):
            x=torch.from_numpy(((raw[start:start+batch]-mean)/std).astype(np.float32)).to(device)
            b=torch.from_numpy(base[start:start+batch]).to(device)
            result.append(model(x,b)[0].cpu().numpy())
    return np.concatenate(result)
