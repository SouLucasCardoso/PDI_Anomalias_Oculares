"""Encoder maior e lotes com sessoes distintas para reconhecimento de olho."""
import numpy as np
import torch
from torch import nn
from torch.utils.data import Sampler
from torchvision import models

class GeM(nn.Module):
    def forward(self,x):
        return x.clamp_min(1e-6).pow(3).mean((-2,-1),keepdim=True).pow(1/3)

class Encoder(nn.Module):
    def __init__(self):
        super().__init__();self.backbone=models.resnet50(weights=None)
        self.backbone.avgpool=GeM();self.backbone.fc=nn.Identity()
        self.projection=nn.Sequential(nn.Linear(2048,256,bias=False),nn.BatchNorm1d(256))
    def forward(self,x):
        return nn.functional.normalize(self.projection(self.backbone(x)),dim=1)

class SessionBatches(Sampler):
    def __init__(self,labels,sessions,p=16,rounds=4,seed=46):
        self.labels=np.asarray(labels);self.sessions=np.asarray(sessions);self.p=p;self.rounds=rounds;self.seed=seed;self.epoch=0
        self.eyes=np.unique(self.labels);self.groups={e:np.flatnonzero(self.labels==e) for e in self.eyes}
        if len(self.eyes)<p or len(labels)!=len(sessions):raise ValueError('Insufficient training identities')
    def __len__(self):return self.rounds*(len(self.eyes)//self.p)
    def __iter__(self):
        rng=np.random.default_rng(self.seed+self.epoch);self.epoch+=1
        for _ in range(self.rounds):
            order=rng.permutation(self.eyes)
            for start in range(0,len(order)-self.p+1,self.p):
                batch=[]
                for eye in order[start:start+self.p]:
                    indices=self.groups[eye];s1=indices[self.sessions[indices]==1];s2=indices[self.sessions[indices]==2]
                    if len(s1) and len(s2):
                        batch.extend(rng.choice(s1,2,replace=len(s1)<2));batch.extend(rng.choice(s2,2,replace=len(s2)<2))
                    else:batch.extend(rng.choice(indices,4,replace=len(indices)<4))
                yield [int(i) for i in batch]

def supervised_contrastive(features,labels,temperature=.1):
    f=nn.functional.normalize(features.float(),dim=1);logits=f@f.T/temperature
    off=~torch.eye(len(f),dtype=torch.bool,device=f.device)
    positive=(labels[:,None]==labels[None,:])&off
    if not positive.any(1).all():raise ValueError('Every anchor needs same-eye positive')
    logits=logits.masked_fill(~off,-torch.inf)
    logprob=logits-torch.logsumexp(logits,dim=1,keepdim=True)
    return -(logprob.masked_fill(~positive,0).sum(1)/positive.sum(1)).mean()

def load(checkpoint,device='cpu'):
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    assert state['configuration']['architecture']=='resnet50_gem3_256'
    model=Encoder();model.load_state_dict(state['model']);return model.to(device).eval(),state['configuration']
